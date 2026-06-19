import os
import tempfile
import time
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

TEST_DB_PATH = Path(tempfile.gettempdir()) / "mediscanai_pytest.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402

DEFAULT_EMAIL = "dr.kabila@mediscanai.cd"
DEFAULT_PASSWORD = "Medecin2025!"


@pytest.fixture(scope="session", autouse=True)
def prepare_database() -> Generator[None, None, None]:
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink(missing_ok=True)
    init_db()
    yield
    from app.core.database import engine

    engine.dispose()
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except PermissionError:
            pass


@pytest.fixture
def db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": DEFAULT_EMAIL, "password": DEFAULT_PASSWORD},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def demo_study_id(client: TestClient, auth_headers: dict[str, str]) -> str:
    response = client.get("/api/demo/load-sample", headers=auth_headers)
    assert response.status_code == 200, response.text
    study_id = response.json()["study_id"]
    assert study_id
    return study_id


def wait_for_analysis(client: TestClient, study_id: str, headers: dict[str, str]) -> None:
    for _ in range(50):
        response = client.get(f"/api/analyse/{study_id}/status", headers=headers)
        assert response.status_code == 200
        if response.json()["status"] == "done":
            return
        if response.json()["status"] == "error":
            pytest.fail(f"Analyse en erreur: {response.json().get('error')}")
        time.sleep(0.1)
    pytest.fail("Timeout en attente de l'analyse IA")
