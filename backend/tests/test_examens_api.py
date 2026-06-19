from fastapi.testclient import TestClient


def test_demo_load_sample(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/demo/load-sample", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["finalized"] is True
    assert body["study_id"]
    assert body["nb_coupes"] > 0
    assert body["metadata"]["patient_id"]
    assert len(body["preview_slices"]) > 0


def test_demo_requires_auth(client: TestClient) -> None:
    response = client.get("/api/demo/load-sample")
    assert response.status_code == 401


def test_upload_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/examens/upload",
        data={"patient_id": "TEST-001"},
        files=[("files", ("test.dcm", b"fake", "application/octet-stream"))],
    )
    assert response.status_code == 401


def test_upload_requires_patient_id(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/examens/upload",
        headers=auth_headers,
        data={"patient_id": "  "},
        files=[("files", ("test.dcm", b"fake", "application/octet-stream"))],
    )
    assert response.status_code == 400


def test_upload_requires_files(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/examens/upload",
        headers=auth_headers,
        data={"patient_id": "TEST-001"},
    )
    assert response.status_code == 422


def test_get_examen_after_demo(client: TestClient, auth_headers: dict[str, str], demo_study_id: str) -> None:
    response = client.get(f"/api/examens/{demo_study_id}", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["study_instance_uid"] == demo_study_id
    assert body["nb_coupes"] > 0
