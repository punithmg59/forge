"""HTTP and transaction tests for onboarding confirmation."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import app
from app.models.company import Company
from app.models.company_belief import CompanyBelief
from app.models.company_brain_profile import CompanyBrainProfile
from app.models.company_constraint import CompanyConstraint
from app.models.company_fact import CompanyFact
from app.models.company_member import CompanyMember
from app.models.decision import Decision
from app.models.objective import Objective
from app.models.onboarding_draft import OnboardingDraft
from app.services.onboarding_confirm import ONBOARDING_DECISION_TITLE, confirm_onboarding

BELIEF_STATEMENT = "We believe users leave because onboarding is confusing."


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
            "name": "Placeholder Co",
            "description": "placeholder",
            "target_customer": "placeholder",
            "stage": "idea",
        },
    )
    assert response.status_code == 201
    return response.json()


def _confirm_url(company_id: str) -> str:
    return f"/api/v1/companies/{company_id}/onboarding/confirm"


def _draft_url(company_id: str) -> str:
    return f"/api/v1/companies/{company_id}/onboarding/draft"


def _complete_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "company": {
            "name": "Forge",
            "product_description": "OS for solo founders",
            "stage": "mvp",
        },
        "customer": {
            "target_customer": "Ambitious solo founders",
            "beliefs": [BELIEF_STATEMENT],
            "paying_customers": 5,
        },
        "current_situation": {
            "objective": "Reach 20 paying customers",
            "bottleneck": "Limited engineering bandwidth",
            "deadline": "2026-12-31",
            "constraint": {
                "type": "budget",
                "name": "monthly_burn",
                "value": "4000",
                "description": "Stay under $4k monthly burn",
                "severity": "high",
            },
        },
        "context": {
            "mission": "Give every founder an AI co-founder",
            "non_goals": "Enterprise sales",
        },
    }
    payload.update(overrides)
    return payload


def _save_complete_draft(client: TestClient, company_id: str) -> None:
    response = client.patch(
        _draft_url(company_id),
        json={"payload": _complete_payload(), "current_step": 5},
    )
    assert response.status_code == 200


def test_unauthenticated_cannot_confirm() -> None:
    client = _client()
    assert client.post(_confirm_url(str(uuid.uuid4()))).status_code == 401


def test_other_company_cannot_confirm() -> None:
    owner = _client()
    _signup(owner)
    company = _create_company(owner)
    _save_complete_draft(owner, company["id"])

    stranger = _client()
    _signup(stranger)
    assert stranger.post(_confirm_url(company["id"])).status_code == 403


def test_founder_can_confirm_and_initialize_brain() -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    _save_complete_draft(client, company["id"])

    response = client.post(_confirm_url(company["id"]))
    assert response.status_code == 200
    body = response.json()
    assert body["brain_initialized"] is True
    assert body["draft"]["status"] == "confirmed"
    assert body["draft"]["company_id"] == company["id"]

    company_body = client.get(f"/api/v1/companies/{company['id']}").json()
    assert company_body["name"] == "Forge"
    assert company_body["description"] == "OS for solo founders"
    assert company_body["target_customer"] == "Ambitious solo founders"
    assert company_body["stage"] == "mvp"


@pytest.mark.asyncio
async def test_member_cannot_confirm(async_session_factory) -> None:
    founder = _client()
    _signup(founder)
    company = _create_company(founder)
    _save_complete_draft(founder, company["id"])

    member = _client()
    _signup(member)
    member_id = uuid.UUID(member.get("/api/v1/auth/me").json()["id"])
    async with async_session_factory() as session:
        session.add(
            CompanyMember(
                company_id=uuid.UUID(company["id"]),
                user_id=member_id,
                role="member",
            )
        )
        await session.commit()

    assert member.post(_confirm_url(company["id"])).status_code == 403


@pytest.mark.asyncio
async def test_confirmation_writes_brain_records(async_session_factory) -> None:
    client = _client()
    _signup(client)
    me = client.get("/api/v1/auth/me").json()
    company = _create_company(client)
    _save_complete_draft(client, company["id"])
    assert client.post(_confirm_url(company["id"])).status_code == 200
    company_id = uuid.UUID(company["id"])
    founder_id = uuid.UUID(me["id"])

    async with async_session_factory() as session:
        profile = (
            await session.execute(
                select(CompanyBrainProfile).where(CompanyBrainProfile.company_id == company_id)
            )
        ).scalar_one()
        assert profile.current_bottlenecks == "Limited engineering bandwidth"
        assert profile.non_goals == "Enterprise sales"
        assert profile.strategy is None
        assert profile.working_style is None

        db_company = await session.get(Company, company_id)
        assert db_company is not None
        assert db_company.mission == "Give every founder an AI co-founder"
        assert db_company.vision is None

        facts = (
            await session.execute(select(CompanyFact).where(CompanyFact.company_id == company_id))
        ).scalars().all()
        assert len(facts) == 1
        assert facts[0].key == "paying_customers"
        assert facts[0].value == "5"
        assert facts[0].source_type == "founder_input"
        assert facts[0].source_reference == f"onboarding:{company_id}"

        beliefs = (
            await session.execute(
                select(CompanyBelief).where(CompanyBelief.company_id == company_id)
            )
        ).scalars().all()
        assert len(beliefs) == 1
        assert beliefs[0].statement == BELIEF_STATEMENT
        assert beliefs[0].source == "founder_input"

        constraints = (
            await session.execute(
                select(CompanyConstraint).where(CompanyConstraint.company_id == company_id)
            )
        ).scalars().all()
        assert len(constraints) == 1
        assert constraints[0].type == "budget"
        assert constraints[0].value == "4000"

        objectives = (
            await session.execute(select(Objective).where(Objective.company_id == company_id))
        ).scalars().all()
        assert len(objectives) == 1
        assert objectives[0].title == "Reach 20 paying customers"
        assert objectives[0].created_by == founder_id
        assert objectives[0].deadline == "2026-12-31"

        decisions = (
            await session.execute(select(Decision).where(Decision.company_id == company_id))
        ).scalars().all()
        assert len(decisions) == 1
        assert decisions[0].title == ONBOARDING_DECISION_TITLE
        assert decisions[0].created_by == founder_id

        draft = (
            await session.execute(
                select(OnboardingDraft).where(OnboardingDraft.company_id == company_id)
            )
        ).scalar_one()
        assert draft.status == "confirmed"
        assert draft.confirmed_at is not None
        assert draft.confirmed_by_user_id == founder_id


@pytest.mark.asyncio
async def test_belief_is_not_stored_as_fact(async_session_factory) -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    _save_complete_draft(client, company["id"])
    assert client.post(_confirm_url(company["id"])).status_code == 200
    company_id = uuid.UUID(company["id"])

    async with async_session_factory() as session:
        beliefs = (
            await session.execute(
                select(CompanyBelief).where(CompanyBelief.company_id == company_id)
            )
        ).scalars().all()
        facts = (
            await session.execute(select(CompanyFact).where(CompanyFact.company_id == company_id))
        ).scalars().all()
        assert any(item.statement == BELIEF_STATEMENT for item in beliefs)
        assert all(BELIEF_STATEMENT not in (item.value, item.key) for item in facts)


@pytest.mark.asyncio
async def test_second_confirmation_is_idempotent(async_session_factory) -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    _save_complete_draft(client, company["id"])
    first = client.post(_confirm_url(company["id"]))
    second = client.post(_confirm_url(company["id"]))
    assert first.status_code == 200
    assert second.status_code == 200
    company_id = uuid.UUID(company["id"])

    async with async_session_factory() as session:
        async def count(model) -> int:
            result = await session.execute(
                select(func.count()).select_from(model).where(model.company_id == company_id)
            )
            return int(result.scalar_one())

        assert await count(CompanyBrainProfile) == 1
        assert await count(CompanyFact) == 1
        assert await count(CompanyBelief) == 1
        assert await count(CompanyConstraint) == 1
        assert await count(Objective) == 1
        assert await count(Decision) == 1
        assert await count(OnboardingDraft) == 1


@pytest.mark.asyncio
async def test_invalid_confirm_does_not_write_brain(async_session_factory) -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    patched = client.patch(
        _draft_url(company["id"]),
        json={"payload": {"company": {"name": "Forge"}}, "current_step": 2},
    )
    assert patched.status_code == 200
    failed = client.post(_confirm_url(company["id"]))
    assert failed.status_code == 400
    company_id = uuid.UUID(company["id"])

    async with async_session_factory() as session:
        profile = await session.execute(
            select(CompanyBrainProfile).where(CompanyBrainProfile.company_id == company_id)
        )
        assert profile.scalar_one_or_none() is None
        facts = await session.execute(
            select(func.count()).select_from(CompanyFact).where(CompanyFact.company_id == company_id)
        )
        assert facts.scalar_one() == 0
        draft = (
            await session.execute(
                select(OnboardingDraft).where(OnboardingDraft.company_id == company_id)
            )
        ).scalar_one()
        assert draft.status == "draft"
        assert draft.confirmed_at is None


@pytest.mark.asyncio
async def test_transaction_rollback_leaves_no_partial_brain(async_session_factory) -> None:
    client = _client()
    creds = _signup(client)
    company = _create_company(client)
    _save_complete_draft(client, company["id"])
    me = client.get("/api/v1/auth/me").json()
    company_id = uuid.UUID(company["id"])

    async with async_session_factory() as session:
        user_result = await session.execute(
            select(OnboardingDraft).where(OnboardingDraft.company_id == company_id)
        )
        draft = user_result.scalar_one()
        from app.models.user import User

        user = await session.get(User, draft.created_by_user_id)
        assert user is not None
        session.commit = AsyncMock(side_effect=RuntimeError("commit failed"))
        with pytest.raises(RuntimeError, match="commit failed"):
            await confirm_onboarding(session, company_id=company_id, user=user)

    async with async_session_factory() as session:
        profile = await session.execute(
            select(CompanyBrainProfile).where(CompanyBrainProfile.company_id == company_id)
        )
        assert profile.scalar_one_or_none() is None
        assert (
            await session.execute(
                select(func.count()).select_from(CompanyFact).where(
                    CompanyFact.company_id == company_id
                )
            )
        ).scalar_one() == 0
        assert (
            await session.execute(
                select(func.count()).select_from(CompanyBelief).where(
                    CompanyBelief.company_id == company_id
                )
            )
        ).scalar_one() == 0
        assert (
            await session.execute(
                select(func.count()).select_from(Objective).where(Objective.company_id == company_id)
            )
        ).scalar_one() == 0
        draft = (
            await session.execute(
                select(OnboardingDraft).where(OnboardingDraft.company_id == company_id)
            )
        ).scalar_one()
        assert draft.status == "draft"
        assert draft.confirmed_at is None

    resumed = _client()
    assert (
        resumed.post(
            "/api/v1/auth/login",
            json={"email": creds["email"], "password": creds["password"]},
        ).status_code
        == 200
    )
    retry = resumed.post(_confirm_url(company["id"]))
    assert retry.status_code == 200
    assert me["id"] == resumed.get("/api/v1/auth/me").json()["id"]


@pytest.mark.asyncio
async def test_tenant_isolation_on_confirm(async_session_factory) -> None:
    user_a = _client()
    user_b = _client()
    _signup(user_a)
    _signup(user_b)
    company_a = _create_company(user_a)
    company_b = _create_company(user_b)
    _save_complete_draft(user_a, company_a["id"])
    _save_complete_draft(user_b, company_b["id"])

    assert user_a.post(_confirm_url(company_b["id"])).status_code == 403
    assert user_b.post(_confirm_url(company_a["id"])).status_code == 403
    assert user_a.post(_confirm_url(company_a["id"])).status_code == 200

    async with async_session_factory() as session:
        b_profile = await session.execute(
            select(CompanyBrainProfile).where(
                CompanyBrainProfile.company_id == uuid.UUID(company_b["id"])
            )
        )
        assert b_profile.scalar_one_or_none() is None
        a_facts = (
            await session.execute(
                select(CompanyFact).where(CompanyFact.company_id == uuid.UUID(company_a["id"]))
            )
        ).scalars().all()
        b_facts = (
            await session.execute(
                select(CompanyFact).where(CompanyFact.company_id == uuid.UUID(company_b["id"]))
            )
        ).scalars().all()
        assert len(a_facts) == 1
        assert len(b_facts) == 0
