"""Tests API paramètres."""

from fastapi.testclient import TestClient

from tests.conftest import DEFAULT_EMAIL, DEFAULT_PASSWORD


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": DEFAULT_EMAIL, "password": DEFAULT_PASSWORD},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_settings_returns_thresholds(client: TestClient):
    headers = _auth_headers(client)
    response = client.get("/api/settings", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["seuils"]["seuil_bas"] == 0.15
    assert data["seuils"]["seuil_haut"] == 0.30
    assert "model1" in data["modeles"]


def test_update_thresholds_forbidden_for_medecin(client: TestClient):
    headers = _auth_headers(client)
    payload = {
        "seuil_bas": 0.15,
        "seuil_haut": 0.30,
        "score_thresh_rcnn": 0.50,
        "nms_thresh_rcnn": 0.30,
        "max_detections": 3,
        "derniere_maj": "2025-06",
    }
    response = client.put("/api/settings/thresholds", json=payload, headers=headers)
    assert response.status_code == 403


def test_update_thresholds_allowed_for_admin(client: TestClient):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@mediscanai.cd", "password": "Admin2025!"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    payload = {
        "seuil_bas": 0.16,
        "seuil_haut": 0.31,
        "score_thresh_rcnn": 0.50,
        "nms_thresh_rcnn": 0.30,
        "max_detections": 3,
        "derniere_maj": "2025-06-test",
    }
    response = client.put("/api/settings/thresholds", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["seuil_bas"] == 0.16

    # Restaurer les valeurs de production
    restore = {
        **payload,
        "seuil_bas": 0.15,
        "seuil_haut": 0.30,
        "derniere_maj": "2025-06",
    }
    client.put("/api/settings/thresholds", json=restore, headers=headers)
