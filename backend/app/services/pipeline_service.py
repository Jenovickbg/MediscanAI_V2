from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from app.core.config import settings
from app.models.resultat import VERTEBRES
from app.services.dicom_service import DicomService
from app.services.model2_localization import Model2LocalizationService
from app.services.model3_vertebra import Model3VertebraService
from app.services.triage_config import (
    TriageThresholds,
    classifier_triage,
    is_coupe_flaguee,
    load_triage_thresholds,
)
from app.utils.model_paths import resolve_model_path
from app.utils.runtime import is_ia_mock_forced

logger = logging.getLogger(__name__)

os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("MKL_NUM_THREADS", "4")


def _cpu_thread_count() -> int:
    return max(1, min(4, os.cpu_count() or 4))


def _configure_torch_threads() -> None:
    try:
        import torch

        n = _cpu_thread_count()
        torch.set_num_threads(n)
        if hasattr(torch, "set_num_interop_threads"):
            torch.set_num_interop_threads(max(1, n // 2))
    except Exception:
        pass


MODEL1_BATCH_SIZE = 16
MODEL1_IMAGE_SIZE_CPU = 256
MODEL1_IMAGE_SIZE_DEFAULT = 384


def _is_finite_number(value: object) -> bool:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return number == number and number not in (float("inf"), float("-inf"))


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
    """Orchestrateur pipeline IA — Modèles 1 (triage), 2 (localisation), 3 (vertèbre)."""

    def __init__(self) -> None:
        _configure_torch_threads()
        self.dicom_service = DicomService()
        self.thresholds: TriageThresholds = load_triage_thresholds()
        self.model_1 = None
        self.model_2 = Model2LocalizationService(dicom_service=self.dicom_service)
        self.model_3 = Model3VertebraService()
        self.device = None
        self.use_mock = True
        self.model_loaded = False
        self._try_load_model_1()

    @property
    def threshold(self) -> float:
        """Compatibilité — seuil bas du triage (ancien code)."""
        return self.thresholds.seuil_bas

    @property
    def model(self):
        """Alias rétrocompatibilité Grad-CAM."""
        return self.model_1

    def reload_thresholds(self) -> None:
        """Recharge les seuils depuis le fichier JSON (sans redéployer)."""
        self.thresholds = load_triage_thresholds()

    def _try_load_model_1(self) -> None:
        if is_ia_mock_forced():
            logger.info("MEDISCANAI_FORCE_MOCK — Modèle 1 en mode mock")
            return

        model_path = resolve_model_path(settings.MODEL_1_PATH)
        if model_path is None:
            logger.info(
                "Modèle 1 absent (%s) — mode mock activé",
                settings.MODEL_1_PATH,
            )
            return

        try:
            import torch
            import timm

            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model_1 = timm.create_model(
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
            self.model_1.load_state_dict(state)
            self.model_1.eval()
            self.model_1.to(self.device)
            self.use_mock = False
            self.model_loaded = True
            logger.info("Modèle 1 (DenseNet-121 2.5D) chargé sur %s", self.device)
        except Exception as exc:
            logger.warning("Impossible de charger le Modèle 1 — mode mock: %s", exc)
            self.model_1 = None
            self.use_mock = True
            self.model_loaded = False

    def build_25d_stack(
        self,
        volume: np.ndarray,
        slice_idx: int,
        image_size: int | None = None,
        windowed_volume: np.ndarray | None = None,
    ) -> np.ndarray:
        """Extrait 5 coupes consécutives (2.5D) pour le Modèle 1."""
        return self.load_25d_slice(
            volume,
            slice_idx,
            image_size=image_size,
            windowed_volume=windowed_volume,
        )

    @staticmethod
    def window_volume(volume: np.ndarray, dicom_service: DicomService | None = None) -> np.ndarray:
        """Fenêtrage osseux une seule fois sur tout le volume (évite N recalculs)."""
        svc = dicom_service or DicomService()
        return svc.apply_windowing(volume.astype(np.float32))

    def load_25d_slice(
        self,
        volume: np.ndarray,
        slice_idx: int,
        image_size: int | None = None,
        windowed_volume: np.ndarray | None = None,
    ) -> np.ndarray:
        """Extrait 5 coupes consécutives, fenêtrage osseux, normalisation, resize."""
        size = image_size if image_size is not None else self._inference_image_size()
        n_slices = volume.shape[0]
        indices = [
            max(0, min(slice_idx + offset, n_slices - 1))
            for offset in (-2, -1, 0, 1, 2)
        ]

        windowed = (
            windowed_volume
            if windowed_volume is not None
            else self.window_volume(volume, self.dicom_service)
        )
        stack = np.stack([windowed[i] for i in indices], axis=0)

        resized = np.stack(
            [self._resize_slice(stack[i], size=(size, size)) for i in range(5)],
            axis=0,
        )
        return resized.astype(np.float32)

    def _inference_image_size(self) -> int:
        on_cuda = self.device is not None and str(self.device).startswith("cuda")
        return MODEL1_IMAGE_SIZE_DEFAULT if on_cuda else MODEL1_IMAGE_SIZE_CPU

    @staticmethod
    def _resize_slice(slice_arr: np.ndarray, size: tuple[int, int] = (384, 384)) -> np.ndarray:
        image = Image.fromarray((slice_arr * 255).astype(np.uint8), mode="L")
        resized = image.resize(size, Image.Resampling.BILINEAR)
        return np.asarray(resized, dtype=np.float32) / 255.0

    def _slice_to_vertebra(self, slice_idx: int, n_slices: int) -> str:
        segment = min(int(slice_idx / max(n_slices, 1) * 7), 6)
        return VERTEBRES[segment]

    def _predict_slice_score(self, volume: np.ndarray, slice_idx: int) -> float:
        if self.use_mock or self.model_1 is None:
            return 0.0

        import torch

        tensor_input = self.build_25d_stack(volume, slice_idx)
        tensor = torch.from_numpy(tensor_input).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output = self.model_1(tensor)
            score = torch.sigmoid(output).item()
        return float(score)

    def _mock_slice_score(
        self,
        slice_idx: int,
        n_slices: int,
        rng: np.random.Generator,
    ) -> float:
        vertebra = self._slice_to_vertebra(slice_idx, n_slices)
        base = {
            "C1": 0.08,
            "C2": 0.23,
            "C3": 0.05,
            "C4": 0.67,
            "C5": 0.976,
            "C6": 0.31,
            "C7": 0.12,
        }
        noise = float(rng.uniform(-0.04, 0.04))
        return max(0.0, min(1.0, base.get(vertebra, 0.1) + noise))

    def _run_model1(
        self,
        volume: np.ndarray,
        on_progress: Callable[[int], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
        windowed_volume: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        """Modèle 1 — inférence par lots (batch 16, 256×256 sur CPU)."""
        import torch

        results: list[dict[str, Any]] = []
        n_slices = volume.shape[0]
        image_size = self._inference_image_size()
        windowed = windowed_volume if windowed_volume is not None else self.window_volume(volume, self.dicom_service)

        with torch.no_grad():
            for batch_start in range(0, n_slices, MODEL1_BATCH_SIZE):
                if is_cancelled and is_cancelled():
                    break

                if on_progress:
                    on_progress(40 + int(batch_start / max(n_slices, 1) * 20))

                batch_end = min(batch_start + MODEL1_BATCH_SIZE, n_slices)
                batch_indices = range(batch_start, batch_end)

                stacks = [
                    self.load_25d_slice(
                        volume,
                        i,
                        image_size=image_size,
                        windowed_volume=windowed,
                    )
                    for i in batch_indices
                ]
                batch_tensor = torch.from_numpy(np.stack(stacks)).float().to(self.device)
                logits = self.model_1(batch_tensor)
                probs = torch.sigmoid(logits).cpu().numpy()

                for j, slice_idx in enumerate(batch_indices):
                    prob = float(probs[j, 0]) if probs.ndim > 1 else float(probs[j])
                    if not _is_finite_number(prob):
                        prob = 0.0
                    results.append(
                        {
                            "slice": slice_idx,
                            "score": prob,
                            "categorie": classifier_triage(prob, self.thresholds),
                        }
                    )

                if on_progress:
                    on_progress(40 + int(batch_end / max(n_slices, 1) * 20))

        return results

    def run_model_1_triage(
        self,
        volume: np.ndarray,
        study_id: str = "",
        on_progress: Callable[[int], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
        windowed_volume: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        """
        Modèle 1 sur toutes les coupes du volume.
        Retourne une entrée par coupe : { slice, score, categorie }.
        """
        n_slices = volume.shape[0]
        results: list[dict[str, Any]] = []

        if self.use_mock:
            seed = abs(hash(study_id)) % (2**32)
            rng = np.random.default_rng(seed)
            for slice_idx in range(n_slices):
                if is_cancelled and is_cancelled():
                    break
                score = self._mock_slice_score(slice_idx, n_slices, rng)
                categorie = classifier_triage(score, self.thresholds)
                results.append({"slice": slice_idx, "score": score, "categorie": categorie})
                if on_progress and (slice_idx == n_slices - 1 or slice_idx % max(1, n_slices // 5) == 0):
                    on_progress(40 + int((slice_idx + 1) / max(n_slices, 1) * 20))
            return results

        return self._run_model1(
            volume,
            on_progress=on_progress,
            is_cancelled=is_cancelled,
            windowed_volume=windowed_volume,
        )

    @staticmethod
    def coupes_flaguees_from_triage(triage_par_coupe: list[dict[str, Any]]) -> list[int]:
        """Coupes transmises aux Modèles 2 et 3 (incertain ou eleve)."""
        return [
            int(entry["slice"])
            for entry in triage_par_coupe
            if is_coupe_flaguee(entry["categorie"])
        ]

    @staticmethod
    def _fracture_from_triage(
        triage_par_coupe: list[dict[str, Any]],
        seuil_haut: float,
    ) -> bool:
        """Fracture si au moins une coupe est eleve, ou score max >= seuil haut."""
        if not triage_par_coupe:
            return False
        if any(entry["categorie"] == "eleve" for entry in triage_par_coupe):
            return True
        max_score = max(float(entry["score"]) for entry in triage_par_coupe)
        return max_score >= seuil_haut

    def run_model_2_localization(
        self,
        volume: np.ndarray,
        coupes_a_traiter: list[int],
        study_id: str = "",
        triage_par_coupe: list[dict[str, Any]] | None = None,
        windowed_volume: np.ndarray | None = None,
    ) -> dict[int, dict[str, Any]]:
        """Modèle 2 — bbox fracture sur coupes flaguées uniquement."""
        triage_scores: dict[int, float] = {}
        if triage_par_coupe:
            triage_scores = {
                int(entry["slice"]): float(entry["score"]) for entry in triage_par_coupe
            }
        return self.model_2.run(
            volume,
            coupes_a_traiter,
            study_id=study_id,
            triage_scores=triage_scores,
            windowed_volume=windowed_volume,
        )

    def run_model_3_vertebra(
        self,
        volume: np.ndarray,
        coupes_a_traiter: list[int],
        study_id: str = "",
        windowed_volume: np.ndarray | None = None,
    ) -> dict[int, dict[str, Any]]:
        """Modèle 3 — classification vertèbre sur coupes flaguées uniquement."""
        return self.model_3.run(
            volume,
            coupes_a_traiter,
            study_id=study_id,
            stack_builder=lambda vol, idx: self.build_25d_stack(
                vol,
                idx,
                windowed_volume=windowed_volume,
            ),
        )

    @staticmethod
    def _parse_vertebre_result(value: str | dict[str, Any]) -> tuple[str, float | None]:
        if isinstance(value, dict):
            return str(value["vertebre"]), float(value.get("confiance", 0.0))
        return str(value), None

    def _execute_pipeline_phases(
        self,
        volume: np.ndarray,
        study_id: str = "",
        on_progress: Callable[[int], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> tuple[
        list[dict[str, Any]],
        list[int],
        dict[int, dict[str, Any]],
        dict[int, dict[str, Any]],
    ]:
        """Phases 1–2 : triage complet puis Modèles 2 et 3 sur coupes flaguées."""
        if on_progress:
            on_progress(39)
        windowed = self.window_volume(volume, self.dicom_service)
        if on_progress:
            on_progress(40)
        triage_par_coupe = self.run_model_1_triage(
            volume,
            study_id=study_id,
            on_progress=on_progress,
            is_cancelled=is_cancelled,
            windowed_volume=windowed,
        )
        coupes_flaguees = self.coupes_flaguees_from_triage(triage_par_coupe)
        if on_progress:
            on_progress(62)

        resultats_localisation: dict[int, dict[str, Any]] = {}
        resultats_vertebre: dict[int, dict[str, Any]] = {}
        if coupes_flaguees:
            resultats_localisation = self.run_model_2_localization(
                volume,
                coupes_flaguees,
                study_id=study_id,
                triage_par_coupe=triage_par_coupe,
                windowed_volume=windowed,
            )
            if on_progress:
                on_progress(72)
            resultats_vertebre = self.run_model_3_vertebra(
                volume,
                coupes_flaguees,
                study_id=study_id,
                windowed_volume=windowed,
            )
            if on_progress:
                on_progress(80)

        return triage_par_coupe, coupes_flaguees, resultats_localisation, resultats_vertebre

    def _agreger_par_vertebre(
        self,
        triage_par_coupe: list[dict[str, Any]],
        resultats_bbox: dict[int, dict[str, Any]],
        resultats_vertebre: dict[int, str | dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """
        Agrège par vertèbre — retient la coupe au score de fracture le plus élevé.
        Contrat : { "C5": { probabilite, bounding_box, coupe_reference, niveau_risque, confiance_vertebre? } }.
        """
        score_by_slice = {int(entry["slice"]): float(entry["score"]) for entry in triage_par_coupe}
        par_vertebre: dict[str, dict[str, Any]] = {}

        for slice_idx, raw in resultats_vertebre.items():
            vlabel, confiance = self._parse_vertebre_result(raw)
            if vlabel == "hors_zone":
                continue

            score = score_by_slice.get(slice_idx, 0.0)
            bbox_raw = resultats_bbox.get(slice_idx, {}).get("bbox")
            bounding_box: dict[str, int] | None = None
            if bbox_raw and len(bbox_raw) == 4:
                x, y, w, h = bbox_raw
                if all(_is_finite_number(v) for v in (x, y, w, h)):
                    bounding_box = {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}

            niveau_risque = classifier_triage(score, self.thresholds)
            entry: dict[str, Any] = {
                "probabilite": score,
                "bounding_box": bounding_box,
                "coupe_reference": int(slice_idx),
                "niveau_risque": niveau_risque,
            }
            if confiance is not None:
                entry["confiance_vertebre"] = round(confiance, 4)

            if vlabel not in par_vertebre or score > par_vertebre[vlabel]["probabilite"]:
                par_vertebre[vlabel] = entry

        return par_vertebre

    def _generer_rapport_clinique(self, scores_par_vertebre: dict[str, dict[str, Any]]) -> str:
        """Rapport clinique à partir du contrat agrégé par vertèbre."""
        if not scores_par_vertebre:
            return "Aucune anomalie détectée sur l'ensemble de l'examen."

        flat_scores = {v: float(d["probabilite"]) for v, d in scores_par_vertebre.items()}
        fracture_detectee = any(
            d.get("niveau_risque") in ("incertain", "eleve") for d in scores_par_vertebre.values()
        )
        return self.generate_clinical_report(flat_scores, fracture_detectee=fracture_detectee)

    def analyser_examen(
        self,
        volume: np.ndarray,
        study_id: str = "",
        on_progress: Callable[[int], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        """
        Point d'entrée principal — orchestration complète des 3 modèles (4 phases).

        Retourne le contrat JSON final pour le frontend et la persistance.
        """
        triage_par_coupe, coupes_flaguees, resultats_bbox, resultats_vertebre = (
            self._execute_pipeline_phases(
                volume,
                study_id=study_id,
                on_progress=on_progress,
                is_cancelled=is_cancelled,
            )
        )

        if not coupes_flaguees:
            return {
                "study_id": study_id,
                "fracture_detectee": False,
                "scores_par_vertebre": {},
                "rapport_clinique": "Aucune anomalie détectée sur l'ensemble de l'examen.",
                "mode_mock": self.use_mock,
                "mode_mock_model_2": self.model_2.use_mock,
                "mode_mock_model_3": self.model_3.use_mock,
                "triage_par_coupe": triage_par_coupe,
                "coupes_flaguees": [],
            }

        scores_par_vertebre = self._agreger_par_vertebre(
            triage_par_coupe,
            resultats_bbox,
            resultats_vertebre,
        )
        rapport = self._generer_rapport_clinique(scores_par_vertebre)
        fracture_detectee = self._fracture_from_triage(
            triage_par_coupe,
            self.thresholds.seuil_haut,
        )

        return {
            "study_id": study_id,
            "fracture_detectee": fracture_detectee,
            "scores_par_vertebre": scores_par_vertebre,
            "rapport_clinique": rapport,
            "mode_mock": self.use_mock,
            "mode_mock_model_2": self.model_2.use_mock,
            "mode_mock_model_3": self.model_3.use_mock,
            "triage_par_coupe": triage_par_coupe,
            "coupes_flaguees": coupes_flaguees,
            "resultats_localisation": resultats_bbox,
            "resultats_vertebre": resultats_vertebre,
        }

    def _aggregate_vertebra_scores(
        self,
        triage_par_coupe: list[dict[str, Any]],
        n_slices: int,
    ) -> dict[str, float]:
        scores_par_vertebre: dict[str, float] = {v: 0.0 for v in VERTEBRES}
        for entry in triage_par_coupe:
            slice_idx = int(entry["slice"])
            score = float(entry["score"])
            vertebra = self._slice_to_vertebra(slice_idx, n_slices)
            scores_par_vertebre[vertebra] = max(scores_par_vertebre[vertebra], score)
        return scores_par_vertebre

    def _prediction_from_triage(
        self,
        triage_par_coupe: list[dict[str, Any]],
        n_slices: int,
        mode_mock: bool,
        resultats_localisation: dict[int, dict[str, Any]] | None = None,
        resultats_vertebre: dict[int, str | dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        coupes_flaguees = self.coupes_flaguees_from_triage(triage_par_coupe)
        scores_par_vertebre = self._aggregate_vertebra_scores(triage_par_coupe, n_slices)
        score_global = max(scores_par_vertebre.values()) if scores_par_vertebre else 0.0

        scores_par_coupe = [
            (int(entry["slice"]), float(entry["score"])) for entry in triage_par_coupe
        ]

        return {
            "scores_par_coupe": scores_par_coupe,
            "triage_par_coupe": triage_par_coupe,
            "scores_par_vertebre": scores_par_vertebre,
            "coupes_flaguees": coupes_flaguees,
            "coupes_positives": coupes_flaguees,
            "resultats_localisation": resultats_localisation or {},
            "resultats_vertebre": resultats_vertebre or {},
            "fracture_detectee": self._fracture_from_triage(
                triage_par_coupe,
                self.thresholds.seuil_haut,
            ),
            "score_global": score_global,
            "mode_mock": mode_mock,
            "mode_mock_model_2": self.model_2.use_mock,
            "mode_mock_model_3": self.model_3.use_mock,
            "thresholds": {
                "seuil_bas": self.thresholds.seuil_bas,
                "seuil_haut": self.thresholds.seuil_haut,
            },
        }

    def _mock_predict(self, volume: np.ndarray, study_id: str) -> dict[str, Any]:
        """Scores réalistes déterministes pour tests sans Modèle 1."""
        triage, _, loc, vert = self._execute_pipeline_phases(volume, study_id=study_id)
        return self._prediction_from_triage(
            triage,
            volume.shape[0],
            mode_mock=True,
            resultats_localisation=loc,
            resultats_vertebre=vert,
        )

    def predict_volume(self, volume: np.ndarray, study_id: str = "") -> dict[str, Any]:
        triage, _, loc, vert = self._execute_pipeline_phases(volume, study_id=study_id)
        return self._prediction_from_triage(
            triage,
            volume.shape[0],
            mode_mock=self.use_mock,
            resultats_localisation=loc,
            resultats_vertebre=vert,
        )

    @staticmethod
    def _normalize_bbox(bbox: list[int], width: int = 512, height: int = 512) -> tuple[float, float, float, float]:
        x, y, bw, bh = bbox
        return x / width, y / height, bw / width, bh / height

    def build_vertebra_details_from_analyse(
        self,
        analyse: dict[str, Any],
        n_slices: int,
    ) -> list[dict[str, Any]]:
        """Construit les lignes DB à partir du contrat `analyser_examen()`."""
        aggregated: dict[str, dict[str, Any]] = analyse.get("scores_par_vertebre", {})
        details: list[dict[str, Any]] = []

        for vertebre in VERTEBRES:
            segment_idx = VERTEBRES.index(vertebre)
            coupe_ref = int((segment_idx + 0.5) / 7 * max(n_slices - 1, 0))
            bbox_x, bbox_y, bbox_w, bbox_h = 0.35 + segment_idx * 0.03, 0.25, 0.18, 0.22
            prob = 0.0
            confiance_vertebre: float | None = None

            if vertebre in aggregated:
                entry = aggregated[vertebre]
                prob = float(entry["probabilite"])
                coupe_ref = int(entry["coupe_reference"])
                confiance_vertebre = entry.get("confiance_vertebre")
                bbox = entry.get("bounding_box")
                if bbox:
                    bbox_x, bbox_y, bbox_w, bbox_h = self._normalize_bbox(
                        [bbox["x"], bbox["y"], bbox["w"], bbox["h"]],
                    )

            detail: dict[str, Any] = {
                "vertebre": vertebre,
                "probabilite": prob,
                "localisation": LOCALISATIONS.get(vertebre, "Région vertébrale"),
                "bounding_box_x": bbox_x,
                "bounding_box_y": bbox_y,
                "bounding_box_w": bbox_w,
                "bounding_box_h": bbox_h,
                "coupe_reference": coupe_ref,
                "niveau_risque": aggregated.get(vertebre, {}).get("niveau_risque"),
            }
            if confiance_vertebre is not None:
                detail["confiance_vertebre"] = confiance_vertebre
            details.append(detail)
        return details

    @staticmethod
    def score_global_from_analyse(analyse: dict[str, Any]) -> float:
        scores = analyse.get("scores_par_vertebre") or {}
        if not scores:
            triage = analyse.get("triage_par_coupe") or []
            if triage:
                return max(float(entry["score"]) for entry in triage)
            return 0.0
        return max(float(entry["probabilite"]) for entry in scores.values())

    def build_vertebra_details(
        self,
        prediction: dict[str, Any],
        n_slices: int,
    ) -> list[dict[str, Any]]:
        """Construit les détails par vertèbre avec localisation et bounding box (Modèle 2 si dispo)."""
        details: list[dict[str, Any]] = []
        scores_par_coupe = prediction["scores_par_coupe"]
        resultats_localisation: dict[int, dict[str, Any]] = prediction.get(
            "resultats_localisation",
            {},
        )
        resultats_vertebre: dict[int, str | dict[str, Any]] = prediction.get("resultats_vertebre", {})

        def _vertebre_at(slice_idx: int) -> str | None:
            raw = resultats_vertebre.get(slice_idx)
            if raw is None:
                return None
            label, _ = self._parse_vertebre_result(raw)
            return label

        for vertebre in VERTEBRES:
            prob = float(prediction["scores_par_vertebre"].get(vertebre, 0.0))
            segment_idx = VERTEBRES.index(vertebre)
            coupe_ref = int((segment_idx + 0.5) / 7 * max(n_slices - 1, 0))
            bbox_x, bbox_y, bbox_w, bbox_h = 0.35 + segment_idx * 0.03, 0.25, 0.18, 0.22

            best_slice_for_vertebra: int | None = None
            best_score = -1.0
            for slice_idx, score in scores_par_coupe:
                if self._slice_to_vertebra(slice_idx, n_slices) == vertebre and score >= prob - 0.01:
                    coupe_ref = slice_idx
                if (
                    _vertebre_at(slice_idx) == vertebre
                    and slice_idx in resultats_localisation
                    and score > best_score
                ):
                    best_score = score
                    best_slice_for_vertebra = slice_idx

            if best_slice_for_vertebra is None:
                for slice_idx, score in scores_par_coupe:
                    if (
                        _vertebre_at(slice_idx) == vertebre
                        and slice_idx in resultats_localisation
                        and score > best_score
                    ):
                        best_score = score
                        best_slice_for_vertebra = slice_idx

            if best_slice_for_vertebra is not None:
                loc = resultats_localisation[best_slice_for_vertebra]
                bbox_x, bbox_y, bbox_w, bbox_h = self._normalize_bbox(loc["bbox"])
                coupe_ref = best_slice_for_vertebra

            details.append(
                {
                    "vertebre": vertebre,
                    "probabilite": prob,
                    "localisation": LOCALISATIONS.get(vertebre, "Région vertébrale"),
                    "bounding_box_x": bbox_x,
                    "bounding_box_y": bbox_y,
                    "bounding_box_w": bbox_w,
                    "bounding_box_h": bbox_h,
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
        if not self.use_mock and self.model_1 is not None:
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

        assert self.model_1 is not None

        tensor_input = self.build_25d_stack(volume, slice_idx)
        input_tensor = torch.from_numpy(tensor_input).unsqueeze(0).to(self.device)
        input_tensor.requires_grad_(True)

        features: torch.Tensor | None = None

        def hook(_module: torch.nn.Module, _inputs: tuple, output: torch.Tensor) -> None:
            nonlocal features
            features = output

        handle = self.model_1.features.norm5.register_forward_hook(hook)
        try:
            output = self.model_1(input_tensor)
            score = torch.sigmoid(output).squeeze()
            self.model_1.zero_grad()
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
