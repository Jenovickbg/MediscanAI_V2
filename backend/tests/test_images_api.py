from fastapi.testclient import TestClient

from tests.conftest import wait_for_analysis


def test_get_coupe_info_returns_dimensions(
    client: TestClient,
    auth_headers: dict[str, str],
    demo_study_id: str,
):
    response = client.get(f"/api/images/{demo_study_id}/coupes", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["nb_coupes"] > 0
    assert "width" in data
    assert "height" in data


def test_get_coupe_image_png(
    client: TestClient,
    auth_headers: dict[str, str],
    demo_study_id: str,
):
    response = client.get(
        f"/api/images/{demo_study_id}/coupe/0",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_get_gradcam_overlay_png(
    client: TestClient,
    auth_headers: dict[str, str],
    demo_study_id: str,
):
    response = client.get(
        f"/api/images/{demo_study_id}/gradcam/5",
        headers=auth_headers,
        params={"vertebra": "C5", "overlay": True},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert len(response.content) > 100


def test_get_reconstruction_3d_json(
    client: TestClient,
    auth_headers: dict[str, str],
    demo_study_id: str,
):
    client.post(f"/api/analyse/{demo_study_id}", headers=auth_headers)
    wait_for_analysis(client, demo_study_id, auth_headers)

    response = client.get(
        f"/api/images/{demo_study_id}/reconstruction-3d",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "vertices" in data
    assert "faces" in data
    assert len(data["vertices"]) > 0


def test_export_pdf_after_analysis(
    client: TestClient,
    auth_headers: dict[str, str],
    demo_study_id: str,
):
    client.post(f"/api/analyse/{demo_study_id}", headers=auth_headers)
    wait_for_analysis(client, demo_study_id, auth_headers)

    response = client.get(
        f"/api/images/{demo_study_id}/export-pdf",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


def test_images_require_auth(client: TestClient, demo_study_id: str):
    response = client.get(f"/api/images/{demo_study_id}/coupe/0")
    assert response.status_code == 401
