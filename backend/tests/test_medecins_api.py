from fastapi.testclient import TestClient

ADMIN_EMAIL = "admin@mediscanai.cd"
ADMIN_PASSWORD = "Admin2025!"
MEDECIN_EMAIL = "dr.kabila@mediscanai.cd"
MEDECIN_PASSWORD = "Medecin2025!"


def _login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_medecins_requires_admin(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/medecins", headers=auth_headers)
    assert response.status_code == 403


def test_medecins_crud(client: TestClient) -> None:
    admin_headers = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)

    list_response = client.get("/api/medecins", headers=admin_headers)
    assert list_response.status_code == 200
    initial_count = len(list_response.json())
    assert initial_count >= 1

    create_response = client.post(
        "/api/medecins",
        headers=admin_headers,
        json={
            "email": "dr.test@mediscanai.cd",
            "nom": "Dr. Test",
            "password": "Test2025!!",
            "actif": True,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    medecin_id = created["id"]
    assert created["email"] == "dr.test@mediscanai.cd"
    assert created["actif"] is True

    update_response = client.put(
        f"/api/medecins/{medecin_id}",
        headers=admin_headers,
        json={"nom": "Dr. Test Modifié", "actif": False},
    )
    assert update_response.status_code == 200
    assert update_response.json()["nom"] == "Dr. Test Modifié"
    assert update_response.json()["actif"] is False

    login_inactive = client.post(
        "/api/auth/login",
        json={"email": "dr.test@mediscanai.cd", "password": "Test2025!!"},
    )
    assert login_inactive.status_code == 403

    delete_response = client.delete(f"/api/medecins/{medecin_id}", headers=admin_headers)
    assert delete_response.status_code == 200


def test_medecin_sees_only_own_examens(client: TestClient) -> None:
    medecin_headers = _login(client, MEDECIN_EMAIL, MEDECIN_PASSWORD)
    admin_headers = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)

    client.post(
        "/api/medecins",
        headers=admin_headers,
        json={
            "email": "dr.test2@mediscanai.cd",
            "nom": "Dr. Test 2",
            "password": "Test2025!!",
            "actif": True,
        },
    )
    other_headers = _login(client, "dr.test2@mediscanai.cd", "Test2025!!")

    demo = client.get("/api/demo/load-sample", headers=medecin_headers)
    assert demo.status_code == 200
    study_id = demo.json()["study_id"]

    medecin_list = client.get("/api/examens", headers=medecin_headers)
    assert medecin_list.status_code == 200
    assert study_id in {item["study_id"] for item in medecin_list.json()["items"]}

    other_list = client.get("/api/examens", headers=other_headers)
    assert other_list.status_code == 200
    assert study_id not in {item["study_id"] for item in other_list.json()["items"]}

    forbidden = client.get(f"/api/examens/{study_id}", headers=other_headers)
    assert forbidden.status_code == 403
