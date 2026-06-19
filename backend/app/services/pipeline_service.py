from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from app.core.config import BACKEND_DIR, settings
from app.models.resultat import VERTEBRES
from app.services.dicom_service import DicomService

logger = logging.getLogger(__name__)

LOCALISATIONS: dict[str, str] = {
    "C1": "Processus odontoïde, arc antérieur",
    "C2": "Corpus vertébral, zone pédiculaire",
    "C3": "Corps vertébral antérieur",
    "C4": "Corps vertébral, plateau supérieur",
    "C5": "Arc vertébral postérieur, Pédicule droit",
    "C6": "Processus articulaire inférieur",
    "C7": "Processus épineux, région cervicale basse",
}


class PipelineAIService:
    """Pipeline DenseNet-121 2.5D avec repli mock si le modèle est absent."""

    def __init__(self) -> None:
        self.dicom_service = DicomService()
        self.threshold = 0.03
        self.model = None
        self.device = None
        self.use_mock = True
        self.model_loaded = False
        self._try_load_model()

    def _try_load_model(self) -> None:
        model_path = BACKEND_DIR / settings.MODEL_PATH
        if not model_path.exists():
            logger.info("Modèle PyTorch absent — mode mock activé")
            return

        try:
            import torch
            import timm

            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = timm.create_model(
                "densenet121",
                pretrained=False,
                in_chans=5,
                num_classes=1,
                drop_rate=0.0,
            )
            try:
                state = torch.load(model_path, map_location="cpu", weights_only=True)
            except TypeError:
                state = torch.load(model_path, map_location="cpu")
            self.model.load_state_dict(state)
            self.model.eval()
            self.model.to(self.device)
            self.use_mock = False
            self.model_loaded = True
            logger.info("Modèle DenseNet-121 2.5D chargé sur %s", self.device)
        except Exception as exc:
            logger.warning("Impossible de charger le modèle — mode mock: %s", exc)
            self.model = None
            self.use_mock = True
            self.model_loaded = False

    def load_25d_slice(self, volume: np.ndarray, slice_idx: int) -> np.ndarray:
        """Extrait 5 coupes consécutives, fenêtrage osseux, normalisation, resize 384."""
        n_slices = volume.shape[0]
        indices = [
            max(0, min(slice_idx + offset, n_slices - 1))
            for offset in (-2, -1, 0, 1, 2)
        ]

        windowed = self.dicom_service.apply_windowing(volume.astype(np.float32))
        stack = np.stack([windowed[i] for i in indices], axis=0)

        resized = np.stack([self._resize_slice(stack[i]) for i in range(5)], axis=0)
        return resized.astype(np.float32)

    @staticmethod
    def _resize_slice(slice_arr: np.ndarray, size: tuple[int, int] = (384, 384)) -> np.ndarray:
        image = Image.fromarray((slice_arr * 255).astype(np.uint8), mode="L")
        resized = image.resize(size, Image.Resampling.BILINEAR)
        return np.asarray(resized, dtype=np.float32) / 255.0

    def _slice_to_vertebra(self, slice_idx: int, n_slices: int) -> str:
        segment = min(int(slice_idx / max(n_slices, 1) * 7), 6)
        return VERTEBRES[segment]

    def _predict_slice_score(self, volume: np.ndarray, slice_idx: int) -> float:
        if self.use_mock or self.model is None:
            return 0.0

        import torch

        tensor_input = self.load_25d_slice(volume, slice_idx)
        tensor = torch.from_numpy(tensor_input).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output = self.model(tensor)
            score = torch.sigmoid(output).item()
        return float(score)

    def _mock_predict(self, volume: np.ndarray, study_id: str) -> dict[str, Any]:
        """Scores réalistes déterministes pour tests sans modèle."""
        seed = abs(hash(study_id)) % (2**32)
        rng = np.random.default_rng(seed)
        n_slices = volume.shape[0]

        scores_par_coupe: list[tuple[int, float]] = []
        scores_par_vertebre: dict[str, float] = {v: 0.0 for v in VERTEBRES}
        coupes_positives: list[int] = []

        for slice_idx in range(n_slices):
            vertebra = self._slice_to_vertebra(slice_idx, n_slices)
            base = {"C1": 0.08, "C2": 0.23, "C3": 0.05, "C4": 0.67, "C5": 0.976, "C6": 0.31, "C7": 0.12}
            noise = float(rng.uniform(-0.04, 0.04))
            score = max(0.0, min(1.0, base.get(vertebra, 0.1) + noise))
            scores_par_coupe.append((slice_idx, score))
            scores_par_vertebre[vertebra] = max(scores_par_vertebre[vertebra], score)
            if score > self.threshold:
                coupes_positives.append(slice_idx)

        score_global = max(scores_par_vertebre.values())
        fracture_detectee = score_global > self.threshold

        return {
            "scores_par_coupe": scores_par_coupe,
            "scores_par_vertebre": scores_par_vertebre,
            "coupes_positives": coupes_positives,
            "fracture_detectee": fracture_detectee,
            "score_global": score_global,
            "mode_mock": True,
        }

    def predict_volume(self, volume: np.ndarray, study_id: str = "") -> dict[str, Any]:
        if self.use_mock:
            return self._mock_predict(volume, study_id)

        n_slices = volume.shape[0]
        scores_par_coupe: list[tuple[int, float]] = []
        scores_par_vertebre: dict[str, float] = {v: 0.0 for v in VERTEBRES}
        coupes_positives: list[int] = []

        # Analyse chaque 2 coupes pour accélérer l'inférence
        step = max(1, n_slices // 120)
        for slice_idx in range(0, n_slices, step):
            score = self._predict_slice_score(volume, slice_idx)
            vertebra = self._slice_to_vertebra(slice_idx, n_slices)
            scores_par_coupe.append((slice_idx, score))
            scores_par_vertebre[vertebra] = max(scores_par_vertebre[vertebra], score)
            if score > self.threshold:
                coupes_positives.append(slice_idx)

        score_global = max(scores_par_vertebre.values()) if scores_par_vertebre else 0.0
        return {
            "scores_par_coupe": scores_par_coupe,
            "scores_par_vertebre": scores_par_vertebre,
            "coupes_positives": coupes_positives,
            "fracture_detectee": score_global > self.threshold,
            "score_global": score_global,
            "mode_mock": False,
        }

    def build_vertebra_details(
        self,
        prediction: dict[str, Any],
        n_slices: int,
    ) -> list[dict[str, Any]]:
        """Construit les détails par vertèbre avec localisation et bounding box estimée."""
        details: list[dict[str, Any]] = []
        scores_par_coupe = prediction["scores_par_coupe"]

        for vertebre in VERTEBRES:
            prob = float(prediction["scores_par_vertebre"].get(vertebre, 0.0))
            segment_idx = VERTEBRES.index(vertebre)
            coupe_ref = int((segment_idx + 0.5) / 7 * max(n_slices - 1, 0))

            for slice_idx, score in scores_par_coupe:
                if self._slice_to_vertebra(slice_idx, n_slices) == vertebre and score >= prob - 0.01:
                    coupe_ref = slice_idx
                    break

            details.append(
                {
                    "vertebre": vertebre,
                    "probabilite": prob,
                    "localisation": LOCALISATIONS.get(vertebre, "Région vertébrale"),
                    "bounding_box_x": 0.35 + segment_idx * 0.03,
                    "bounding_box_y": 0.25,
                    "bounding_box_w": 0.18,
                    "bounding_box_h": 0.22,
                    "coupe_reference": coupe_ref,
                }
            )
        return details

    def generate_clinical_report(
        self,
        scores: dict[str, float],
        fracture_detectee: bool,
    ) -> str:
        at_risk = [
            (v, s)
            for v, s in scores.items()
            if s >= 0.30
        ]
        at_risk.sort(key=lambda item: item[1], reverse=True)

        if fracture_detectee and at_risk:
            summary = (
                f"Fracture vertébrale suspectée avec un score global de "
                f"{max(scores.values()) * 100:.1f}%. "
                f"Atteinte principale : {at_risk[0][0]} ({at_risk[0][1] * 100:.1f}%)."
            )
            certainty = "Élevé" if at_risk[0][1] >= 0.60 else "Modéré"
            recommendation = (
                "Recommandation : confirmation radiologique urgente, immobilisation cervicale "
                "selon protocole ATLS, et corrélation clinique."
            )
        else:
            summary = (
                "Aucune fracture vertébrale cervicale significative détectée "
                "par le modèle MediScanAI sur les segments C1–C7."
            )
            certainty = "Modéré à faible"
            recommendation = (
                "Recommandation : poursuivre la surveillance clinique standard. "
                "En cas de doute, compléter par une relecture radiologique."
            )

        lines = [
            "RÉSUMÉ",
            summary,
            "",
            "VERTÈBRES CONCERNÉES",
        ]

        if at_risk:
            for vertebre, score in at_risk:
                lines.append(
                    f"- {vertebre} : {score * 100:.1f}% — {LOCALISATIONS.get(vertebre, 'N/A')}"
                )
        else:
            lines.append("- Aucune vertèbre au-dessus du seuil de suspicion (30%).")

        lines.extend(
            [
                "",
                "NIVEAU DE CERTITUDE",
                certainty,
                "",
                "RECOMMANDATION",
                recommendation,
                "",
                "Note : Ce rapport est généré par MediScanAI et doit être validé par un médecin qualifié.",
            ]
        )
        return "\n".join(lines)

    def generate_gradcam(
        self,
        volume: np.ndarray,
        slice_idx: int,
        vertebra_id: str | None = None,
    ) -> np.ndarray:
        """Grad-CAM — heatmap réelle si modèle chargé, sinon estimation anatomique."""
        if not self.use_mock and self.model is not None:
            try:
                return self._gradcam_pytorch(volume, slice_idx)
            except Exception:
                logger.warning("Grad-CAM PyTorch échoué — repli mock")

        return self._gradcam_mock(volume, slice_idx, vertebra_id)

    def render_gradcam_png(
        self,
        volume: np.ndarray,
        slice_idx: int,
        vertebra_id: str | None = None,
        overlay: bool = False,
    ) -> bytes:
        import io

        rgb = self.generate_gradcam(volume, slice_idx, vertebra_id)
        buffer = io.BytesIO()

        if overlay:
            windowed = self.dicom_service.apply_windowing(volume.astype(np.float32))
            idx = max(0, min(slice_idx, volume.shape[0] - 1))
            base = windowed[idx]
            base_rgb = np.stack([base, base, base], axis=-1)
            diff = np.abs(rgb.astype(np.float32) / 255.0 - base_rgb)
            alpha = np.clip(diff.max(axis=2) * 2.5, 0, 1)
            rgba = np.dstack([rgb, (alpha * 255).astype(np.uint8)])
            Image.fromarray(rgba, mode="RGBA").save(buffer, format="PNG")
        else:
            Image.fromarray(rgb, mode="RGB").save(buffer, format="PNG")

        return buffer.getvalue()

    def _gradcam_mock(
        self,
        volume: np.ndarray,
        slice_idx: int,
        vertebra_id: str | None = None,
    ) -> np.ndarray:
        """Heatmap estimée avec focalisation par vertèbre (70 % original + 30 % jet)."""
        centers: dict[str, tuple[float, float]] = {
            "C1": (0.18, 0.48),
            "C2": (0.28, 0.50),
            "C3": (0.38, 0.52),
            "C4": (0.48, 0.55),
            "C5": (0.55, 0.62),
            "C6": (0.65, 0.58),
            "C7": (0.78, 0.52),
        }

        windowed = self.dicom_service.apply_windowing(volume.astype(np.float32))
        idx = max(0, min(slice_idx, volume.shape[0] - 1))
        base = windowed[idx]
        h, w = base.shape

        cy_ratio, cx_ratio = centers.get(vertebra_id or "C5", (0.55, 0.62))
        y, x = np.ogrid[:h, :w]
        cy, cx = h * cy_ratio, w * cx_ratio
        sigma = min(h, w) * 0.11
        heatmap = np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * sigma**2))
        heatmap = (heatmap - heatmap.min()) / max(heatmap.max() - heatmap.min(), 1e-6)

        r = np.clip(1.5 - np.abs(4 * heatmap - 3), 0, 1)
        g = np.clip(1.5 - np.abs(4 * heatmap - 2), 0, 1)
        b = np.clip(1.5 - np.abs(4 * heatmap - 1), 0, 1)
        colored = np.stack([r, g, b], axis=-1)

        base_rgb = np.stack([base, base, base], axis=-1)
        blended = 0.7 * base_rgb + 0.3 * colored
        return (np.clip(blended, 0, 1) * 255).astype(np.uint8)

    def _gradcam_pytorch(self, volume: np.ndarray, slice_idx: int) -> np.ndarray:
        """Grad-CAM via model.features.norm5 (DenseNet-121)."""
        import torch

        assert self.model is not None

        tensor_input = self.load_25d_slice(volume, slice_idx)
        input_tensor = torch.from_numpy(tensor_input).unsqueeze(0).to(self.device)
        input_tensor.requires_grad_(True)

        features: torch.Tensor | None = None

        def hook(_module: torch.nn.Module, _inputs: tuple, output: torch.Tensor) -> None:
            nonlocal features
            features = output

        handle = self.model.features.norm5.register_forward_hook(hook)
        try:
            output = self.model(input_tensor)
            score = torch.sigmoid(output).squeeze()
            self.model.zero_grad()
            score.backward(retain_graph=True)

            if features is None:
                raise RuntimeError("Features non capturées")

            gradients = features.grad
            if gradients is None:
                raise RuntimeError("Gradients non disponibles")

            weights = gradients.mean(dim=(2, 3), keepdim=True)
            cam = torch.relu((weights * features).sum(dim=1, keepdim=True))
            cam = cam.squeeze().detach().cpu().numpy()
            cam = (cam - cam.min()) / max(cam.max() - cam.min(), 1e-6)

            center_slice = tensor_input[2]
            h, w = center_slice.shape
            cam_resized = np.array(
                Image.fromarray((cam * 255).astype(np.uint8)).resize((w, h), Image.Resampling.BILINEAR),
                dtype=np.float32,
            ) / 255.0

            r = np.clip(1.5 - np.abs(4 * cam_resized - 3), 0, 1)
            g = np.clip(1.5 - np.abs(4 * cam_resized - 2), 0, 1)
            b = np.clip(1.5 - np.abs(4 * cam_resized - 1), 0, 1)
            colored = np.stack([r, g, b], axis=-1)

            base_rgb = np.stack([center_slice, center_slice, center_slice], axis=-1)
            blended = 0.7 * base_rgb + 0.3 * colored
            return (np.clip(blended, 0, 1) * 255).astype(np.uint8)
        finally:
            handle.remove()


pipeline_service = PipelineAIService()
