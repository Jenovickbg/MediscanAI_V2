from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crée les tables SQLite au démarrage et applique les migrations légères."""
    from app.models import examen, resultat, utilisateur  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _configure_sqlite()
    _migrate_sqlite_schema()

    db = SessionLocal()
    try:
        from app.services.seed import seed_default_users

        seed_default_users(db)
    finally:
        db.close()


def _configure_sqlite() -> None:
    """WAL + délai d'attente — évite les erreurs 500 pendant l'analyse CPU."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    from sqlalchemy import text

    with engine.connect() as connection:
        connection.execute(text("PRAGMA journal_mode=WAL"))
        connection.execute(text("PRAGMA busy_timeout=30000"))
        connection.commit()


def _migrate_sqlite_schema() -> None:
    """Ajoute les colonnes manquantes sur SQLite sans Alembic."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if "scores_vertebres" in table_names:
        columns = {col["name"] for col in inspector.get_columns("scores_vertebres")}
        if "niveau_risque" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE scores_vertebres ADD COLUMN niveau_risque VARCHAR(16)")
                )

        columns = {col["name"] for col in inspector.get_columns("scores_vertebres")}
        if "confiance_vertebre" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE scores_vertebres ADD COLUMN confiance_vertebre FLOAT")
                )

    if "utilisateurs" in table_names:
        user_columns = {col["name"] for col in inspector.get_columns("utilisateurs")}
        if "actif" not in user_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE utilisateurs ADD COLUMN actif INTEGER NOT NULL DEFAULT 1")
                )
