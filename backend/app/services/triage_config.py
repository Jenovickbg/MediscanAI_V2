"""Seuils de triage clinique du Modèle 1 — chargés depuis config externe."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.core.config import BACKEND_DIR, settings

logger = logging.getLogger(__name__)

TriageCategory = Literal["normal", "incertain", "eleve"]

DEFAULT_THRESHOLDS = {
    "seuil_bas": 0.03,
    "seuil_haut": 0.10,
    "derniere_maj": "PLACEHOLDER",
}


@dataclass(frozen=True)
class TriageThresholds:
    """
    Seuils de triage clinique du Modèle 1.
    Valeurs provisoires — recalibrées après réentraînement final.
    """

    seuil_bas: float
    seuil_haut: float
    derniere_maj: str = "PLACEHOLDER"


def load_triage_thresholds(path: Path | None = None) -> TriageThresholds:
    config_path = path or (BACKEND_DIR / settings.TRIAGE_THRESHOLDS_PATH)

    if not config_path.exists():
        logger.warning("Fichier triage absent (%s) — valeurs par défaut", config_path)
        return TriageThresholds(**DEFAULT_THRESHOLDS)

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return TriageThresholds(
            seuil_bas=float(data["seuil_bas"]),
            seuil_haut=float(data["seuil_haut"]),
            derniere_maj=str(data.get("derniere_maj", "PLACEHOLDER")),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Config triage invalide (%s) — valeurs par défaut: %s", config_path, exc)
        return TriageThresholds(**DEFAULT_THRESHOLDS)


def classifier_triage(probability: float, thresholds: TriageThresholds) -> TriageCategory:
    """Classe une probabilité Modèle 1 : normal | incertain | eleve."""
    if probability < thresholds.seuil_bas:
        return "normal"
    if probability < thresholds.seuil_haut:
        return "incertain"
    return "eleve"


def is_coupe_flaguee(categorie: TriageCategory) -> bool:
    """Une coupe est transmise aux Modèles 2 et 3 si elle n'est pas normale."""
    return categorie != "normal"


def resolve_niveau_risque(
    probabilite: float,
    niveau_risque: str | None = None,
    thresholds: TriageThresholds | None = None,
) -> TriageCategory:
    """Niveau de risque effectif — DB en priorité, sinon triage Modèle 1."""
    if niveau_risque in ("normal", "incertain", "eleve"):
        return niveau_risque  # type: ignore[return-value]
    return classifier_triage(probabilite, thresholds or load_triage_thresholds())


def is_vertebra_at_risk(
    probabilite: float,
    niveau_risque: str | None = None,
    thresholds: TriageThresholds | None = None,
) -> bool:
    """Vertèbre à surveiller si incertain ou élevé (pas de seuil 0.30 arbitraire)."""
    return resolve_niveau_risque(probabilite, niveau_risque, thresholds) != "normal"


def niveau_risque_label(niveau: TriageCategory) -> str:
    labels = {
        "normal": "Normal",
        "incertain": "Surveillance",
        "eleve": "Fracture suspectée",
    }
    return labels[niveau]
