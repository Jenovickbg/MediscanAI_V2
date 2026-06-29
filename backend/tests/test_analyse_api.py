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


def test_results_schema_tolerates_nan_bbox():
    from datetime import datetime, timezone

    from app.api.analyse import _to_schema
    from app.models.resultat import ResultatAnalyse, ScoreVertebre

    resultat = ResultatAnalyse(
        study_instance_uid="NAN-STUDY",
        fracture_detectee=True,
        score_global=0.5,
        rapport_clinique="Test",
        date_analyse=datetime.now(timezone.utc),
        duree_analyse_sec=1.0,
        seuil_utilise=0.15,
        mode_mock=False,
    )
    resultat.score_global = float("nan")
    resultat.scores_vertebres = [
        ScoreVertebre(
            resultat_id=1,
            vertebre="C5",
            probabilite=float("nan"),
            localisation="Test",
            bounding_box_x=float("nan"),
            bounding_box_y=0.1,
            bounding_box_w=0.2,
            bounding_box_h=0.2,
            coupe_reference=10,
            niveau_risque="eleve",
        )
    ]

    schema = _to_schema(resultat)
    assert schema.score_global == 0.0
    assert schema.scores_par_vertebre["C5"].probabilite == 0.0
    assert schema.scores_par_vertebre["C5"].bounding_box is None
