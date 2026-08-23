"""Mandatory tenant isolation tests."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app


def _register(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Tenant User",
            "email": f"tenant-{uuid.uuid4()}@example.com",
            "password": "valid-pass-1",
        },
    )


def _create_company(client: TestClient, name: str) -> dict:
    response = client.post(
        "/api/v1/companies",
        json={
            "name": name,
            "description": f"{name} description",
            "target_customer": "founders",
            "stage": "mvp",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_user_a_cannot_access_company_b() -> None:
    user_a = TestClient(app)
    user_b = TestClient(app)
    _register(user_a)
    _register(user_b)

    company_a = _create_company(user_a, "Company A")
    company_b = _create_company(user_b, "Company B")

    listed_a = user_a.get("/api/v1/companies")
    listed_b = user_b.get("/api/v1/companies")
    assert company_a["id"] in [c["id"] for c in listed_a.json()]
    assert company_b["id"] not in [c["id"] for c in listed_a.json()]
    assert company_b["id"] in [c["id"] for c in listed_b.json()]
    assert company_a["id"] not in [c["id"] for c in listed_b.json()]

    assert user_a.get(f"/api/v1/companies/{company_b['id']}").status_code == 403
    assert user_a.patch(
        f"/api/v1/companies/{company_b['id']}",
        json={"name": "Hijacked"},
    ).status_code == 403
    assert user_a.get(f"/api/v1/companies/{company_b['id']}/members").status_code == 403

    # Direct company_id manipulation must not grant access.
    forged_id = company_b["id"]
    assert user_a.get(f"/api/v1/companies/{forged_id}").status_code == 403
    still_b = user_b.get(f"/api/v1/companies/{company_b['id']}")
    assert still_b.status_code == 200
    assert still_b.json()["name"] == "Company B"
    assert still_b.json()["name"] != "Hijacked"
