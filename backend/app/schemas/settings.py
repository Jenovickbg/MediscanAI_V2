from __future__ import annotations

from pydantic import BaseModel, Field


class TriageThresholdsSchema(BaseModel):
    seuil_bas: float = Field(ge=0.0, le=1.0)
    seuil_haut: float = Field(ge=0.0, le=1.0)
    score_thresh_rcnn: float = Field(ge=0.0, le=1.0)
    nms_thresh_rcnn: float = Field(ge=0.0, le=1.0)
    max_detections: int = Field(ge=1, le=20)
    derniere_maj: str = "2025-06"
    recall_garanti: float | None = None
    auc_modele1: float | None = None
    accuracy_modele3: float | None = None


class ModelStatusSchema(BaseModel):
    fichier_present: bool
    charge: bool
    mock: bool


class AppSettingsSchema(BaseModel):
    version: str
    device: str | None = None
    modeles: dict[str, ModelStatusSchema]
    seuils: TriageThresholdsSchema
