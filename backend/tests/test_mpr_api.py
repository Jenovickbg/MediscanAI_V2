from fastapi.testclient import TestClient

from tests.conftest import wait_for_analysis


def test_get_mpr_axial_png(
    client: TestClient,
    auth_headers: dict[str, str],
    demo_study_id: str,
):
    response = client.get(
        f"/api/images/{demo_study_id}/mpr/axial/0",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_get_mpr_invalid_view(
    client: TestClient,
    auth_headers: dict[str, str],
    demo_study_id: str,
):
    response = client.get(
        f"/api/images/{demo_study_id}/mpr/oblique/0",
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_analysis_results_new_contract(
    client: TestClient,
    auth_headers: dict[str, str],
    demo_study_id: str,
):
    client.post(f"/api/analyse/{demo_study_id}", headers=auth_headers)
    wait_for_analysis(client, demo_study_id, auth_headers)

    response = client.get(f"/api/analyse/{demo_study_id}/resultats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert "scores_par_vertebre" in data
    assert "scores_vertebres" not in data
    assert isinstance(data["scores_par_vertebre"], dict)
    assert data["fracture_detectee"] is True
    assert "C5" in data["scores_par_vertebre"]

    c5 = data["scores_par_vertebre"]["C5"]
    assert c5["niveau_risque"] in ("normal", "incertain", "eleve")
    assert "probabilite" in c5
    assert "coupe_reference" in c5
