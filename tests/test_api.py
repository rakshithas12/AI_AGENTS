from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.database import initialize_database
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDENT_DB_PATH", str(tmp_path / "students.db"))
    monkeypatch.setenv("AI_ENABLED", "false")
    with TestClient(app) as test_client:
        yield test_client


def sample_student(student_id="STU-001"):
    return {
        "student_id": student_id,
        "name": "Alex Example",
        "date_of_birth": "2005-04-12",
        "email": "alex@example.com",
        "course": "Python Backend",
        "enrollment_date": "2026-09-01",
    }


def test_create_list_filter_and_get_persisted_record(client):
    response = client.post("/students", json=sample_student())
    assert response.status_code == 201
    assert response.json()["student_id"] == "STU-001"
    assert response.json()["date_of_birth"] == "2005-04-12"
    assert client.get("/students").json()["total"] == 1
    filtered = client.get("/students", params={"course": "backend", "dob_after": "2000-01-01"})
    assert filtered.json()["items"][0]["student_id"] == "STU-001"
    assert client.get("/students/STU-001").status_code == 200


def test_duplicate_missing_and_validation_errors(client):
    assert client.post("/students", json=sample_student()).status_code == 201
    assert client.post("/students", json=sample_student()).status_code == 409
    assert client.get("/students/absent").status_code == 404
    no_contact = sample_student("STU-002")
    no_contact.pop("email")
    assert client.post("/students", json=no_contact).status_code == 422
    assert client.delete("/students/absent").status_code == 404


def test_patch_put_and_delete(client):
    client.post("/students", json=sample_student())
    rejected = client.patch("/students/STU-001", json={"email": None})
    assert rejected.status_code == 422
    patched = client.patch("/students/STU-001", json={"phone": "+1-555-0100"})
    assert patched.status_code == 200
    assert patched.json()["email"] == "alex@example.com"
    assert patched.json()["phone"] == "+1-555-0100"
    replaced = client.put(
        "/students/STU-001",
        json={"name": "Alex Updated", "date_of_birth": "2005-04-12", "phone": "+1-555-0100"},
    )
    assert replaced.status_code == 200
    assert replaced.json()["name"] == "Alex Updated"
    assert client.delete("/students/STU-001").status_code == 204
    assert client.get("/students/STU-001").status_code == 404


def test_list_validation_and_ai_disabled(client):
    assert client.get("/students", params={"limit": 0}).status_code == 422
    assert client.get("/students", params={"dob_after": "2020-01-01", "dob_before": "2000-01-01"}).status_code == 422
    assert client.post("/ask", json={"question": "How many students?"}).status_code == 404
