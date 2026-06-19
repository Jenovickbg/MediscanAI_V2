from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.utilisateur import Utilisateur
from app.schemas.stats import DashboardStatsSchema, HistoriqueStatsSchema
from app.services.stats_service import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/dashboard", response_model=DashboardStatsSchema)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> DashboardStatsSchema:
    data = stats_service.get_dashboard(db)
    return DashboardStatsSchema.model_validate(data)


@router.get("/historique", response_model=HistoriqueStatsSchema)
def get_historique_stats(
    period: str = Query(default="30d", pattern="^(7d|30d|90d)$"),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> HistoriqueStatsSchema:
    data = stats_service.get_historique(db, period=period)  # type: ignore[arg-type]
    return HistoriqueStatsSchema.model_validate(data)
