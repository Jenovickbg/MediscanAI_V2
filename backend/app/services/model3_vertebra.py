from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import numpy as np

from app.core.config import BACKEND_DIR, settings
from app.models.resultat import VERTEBRES

logger = logging.getLogger(__name__)

VERTEBRA_CLASSES: tuple[str, ...] = (
    "hors_zone",
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
    "C6",
    "C7",
)


class Model3VertebraService:
    """Modèle 3 — DenseNet-121 2.5D (classification vertèbre C1–C7 + hors_zone)."""

    def __init__(self) -> None:
        self.model: Any = None
        self.device: Any = None
        self.use_mock = True
        self.model_loaded = False
        self._try_load()

    def _try_load(self) -> None:
        model_path = BACKEND_DIR / settings.MODEL_3_PATH
        if not model_path.exists():
            logger.info(
                "Modèle 3 absent (%s) — mode mock activé",
                settings.MODEL_3_PATH,
            )
            return

        try:
            import torch
            import timm

            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = timm.create_model(
                "densenet121",
                pretrained=False,
                in_chans=5,
                num_classes=len(VERTEBRA_CLASSES),
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
            logger.info("Modèle 3 (DenseNet-121 vertèbre) chargé sur %s", self.device)
        except Exception as exc:
            logger.warning("Impossible de charger le Modèle 3 — mode mock: %s", exc)
            self.model = None
            self.use_mock = True
            self.model_loaded = False

    @staticmethod
    def _slice_to_vertebra(slice_idx: int, n_slices: int) -> str:
        segment = min(int(slice_idx / max(n_slices, 1) * 7), 6)
        return VERTEBRES[segment]

    def _mock_vertebra(self, slice_idx: int, n_slices: int, study_id: str) -> str:
        """Prédiction déterministe basée sur la position anatomique de la coupe."""
        seed = abs(hash(f"{study_id}:{slice_idx}:model3")) % (2**32)
        rng = np.random.default_rng(seed)

        edge_ratio = slice_idx / max(n_slices - 1, 1)
        if edge_ratio < 0.04 or edge_ratio > 0.96:
            if float(rng.uniform(0, 1)) < 0.35:
                return "hors_zone"

        return self._slice_to_vertebra(slice_idx, n_slices)

    def _predict_slice(
        self,
        volume: np.ndarray,
        slice_idx: int,
        stack_builder: Callable[[np.ndarray, int], np.ndarray],
    ) -> str:
        import torch

        assert self.model is not None and self.device is not None

        stack = stack_builder(volume, slice_idx)
        tensor = torch.from_numpy(stack).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)
            pred_idx = int(logits.argmax(dim=1).item())

        return VERTEBRA_CLASSES[pred_idx]

    def run(
        self,
        volume: np.ndarray,
        coupes_a_traiter: list[int],
        study_id: str = "",
        stack_builder: Callable[[np.ndarray, int], np.ndarray] | None = None,
    ) -> dict[int, str]:
        """
        Classifie la vertèbre sur les coupes flaguées uniquement.

        Retourne { slice_idx: "C5" } (ou autre label, y compris hors_zone).
        """
        if not coupes_a_traiter:
            return {}

        if stack_builder is None:
            raise ValueError("stack_builder requis pour le Modèle 3 (empilement 2.5D)")

        n_slices = volume.shape[0]
        resultats: dict[int, str] = {}

        for slice_idx in coupes_a_traiter:
            if slice_idx < 0 or slice_idx >= n_slices:
                continue

            if self.use_mock or self.model is None:
                label = self._mock_vertebra(slice_idx, n_slices, study_id)
            else:
                label = self._predict_slice(volume, slice_idx, stack_builder)

            resultats[int(slice_idx)] = label

        return resultats
