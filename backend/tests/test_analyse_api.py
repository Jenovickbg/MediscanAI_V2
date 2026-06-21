from fastapi.testclient import TestClient

from tests.conftest import wait_for_analysis


def test_start_analysis_returns_task(client: TestClient, auth_headers: dict[str, str], demo_study_id: str):
    response = client.post(f"/api/analyse/{demo_study_id}", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["study_id"] == demo_study_id
    assert body["task_id"]


def test_analysis_pipeline_produces_results(
    client: TestClient,
    auth_headers: dict[str, str],
    demo_study_id: str,
):
    start = client.post(f"/api/analyse/{demo_study_id}", headers=auth_headers)
    assert start.status_code == 200

    wait_for_analysis(client, demo_study_id, auth_headers)

    status = client.get(f"/api/analyse/{demo_study_id}/status", headers=auth_headers)
    assert status.status_code == 200
    assert status.json()["status"] == "done"
    assert status.json()["progress"] == 100

    results = client.get(f"/api/analyse/{demo_study_id}/resultats", headers=auth_headers)
    assert results.status_code == 200
    data = results.json()

    assert data["study_id"] == demo_study_id
    assert "scores_par_vertebre" in data
    assert data["rapport_clinique"]
    assert data["mode_mock"] is True
    assert 0.0 <= data["score_global"] <= 1.0


def test_analysis_unknown_study_returns_404(client: TestClient, auth_headers: dict[str, str]):
    response = client.post("/api/analyse/UNKNOWN-STUDY-ID", headers=auth_headers)
    assert response.status_code == 404


def test_results_before_analysis_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
    demo_study_id: str,
):
    response = client.get(f"/api/analyse/{demo_study_id}/resultats", headers=auth_headers)
    assert response.status_code == 404


def test_reanalysis_is_idempotent(
    client: TestClient,
    auth_headers: dict[str, str],
    demo_study_id: str,
):
    first = client.post(f"/api/analyse/{demo_study_id}", headers=auth_headers)
    assert first.status_code == 200
    wait_for_analysis(client, demo_study_id, auth_headers)

    second = client.post(f"/api/analyse/{demo_study_id}", headers=auth_headers)
    assert second.status_code == 200

    results = client.get(f"/api/analyse/{demo_study_id}/resultats", headers=auth_headers)
    assert results.status_code == 200
