"""Task 6.1 tests for objective CRUD, lifecycle, priority, and tenant isolation."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.objective_service import (
    STATUS_ABANDONED,
    STATUS_ACTIVE,
    STATUS_COMPLETED,
    STATUS_SUPERSEDED,
)


def _client() -> TestClient:
    return TestClient(app)


def _signup(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Founder",
            "email": f"founder-{uuid.uuid4()}@example.com",
            "password": "valid-pass-1",
        },
    )
    assert response.status_code == 201


def _create_company(client: TestClient, name: str = "Objective Co") -> dict:
    response = client.post(
        "/api/v1/companies",
        json={
            "name": name,
            "description": "desc",
            "target_customer": "founders",
            "stage": "mvp",
        },
    )
    assert response.status_code == 201
    return response.json()


def _objectives_url(company_id: str, objective_id: str | None = None) -> str:
    base = f"/api/v1/companies/{company_id}/objectives"
    return f"{base}/{objective_id}" if objective_id else base


def _create_objective(
    client: TestClient,
    company_id: str,
    *,
    title: str,
    priority: int = 100,
    target_value: str | None = None,
) -> dict:
    payload: dict[str, object] = {
        "title": title,
        "description": f"{title} description",
        "priority": priority,
        "target_unit": "customers",
    }
    if target_value is not None:
        payload["target_value"] = target_value
    response = client.post(_objectives_url(company_id), json=payload)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def founder_client() -> tuple[TestClient, dict]:
    client = _client()
    _signup(client)
    company = _create_company(client)
    return client, company


def test_create_objective(founder_client: tuple[TestClient, dict]) -> None:
    client, company = founder_client
    body = _create_objective(
        client,
        company["id"],
        title="Ship MVP",
        priority=200,
        target_value="100",
    )
    assert body["title"] == "Ship MVP"
    assert body["status"] == STATUS_ACTIVE
    assert body["priority"] == 200
    assert body["company_id"] == company["id"]
    assert body["target_value"] == "100"


def test_list_objectives(founder_client: tuple[TestClient, dict]) -> None:
    client, company = founder_client
    first = _create_objective(client, company["id"], title="First", priority=50)
    second = _create_objective(client, company["id"], title="Second", priority=150)
    response = client.get(_objectives_url(company["id"]))
    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["objectives"]] == [second["id"], first["id"]]


def test_retrieve_objective(founder_client: tuple[TestClient, dict]) -> None:
    client, company = founder_client
    created = _create_objective(client, company["id"], title="Retrieve me")
    response = client.get(_objectives_url(company["id"], created["id"]))
    assert response.status_code == 200
    assert response.json()["title"] == "Retrieve me"


def test_update_objective_fields(founder_client: tuple[TestClient, dict]) -> None:
    client, company = founder_client
    created = _create_objective(client, company["id"], title="Old title")
    response = client.patch(
        _objectives_url(company["id"], created["id"]),
        json={
            "title": "New title",
            "description": "Updated description",
            "target_value": "100",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "New title"
    assert body["description"] == "Updated description"
    assert body["target_value"] == "100"


def test_change_priority(founder_client: tuple[TestClient, dict]) -> None:
    client, company = founder_client
    created = _create_objective(client, company["id"], title="Priority", priority=10)
    response = client.patch(
        _objectives_url(company["id"], created["id"]),
        json={"priority": 500},
    )
    assert response.status_code == 200
    assert response.json()["priority"] == 500


def test_complete_active_objective(founder_client: tuple[TestClient, dict]) -> None:
    client, company = founder_client
    created = _create_objective(client, company["id"], title="Complete me")
    response = client.patch(
        _objectives_url(company["id"], created["id"]),
        json={"status": STATUS_COMPLETED},
    )
    assert response.status_code == 200
    assert response.json()["status"] == STATUS_COMPLETED


def test_abandon_active_objective(founder_client: tuple[TestClient, dict]) -> None:
    client, company = founder_client
    created = _create_objective(client, company["id"], title="Abandon me")
    response = client.patch(
        _objectives_url(company["id"], created["id"]),
        json={"status": STATUS_ABANDONED},
    )
    assert response.status_code == 200
    assert response.json()["status"] == STATUS_ABANDONED


def test_supersede_active_objective(founder_client: tuple[TestClient, dict]) -> None:
    client, company = founder_client
    created = _create_objective(client, company["id"], title="Supersede me")
    response = client.patch(
        _objectives_url(company["id"], created["id"]),
        json={"status": STATUS_SUPERSEDED},
    )
    assert response.status_code == 200
    assert response.json()["status"] == STATUS_SUPERSEDED


@pytest.mark.parametrize(
    "from_status",
    [STATUS_COMPLETED, STATUS_ABANDONED, STATUS_SUPERSEDED],
)
def test_invalid_lifecycle_transition_is_rejected(
    founder_client: tuple[TestClient, dict],
    from_status: str,
) -> None:
    client, company = founder_client
    created = _create_objective(client, company["id"], title="Terminal")
    client.patch(
        _objectives_url(company["id"], created["id"]),
        json={"status": from_status},
    )
    response = client.patch(
        _objectives_url(company["id"], created["id"]),
        json={"status": STATUS_ACTIVE},
    )
    assert response.status_code == 400


def test_current_objective_is_highest_priority_active(
    founder_client: tuple[TestClient, dict],
) -> None:
    client, company = founder_client
    low = _create_objective(client, company["id"], title="Low", priority=10)
    high = _create_objective(client, company["id"], title="High", priority=300)
    completed = _create_objective(client, company["id"], title="Done", priority=999)
    client.patch(
        _objectives_url(company["id"], completed["id"]),
        json={"status": STATUS_COMPLETED},
    )
    response = client.get(_objectives_url(company["id"]))
    assert response.status_code == 200
    current = response.json()["current_objective"]
    assert current is not None
    assert current["id"] == high["id"]
    assert low["id"] != current["id"]


def test_no_active_objective_returns_null_current(
    founder_client: tuple[TestClient, dict],
) -> None:
    client, company = founder_client
    created = _create_objective(client, company["id"], title="Only one")
    client.patch(
        _objectives_url(company["id"], created["id"]),
        json={"status": STATUS_COMPLETED},
    )
    response = client.get(_objectives_url(company["id"]))
    assert response.status_code == 200
    assert response.json()["current_objective"] is None


def test_equal_priority_objectives_have_deterministic_ordering(
    founder_client: tuple[TestClient, dict],
) -> None:
    client, company = founder_client
    first = _create_objective(client, company["id"], title="First equal", priority=100)
    second = _create_objective(client, company["id"], title="Second equal", priority=100)
    response = client.get(_objectives_url(company["id"]))
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["objectives"]]
    assert ids.index(first["id"]) < ids.index(second["id"])
    assert response.json()["current_objective"]["id"] == second["id"]


def test_unauthenticated_requests_return_401() -> None:
    client = _client()
    company_id = str(uuid.uuid4())
    assert client.get(_objectives_url(company_id)).status_code == 401
    assert client.post(_objectives_url(company_id), json={"title": "x"}).status_code == 401
    objective_id = str(uuid.uuid4())
    assert client.get(_objectives_url(company_id, objective_id)).status_code == 401
    assert client.patch(_objectives_url(company_id, objective_id), json={"title": "x"}).status_code == 401


def test_non_member_cannot_access_objectives() -> None:
    owner = _client()
    _signup(owner)
    company = _create_company(owner, name="Owner Co")
    owner.post(_objectives_url(company["id"]), json={"title": "Owner objective"})

    stranger = _client()
    _signup(stranger)
    assert stranger.get(_objectives_url(company["id"])).status_code == 403
    assert (
        stranger.post(_objectives_url(company["id"]), json={"title": "Hack"}).status_code == 403
    )


def test_company_a_cannot_read_company_b_objectives() -> None:
    owner_a = _client()
    _signup(owner_a)
    company_a = _create_company(owner_a, name="Company A")
    created = _create_objective(owner_a, company_a["id"], title="Secret A")

    owner_b = _client()
    _signup(owner_b)
    _create_company(owner_b, name="Company B")

    assert owner_b.get(_objectives_url(company_a["id"])).status_code == 403
    assert owner_b.get(_objectives_url(company_a["id"], created["id"])).status_code == 403


def test_company_a_cannot_modify_company_b_objectives() -> None:
    owner_a = _client()
    _signup(owner_a)
    company_a = _create_company(owner_a, name="Company A")
    created = _create_objective(owner_a, company_a["id"], title="Secret A")

    owner_b = _client()
    _signup(owner_b)
    _create_company(owner_b, name="Company B")

    response = owner_b.patch(
        _objectives_url(company_a["id"], created["id"]),
        json={"title": "Hijacked"},
    )
    assert response.status_code == 403


def test_foreign_objective_uuid_returns_404() -> None:
    owner_a = _client()
    _signup(owner_a)
    company_a = _create_company(owner_a, name="Company A")
    created = _create_objective(owner_a, company_a["id"], title="A objective")

    owner_b = _client()
    _signup(owner_b)
    company_b = _create_company(owner_b, name="Company B")

    response = owner_b.get(_objectives_url(company_b["id"], created["id"]))
    assert response.status_code == 404
