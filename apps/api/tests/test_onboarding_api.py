"""HTTP tests for onboarding draft GET/PATCH."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import app
from app.models.company_member import CompanyMember
from app.models.onboarding_draft import OnboardingDraft


def _client() -> TestClient:
    return TestClient(app)


def _signup(client: TestClient) -> dict[str, str]:
    email = f"founder-{uuid.uuid4()}@example.com"
    password = "valid-pass-1"
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Founder", "email": email, "password": password},
    )
    assert response.status_code == 201
    return {"email": email, "password": password}


def _create_company(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/companies",
        json={
            "name": "Draft Co",
            "description": "desc",
            "target_customer": "founders",
            "stage": "mvp",
        },
    )
    assert response.status_code == 201
    return response.json()


def _draft_url(company_id: str) -> str:
    return f"/api/v1/companies/{company_id}/onboarding/draft"


def test_flat_payload_aliases_are_normalized() -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    url = _draft_url(company["id"])

    patched = client.patch(
        url,
        json={
            "payload": {
                "company_name": "Forge AI",
                "mission": "Help solo founders build with AI leverage.",
                "vision": "Give small teams operating leverage.",
                "product_description": "AI operating system for solo founders.",
                "target_customer": "Technical solo founders",
                "stage": "mvp",
            },
            "current_step": 1,
            "status": "draft",
        },
    )
    assert patched.status_code == 200
    payload = patched.json()["payload"]
    assert payload["company"]["name"] == "Forge AI"
    assert payload["company"]["product_description"] == "AI operating system for solo founders."
    assert payload["customer"]["target_customer"] == "Technical solo founders"
    assert payload["context"]["mission"] == "Help solo founders build with AI leverage."
    assert payload["context"]["non_goals"] == "Give small teams operating leverage."


def test_founder_can_get_draft_before_first_patch() -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)

    fetched = client.get(_draft_url(company["id"]))
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["company_id"] == company["id"]
    assert body["current_step"] == 1
    assert body["status"] == "draft"
    assert body["payload"]["company"]["name"] == "Draft Co"


def test_founder_can_patch_and_get_draft() -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)

    patched = client.patch(
        _draft_url(company["id"]),
        json={"payload": {"company": {"name": "Forge"}}, "current_step": 2},
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["company_id"] == company["id"]
    assert body["payload"]["company"]["name"] == "Forge"
    assert body["current_step"] == 2
    assert body["status"] == "draft"
    assert "confirmed_at" not in body
    assert "confirmed_by_user_id" not in body

    fetched = client.get(_draft_url(company["id"]))
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]
    assert fetched.json()["payload"]["company"]["name"] == "Forge"


def test_partial_patch_preserves_unrelated_fields() -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    url = _draft_url(company["id"])

    first = client.patch(
        url,
        json={
            "payload": {
                "company": {"name": "Forge", "stage": "mvp"},
                "customer": {"target_customer": "solo founders"},
            }
        },
    )
    assert first.status_code == 200

    second = client.patch(
        url,
        json={"payload": {"company": {"name": "Forge OS"}}},
    )
    assert second.status_code == 200
    payload = second.json()["payload"]
    assert payload["company"]["name"] == "Forge OS"
    assert payload["company"]["stage"] == "mvp"
    assert payload["customer"]["target_customer"] == "solo founders"
    assert "current_situation" in payload
    assert "context" in payload


def test_multiple_patches_do_not_create_duplicate_drafts() -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    url = _draft_url(company["id"])

    responses = [
        client.patch(url, json={"payload": {"company": {"name": f"v{i}"}}})
        for i in range(4)
    ]
    assert all(item.status_code == 200 for item in responses)
    ids = {item.json()["id"] for item in responses}
    assert len(ids) == 1
    assert responses[-1].json()["payload"]["company"]["name"] == "v3"


def test_current_step_persists() -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    url = _draft_url(company["id"])

    patched = client.patch(url, json={"current_step": 4})
    assert patched.status_code == 200
    assert patched.json()["current_step"] == 4
    assert client.get(url).json()["current_step"] == 4


def test_draft_survives_new_request_and_login() -> None:
    client = _client()
    creds = _signup(client)
    company = _create_company(client)
    url = _draft_url(company["id"])
    client.patch(
        url,
        json={"payload": {"context": {"mission": "help founders"}}, "current_step": 3},
    )

    resumed = _client()
    login = resumed.post(
        "/api/v1/auth/login",
        json={"email": creds["email"], "password": creds["password"]},
    )
    assert login.status_code == 200
    fetched = resumed.get(url)
    assert fetched.status_code == 200
    assert fetched.json()["current_step"] == 3
    assert fetched.json()["payload"]["context"]["mission"] == "help founders"


def test_unauthenticated_draft_requests_return_401() -> None:
    client = _client()
    company_id = uuid.uuid4()
    assert client.get(_draft_url(str(company_id))).status_code == 401
    assert client.patch(_draft_url(str(company_id)), json={"current_step": 2}).status_code == 401


def test_other_company_draft_access_returns_403() -> None:
    owner = _client()
    _signup(owner)
    company = _create_company(owner)
    owner.patch(_draft_url(company["id"]), json={"current_step": 2})

    stranger = _client()
    _signup(stranger)
    assert stranger.get(_draft_url(company["id"])).status_code == 403
    assert stranger.patch(_draft_url(company["id"]), json={"current_step": 3}).status_code == 403


def test_invalid_payload_returns_validation_error() -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    url = _draft_url(company["id"])

    assert client.patch(url, json={"payload": ["not", "an", "object"]}).status_code == 422
    assert client.patch(url, json={"payload": {"company": "Forge"}}).status_code == 422
    assert client.patch(url, json={"current_step": 0}).status_code == 422
    assert client.patch(url, json={"status": "confirmed"}).status_code == 422


@pytest.mark.asyncio
async def test_member_cannot_modify_draft(async_session_factory) -> None:
    founder = _client()
    _signup(founder)
    company = _create_company(founder)
    url = _draft_url(company["id"])
    created = founder.patch(url, json={"payload": {"company": {"name": "Forge"}}})
    assert created.status_code == 200

    member = _client()
    _signup(member)
    me = member.get("/api/v1/auth/me")
    assert me.status_code == 200
    member_user_id = uuid.UUID(me.json()["id"])

    async with async_session_factory() as session:
        session.add(
            CompanyMember(
                company_id=uuid.UUID(company["id"]),
                user_id=member_user_id,
                role="member",
            )
        )
        await session.commit()

    assert member.get(url).status_code == 200
    assert member.patch(url, json={"current_step": 3}).status_code == 403

    async with async_session_factory() as session:
        count = await session.execute(
            select(func.count()).select_from(OnboardingDraft).where(
                OnboardingDraft.company_id == uuid.UUID(company["id"])
            )
        )
        assert count.scalar_one() == 1


@pytest.mark.asyncio
async def test_multiple_patches_leave_one_row(async_session_factory) -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    url = _draft_url(company["id"])
    client.patch(url, json={"current_step": 1})
    client.patch(url, json={"current_step": 2})
    client.patch(url, json={"current_step": 2})

    async with async_session_factory() as session:
        count = await session.execute(
            select(func.count()).select_from(OnboardingDraft).where(
                OnboardingDraft.company_id == uuid.UUID(company["id"])
            )
        )
        assert count.scalar_one() == 1
