from fastapi import APIRouter

from app.services.pipeline_service import pipeline_service

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str | bool]:
    """Vérifie que l'API et le modèle IA sont disponibles."""
    from app.core.config import settings

    return {
        "status": "ok",
        "model_loaded": pipeline_service.model_loaded,
        "mock_mode": pipeline_service.use_mock,
        "version": settings.APP_VERSION,
    }
