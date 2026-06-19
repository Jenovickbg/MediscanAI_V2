from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analyse import router as analyse_router
from app.api.stats import router as stats_router
from app.api.auth import router as auth_router
from app.api.demo import router as demo_router
from app.api.examens import router as examens_router
from app.api.health import router as health_router
from app.api.images import router as images_router
from app.core.config import settings
from app.core.database import init_db

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API MediScanAI — Aide au diagnostic de fractures cervicales",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(auth_router, prefix="/api")
app.include_router(examens_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(analyse_router, prefix="/api")
app.include_router(images_router, prefix="/api")
app.include_router(demo_router, prefix="/api")


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    # Initialise le pipeline IA au démarrage (singleton)
    from app.services.pipeline_service import pipeline_service  # noqa: F401
