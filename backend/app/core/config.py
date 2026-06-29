from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "MediScanAI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./mediscanai.db"

    SECRET_KEY: str = "change-me-in-production-mediscanai-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    MODEL_PATH: str = "model/model1_classifier_densenet121.pth"
    MODEL_1_PATH: str = "model/model1_classifier_densenet121.pth"
    MODEL_2_PATH: str = "model/model2_fasterrcnn.pth"
    MODEL_3_PATH: str = "model/model3_vertebra_densenet121.pth"
    TRIAGE_THRESHOLDS_PATH: str = "config/triage_thresholds.json"
    DATA_DIR: Path = BACKEND_DIR.parent / "data"
    CACHE_DIR: Path = BACKEND_DIR / "cache"
    UPLOAD_DIR: Path = BACKEND_DIR.parent / "data" / "uploads"
    SAMPLE_DIR: Path = BACKEND_DIR.parent / "data" / "sample"
    TEMP_UPLOAD_DIR: Path = BACKEND_DIR / "cache" / "uploads_temp"

    UPLOAD_CHUNK_SIZE: int = 50

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()

# Crée les dossiers nécessaires au démarrage
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
(BACKEND_DIR / "config").mkdir(parents=True, exist_ok=True)
