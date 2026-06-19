from datetime import datetime

from pydantic import BaseModel, Field


class ScoreVertebreSchema(BaseModel):
    vertebre: str
    probabilite: float
    localisation: str
    bounding_box_x: float
    bounding_box_y: float
    bounding_box_w: float
    bounding_box_h: float
    coupe_reference: int


class ResultatAnalyseSchema(BaseModel):
    study_id: str
    score_global: float
    fracture_detectee: bool
    scores_vertebres: list[ScoreVertebreSchema]
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
