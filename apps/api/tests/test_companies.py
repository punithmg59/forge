"""Company membership and access-control tests."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def _signup(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Founder",
            "email": f"founder-{uuid.uuid4()}@example.com",
            "password": "valid-pass-1",
        },
    )


def test_create_company_and_membership() -> None:
    client = _client()
    _signup(client)
    response = client.post(
        "/api/v1/companies",
        json={
            "name": "Northstar",
            "description": "AI OS for founders",
            "target_customer": "Solo founders",
            "stage": "mvp",
        },
    )
    assert response.status_code == 201
    company = response.json()
    assert company["name"] == "Northstar"
    assert company["description"] == "AI OS for founders"
    assert company["target_customer"] == "Solo founders"
    assert company["stage"] == "mvp"

    members = client.get(f"/api/v1/companies/{company['id']}/members")
    assert members.status_code == 200
    body = members.json()
    assert len(body) == 1
    assert body[0]["role"] == "founder"


def test_list_and_get_authorized_company() -> None:
    client = _client()
    _signup(client)
    created = client.post(
        "/api/v1/companies",
        json={"name": "Listed Co", "description": "d", "target_customer": "t", "stage": "idea"},
    )
    company_id = created.json()["id"]

    listed = client.get("/api/v1/companies")
    assert listed.status_code == 200
    ids = [item["id"] for item in listed.json()]
    assert company_id in ids

    fetched = client.get(f"/api/v1/companies/{company_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == company_id

    updated = client.patch(f"/api/v1/companies/{company_id}", json={"name": "Listed Co 2"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Listed Co 2"


def test_reject_unauthorized_company() -> None:
    owner = _client()
    _signup(owner)
    created = owner.post(
        "/api/v1/companies",
        json={
            "name": "Private Co",
            "description": "secret",
            "target_customer": "t",
            "stage": "mvp",
        },
    )
    company_id = created.json()["id"]

    stranger = _client()
    _signup(stranger)
    response = stranger.get(f"/api/v1/companies/{company_id}")
    assert response.status_code == 403
