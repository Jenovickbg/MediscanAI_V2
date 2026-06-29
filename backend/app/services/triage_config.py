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
    "seuil_bas": 0.15,
    "seuil_haut": 0.30,
    "score_thresh_rcnn": 0.50,
    "nms_thresh_rcnn": 0.30,
    "max_detections": 3,
    "derniere_maj": "2025-06",
}


@dataclass(frozen=True)
class TriageThresholds:
    """Seuils de triage clinique du Modèle 1 et paramètres RCNN (Modèle 2)."""

    seuil_bas: float
    seuil_haut: float
    score_thresh_rcnn: float = 0.50
    nms_thresh_rcnn: float = 0.30
    max_detections: int = 3
    derniere_maj: str = "2025-06"


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
            score_thresh_rcnn=float(data.get("score_thresh_rcnn", 0.50)),
            nms_thresh_rcnn=float(data.get("nms_thresh_rcnn", 0.30)),
            max_detections=int(data.get("max_detections", 3)),
            derniere_maj=str(data.get("derniere_maj", "2025-06")),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Config triage invalide (%s) — valeurs par défaut: %s", config_path, exc)
        return TriageThresholds(**DEFAULT_THRESHOLDS)


def save_triage_thresholds(thresholds: TriageThresholds, path: Path | None = None) -> TriageThresholds:
    """Persiste les seuils dans le fichier JSON (conserve les métadonnées existantes)."""
    config_path = path or (BACKEND_DIR / settings.TRIAGE_THRESHOLDS_PATH)
    existing: dict = {}
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    payload = {
        **existing,
        "seuil_bas": thresholds.seuil_bas,
        "seuil_haut": thresholds.seuil_haut,
        "score_thresh_rcnn": thresholds.score_thresh_rcnn,
        "nms_thresh_rcnn": thresholds.nms_thresh_rcnn,
        "max_detections": thresholds.max_detections,
        "derniere_maj": thresholds.derniere_maj,
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return load_triage_thresholds(config_path)


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
