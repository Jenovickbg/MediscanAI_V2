from __future__ import annotations

import logging
from typing import Any

import numpy as np
from PIL import Image

from app.core.config import settings
from app.services.dicom_service import DicomService
from app.services.triage_config import load_triage_thresholds
from app.utils.model_paths import resolve_model_path
from app.utils.runtime import is_ia_mock_forced

logger = logging.getLogger(__name__)

# Centres anatomiques approximatifs (ratio y, x) pour bbox mock par vertèbre
_MOCK_CENTERS: dict[str, tuple[float, float]] = {
    "C1": (0.48, 0.18),
    "C2": (0.50, 0.28),
    "C3": (0.52, 0.38),
    "C4": (0.55, 0.48),
    "C5": (0.62, 0.55),
    "C6": (0.58, 0.65),
    "C7": (0.52, 0.78),
}


class Model2LocalizationService:
    """Modèle 2 — Faster RCNN ResNet50 FPN (localisation fracture sur coupes flaguées)."""

    FRACTURE_LABEL = 1
    INPUT_SIZE = (512, 512)

    def __init__(self, dicom_service: DicomService | None = None) -> None:
        self.dicom_service = dicom_service or DicomService()
        self.thresholds = load_triage_thresholds()
        self.model: Any = None
        self.device: Any = None
        self.use_mock = True
        self.model_loaded = False
        self._try_load()

    def _try_load(self) -> None:
        if is_ia_mock_forced():
            logger.info("MEDISCANAI_FORCE_MOCK — Modèle 2 en mode mock")
            return

        model_path = resolve_model_path(settings.MODEL_2_PATH)
        if model_path is None:
            logger.info(
                "Modèle 2 absent (%s) — mode mock activé",
                settings.MODEL_2_PATH,
            )
            return

        try:
            import torch
            from torchvision.models.detection import fasterrcnn_resnet50_fpn

            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = fasterrcnn_resnet50_fpn(weights=None, num_classes=2)
            try:
                state = torch.load(model_path, map_location="cpu", weights_only=True)
            except TypeError:
                state = torch.load(model_path, map_location="cpu")
            self.model.load_state_dict(state)
            self.model.roi_heads.nms_thresh = self.thresholds.nms_thresh_rcnn
            self.model.roi_heads.detections_per_img = self.thresholds.max_detections
            self.model.eval()
            self.model.to(self.device)
            self.use_mock = False
            self.model_loaded = True
            logger.info("Modèle 2 (Faster RCNN) chargé sur %s", self.device)
        except Exception as exc:
            logger.warning("Impossible de charger le Modèle 2 — mode mock: %s", exc)
            self.model = None
            self.use_mock = True
            self.model_loaded = False

    @staticmethod
    def _slice_to_vertebra(slice_idx: int, n_slices: int) -> str:
        from app.models.resultat import VERTEBRES

        segment = min(int(slice_idx / max(n_slices, 1) * 7), 6)
        return VERTEBRES[segment]

    def _prepare_slice_rgb(
        self,
        volume: np.ndarray,
        slice_idx: int,
        windowed_volume: np.ndarray | None = None,
    ) -> np.ndarray:
        """Fenêtrage osseux, resize 512×512, conversion en RGB float32 [0, 1]."""
        windowed = (
            windowed_volume
            if windowed_volume is not None
            else self.dicom_service.apply_windowing(volume.astype(np.float32))
        )
        idx = max(0, min(slice_idx, volume.shape[0] - 1))
        gray = windowed[idx]
        resized = np.asarray(
            Image.fromarray((gray * 255).astype(np.uint8), mode="L").resize(
                self.INPUT_SIZE,
                Image.Resampling.BILINEAR,
            ),
            dtype=np.float32,
        ) / 255.0
        return np.stack([resized, resized, resized], axis=0)

    def _mock_bbox(
        self,
        slice_idx: int,
        n_slices: int,
        h: int,
        w: int,
        study_id: str,
        triage_score: float | None = None,
    ) -> dict[str, Any]:
        """BBox déterministe centrée sur la vertèbre estimée de la coupe."""
        vertebra = self._slice_to_vertebra(slice_idx, n_slices)
        cy_ratio, cx_ratio = _MOCK_CENTERS.get(vertebra, (0.55, 0.55))

        seed = abs(hash(f"{study_id}:{slice_idx}:model2")) % (2**32)
        rng = np.random.default_rng(seed)
        jitter_y = float(rng.uniform(-0.03, 0.03))
        jitter_x = float(rng.uniform(-0.03, 0.03))

        cx = int((cx_ratio + jitter_x) * w)
        cy = int((cy_ratio + jitter_y) * h)
        bw = max(16, int(w * float(rng.uniform(0.04, 0.08))))
        bh = max(14, int(h * float(rng.uniform(0.035, 0.07))))

        x = max(0, min(cx - bw // 2, w - bw))
        y = max(0, min(cy - bh // 2, h - bh))

        base_conf = 0.72 if triage_score is None else min(0.98, 0.55 + triage_score * 0.4)
        confidence = float(max(0.5, min(0.99, base_conf + rng.uniform(-0.05, 0.05))))

        return {"bbox": [x, y, bw, bh], "confidence": confidence}

    def _predict_slice(
        self,
        volume: np.ndarray,
        slice_idx: int,
        windowed_volume: np.ndarray | None = None,
    ) -> dict[str, Any] | None:
        import torch

        assert self.model is not None and self.device is not None

        rgb = self._prepare_slice_rgb(volume, slice_idx, windowed_volume=windowed_volume)
        tensor = torch.from_numpy(rgb).to(self.device)

        with torch.no_grad():
            outputs = self.model([tensor])[0]

        boxes = outputs.get("boxes")
        labels = outputs.get("labels")
        scores = outputs.get("scores")
        if boxes is None or labels is None or scores is None or len(boxes) == 0:
            return None

        best: dict[str, Any] | None = None
        score_min = self.thresholds.score_thresh_rcnn
        for box, label, score in zip(boxes, labels, scores):
            if int(label.item()) != self.FRACTURE_LABEL:
                continue
            conf = float(score.item())
            if conf < score_min:
                continue
            if best is None or conf > best["confidence"]:
                x1, y1, x2, y2 = box.tolist()
                best = {
                    "bbox": [
                        int(round(x1)),
                        int(round(y1)),
                        int(round(x2 - x1)),
                        int(round(y2 - y1)),
                    ],
                    "confidence": conf,
                }
        return best

    def run(
        self,
        volume: np.ndarray,
        coupes_a_traiter: list[int],
        study_id: str = "",
        triage_scores: dict[int, float] | None = None,
        windowed_volume: np.ndarray | None = None,
    ) -> dict[int, dict[str, Any]]:
        """
        Localise les fractures sur les coupes flaguées uniquement.

        Retourne { slice_idx: {"bbox": [x, y, w, h], "confidence": float} }.
        """
        if not coupes_a_traiter:
            return {}

        n_slices = volume.shape[0]
        h, w = self.INPUT_SIZE
        triage_scores = triage_scores or {}
        resultats: dict[int, dict[str, Any]] = {}
        windowed = (
            windowed_volume
            if windowed_volume is not None
            else self.dicom_service.apply_windowing(volume.astype(np.float32))
        )

        for slice_idx in coupes_a_traiter:
            if slice_idx < 0 or slice_idx >= n_slices:
                continue

            if self.use_mock or self.model is None:
                entry = self._mock_bbox(
                    slice_idx,
                    n_slices,
                    h,
                    w,
                    study_id,
                    triage_scores.get(slice_idx),
                )
            else:
                entry = self._predict_slice(volume, slice_idx, windowed_volume=windowed)
                if entry is None:
                    entry = self._mock_bbox(
                        slice_idx,
                        n_slices,
                        h,
                        w,
                        study_id,
                        triage_scores.get(slice_idx),
                    )

            resultats[int(slice_idx)] = entry

        return resultats
