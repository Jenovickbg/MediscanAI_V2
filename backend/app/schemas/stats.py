from datetime import date, datetime

from pydantic import BaseModel, Field


class RecentExamenSchema(BaseModel):
    study_id: str
    patient_id: str
    date: datetime
    vertebres: list[str] = Field(default_factory=list)
    score_global: float | None = None
    fracture_detectee: bool | None = None
    analysed: bool = False


class DashboardStatsSchema(BaseModel):
    today_exams: int
    month_fractures: int
    avg_score: float
    avg_time: float
    recent_exams: list[RecentExamenSchema]


class DailyCountSchema(BaseModel):
    date: date
    count: int


class ResultDistributionSchema(BaseModel):
    label: str
    value: int


class VertebraStatSchema(BaseModel):
    vertebre: str
    fracture_count: int
    avg_score: float


class RecallMetricsSchema(BaseModel):
    recall: float
    auc: float
    f1: float
    model_name: str


class HistoriqueStatsSchema(BaseModel):
    period: str
    daily_counts: list[DailyCountSchema]
    result_distribution: list[ResultDistributionSchema]
    vertebrae_distribution: list[VertebraStatSchema]
    recall_metrics: RecallMetricsSchema
