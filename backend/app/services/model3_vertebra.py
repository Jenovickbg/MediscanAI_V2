from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import numpy as np

from app.core.config import settings
from app.models.resultat import VERTEBRES
from app.utils.model_paths import resolve_model_path
from app.utils.runtime import is_ia_mock_forced

logger = logging.getLogger(__name__)

VERTEBRA_CLASSES_8: tuple[str, ...] = (
    "hors_zone",
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
    "C6",
    "C7",
)

VERTEBRA_CLASSES_7: tuple[str, ...] = tuple(VERTEBRES)

VERTEBRA_CLASSES = VERTEBRA_CLASSES_7


def _infer_num_classes(state: dict[str, Any]) -> int:
    for key in ("classifier.weight", "classifier.bias"):
        if key in state:
            return int(state[key].shape[0])
    raise ValueError("Impossible de déduire num_classes depuis le state_dict")


def _classes_for_num_classes(num_classes: int) -> tuple[str, ...]:
    if num_classes == 7:
        return VERTEBRA_CLASSES_7
    if num_classes == 8:
        return VERTEBRA_CLASSES_8
    raise ValueError(f"num_classes non supporté pour le Modèle 3 : {num_classes}")


class Model3VertebraService:
    """Modèle 3 — DenseNet-121 2.5D (classification vertèbre C1–C7)."""

    def __init__(self) -> None:
        self.model: Any = None
        self.device: Any = None
        self.use_mock = True
        self.model_loaded = False
        self.vertebra_classes: tuple[str, ...] = VERTEBRA_CLASSES_7
        self._try_load()

    def _try_load(self) -> None:
        if is_ia_mock_forced():
            logger.info("MEDISCANAI_FORCE_MOCK — Modèle 3 en mode mock")
            return

        model_path = resolve_model_path(
            settings.MODEL_3_PATH,
            "model/model3_vertebre_densenet121.pth",
        )
        if model_path is None:
            logger.info(
                "Modèle 3 absent (%s) — mode mock activé",
                settings.MODEL_3_PATH,
            )
            return

        try:
            import torch
            import timm

            try:
                state = torch.load(model_path, map_location="cpu", weights_only=True)
            except TypeError:
                state = torch.load(model_path, map_location="cpu")

            num_classes = _infer_num_classes(state)
            self.vertebra_classes = _classes_for_num_classes(num_classes)

            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = timm.create_model(
                "densenet121",
                pretrained=False,
                in_chans=5,
                num_classes=num_classes,
                drop_rate=0.0,
            )
            self.model.load_state_dict(state)
            self.model.eval()
            self.model.to(self.device)
            self.use_mock = False
            self.model_loaded = True
            logger.info(
                "Modèle 3 (DenseNet-121 vertèbre, %d classes) chargé sur %s",
                num_classes,
                self.device,
            )
        except Exception as exc:
            logger.warning("Impossible de charger le Modèle 3 — mode mock: %s", exc)
            self.model = None
            self.use_mock = True
            self.model_loaded = False

    @staticmethod
    def _slice_to_vertebra(slice_idx: int, n_slices: int) -> str:
        segment = min(int(slice_idx / max(n_slices, 1) * 7), 6)
        return VERTEBRES[segment]

    def _mock_vertebra(self, slice_idx: int, n_slices: int, study_id: str) -> dict[str, Any]:
        """Prédiction déterministe basée sur la position anatomique de la coupe."""
        seed = abs(hash(f"{study_id}:{slice_idx}:model3")) % (2**32)
        rng = np.random.default_rng(seed)

        edge_ratio = slice_idx / max(n_slices - 1, 1)
        if "hors_zone" in self.vertebra_classes:
            if edge_ratio < 0.04 or edge_ratio > 0.96:
                if float(rng.uniform(0, 1)) < 0.35:
                    return {"vertebre": "hors_zone", "confiance": 0.55}

        vertebre = self._slice_to_vertebra(slice_idx, n_slices)
        return {"vertebre": vertebre, "confiance": float(rng.uniform(0.72, 0.96))}

    def _predict_slice(
        self,
        volume: np.ndarray,
        slice_idx: int,
        stack_builder: Callable[[np.ndarray, int], np.ndarray],
    ) -> dict[str, Any]:
        import torch

        assert self.model is not None and self.device is not None

        stack = stack_builder(volume, slice_idx)
        tensor = torch.from_numpy(stack).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
            pred_idx = int(probs.argmax())

        return {
            "vertebre": self.vertebra_classes[pred_idx],
            "confiance": float(probs[pred_idx]),
        }

    def run(
        self,
        volume: np.ndarray,
        coupes_a_traiter: list[int],
        study_id: str = "",
        stack_builder: Callable[[np.ndarray, int], np.ndarray] | None = None,
    ) -> dict[int, dict[str, Any]]:
        """
        Classifie la vertèbre sur les coupes flaguées uniquement.

        Retourne { slice_idx: {"vertebre": "C5", "confiance": 0.92} }.
        """
        if not coupes_a_traiter:
            return {}

        if stack_builder is None:
            raise ValueError("stack_builder requis pour le Modèle 3 (empilement 2.5D)")

        n_slices = volume.shape[0]
        resultats: dict[int, dict[str, Any]] = {}

        for slice_idx in coupes_a_traiter:
            if slice_idx < 0 or slice_idx >= n_slices:
                continue

            if self.use_mock or self.model is None:
                resultats[int(slice_idx)] = self._mock_vertebra(slice_idx, n_slices, study_id)
            else:
                resultats[int(slice_idx)] = self._predict_slice(volume, slice_idx, stack_builder)

        return resultats
