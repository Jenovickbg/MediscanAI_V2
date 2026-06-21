from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BoundingBoxSchema(BaseModel):
    x: int
    y: int
    w: int
    h: int


class VertebreResultatSchema(BaseModel):
    probabilite: float
    bounding_box: BoundingBoxSchema | None = None
    coupe_reference: int
    niveau_risque: str


class ResultatAnalyseSchema(BaseModel):
    study_id: str
    score_global: float
    fracture_detectee: bool
    scores_par_vertebre: dict[str, VertebreResultatSchema]
    rapport_clinique: str
    date_analyse: datetime
    duree_analyse_sec: float
    seuil_utilise: float
    mode_mock: bool = False


class AnalyseStartResponse(BaseModel):
    task_id: str
    study_id: str


class AnalyseStatusSchema(BaseModel):
    study_id: str
    status: str
    progress: int = Field(ge=0, le=100)
    error: str | None = None
