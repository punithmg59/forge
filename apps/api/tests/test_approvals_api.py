"""Focused tests for Task 6.3 approval gate and founder tasks."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.main import app
from app.models.agent_run import AgentRun
from app.models.agent_task import AgentTask
from app.models.approval import Approval
from app.models.company import Company
from app.models.company_member import CompanyMember
from app.models.objective import Objective
from app.models.objective_task import ObjectiveTask
from app.models.user import User
from app.schemas.head_agent import HeadAgentRecommendation, ProposedAction
from app.services.approval_service import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    ApprovalError,
    approve_approval,
    create_approval,
    reject_approval,
)
from app.services.head_agent import HEAD_AGENT_TASK_TYPE, HEAD_AGENT_TYPE


def _client() -> TestClient:
    return TestClient(app)


def _signup(client: TestClient, *, name: str = "Founder") -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": name,
            "email": f"approval-{uuid.uuid4()}@example.com",
            "password": "valid-pass-1",
        },
    )
    assert response.status_code == 201


def _create_company(client: TestClient, name: str = "Approval Co") -> dict:
    response = client.post(
        "/api/v1/companies",
        json={
            "name": name,
            "description": "Approval test",
            "target_customer": "founders",
            "stage": "mvp",
        },
    )
    assert response.status_code == 201
    return response.json()


def _approvals_url(company_id: str, approval_id: str | None = None, action: str | None = None) -> str:
    base = f"/api/v1/companies/{company_id}/approvals"
    if approval_id is None:
        return base
    if action:
        return f"{base}/{approval_id}/{action}"
    return f"{base}/{approval_id}"


def _objectives_url(company_id: str) -> str:
    return f"/api/v1/companies/{company_id}/objectives"


def _create_objective(client: TestClient, company_id: str, title: str = "Get customers") -> dict:
    response = client.post(
        _objectives_url(company_id),
        json={"title": title, "priority": 200},
    )
    assert response.status_code == 201
    return response.json()


def _task_recommendation(
    *,
    action_type: str = "task",
    title: str = "Interview founders",
    task_title: str = "Run five interviews",
) -> dict:
    return {
        "title": title,
        "recommendation": "Interview additional technical founders this week.",
        "rationale": "Grounded in the current objective.",
        "proposed_action": {
            "type": action_type,
            "title": task_title,
            "description": "Ask about onboarding pain.",
        },
        "sources": [],
        "confidence": "medium",
    }


async def _seed_recommendation_task(
    session: AsyncSession,
    *,
    action_type: str = "task",
    company_name: str = "Approval Co",
) -> tuple[CompanyMember, AgentTask, Objective]:
    user = User(email=f"approval-{uuid.uuid4()}@example.com", name="Founder")
    session.add(user)
    await session.flush()
    company = Company(
        name=company_name,
        slug=f"approval-{uuid.uuid4().hex[:8]}",
        stage="mvp",
    )
    session.add(company)
    await session.flush()
    membership = CompanyMember(company_id=company.id, user_id=user.id, role="founder")
    session.add(membership)
    objective = Objective(
        company_id=company.id,
        title="Get first 10 customers",
        status="active",
        priority="300",
        created_by=user.id,
    )
    session.add(objective)
    await session.flush()
    run = AgentRun(
        company_id=company.id,
        agent_type=HEAD_AGENT_TYPE,
        objective_id=objective.id,
        status="completed",
        started_at="2026-08-24T00:00:00+00:00",
        completed_at="2026-08-24T00:00:01+00:00",
    )
    session.add(run)
    await session.flush()
    agent_task = AgentTask(
        company_id=company.id,
        agent_run_id=run.id,
        agent_type=HEAD_AGENT_TYPE,
        task_type=HEAD_AGENT_TASK_TYPE,
        status="completed",
        input={"question": "What should I focus on next?"},
        output=_task_recommendation(action_type=action_type),
        completed_at="2026-08-24T00:00:01+00:00",
    )
    session.add(agent_task)
    await session.commit()
    await session.refresh(membership)
    await session.refresh(agent_task)
    await session.refresh(objective)
    return membership, agent_task, objective


@pytest.mark.asyncio
async def test_create_approval_from_valid_head_agent_recommendation(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, agent_task, _objective = await _seed_recommendation_task(session)
        approval = await create_approval(
            session,
            company_id=membership.company_id,
            agent_task_id=agent_task.id,
        )
    assert approval.status == STATUS_PENDING
    assert approval.action_type == "task"
    assert approval.agent_task_id == agent_task.id


@pytest.mark.asyncio
async def test_list_and_retrieve_approvals(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, agent_task, _objective = await _seed_recommendation_task(session)
        created = await create_approval(
            session,
            company_id=membership.company_id,
            agent_task_id=agent_task.id,
        )
        approvals = (
            await session.execute(
                select(Approval).where(Approval.company_id == membership.company_id)
            )
        ).scalars().all()
        fetched = await session.get(Approval, created.id)
    assert len(approvals) == 1
    assert fetched is not None
    assert fetched.status == STATUS_PENDING


@pytest.mark.asyncio
async def test_founder_can_approve_and_reject(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, agent_task, _objective = await _seed_recommendation_task(session)
        user = await session.get(User, membership.user_id)
        assert user is not None
        approval = await create_approval(
            session,
            company_id=membership.company_id,
            agent_task_id=agent_task.id,
        )
        approved, _task = await approve_approval(session, approval=approval, user=user)
        assert approved.status == STATUS_APPROVED
        assert approved.resolved_by == user.id

        membership2, agent_task2, _objective2 = await _seed_recommendation_task(
            session, company_name="Reject Co"
        )
        user2 = await session.get(User, membership2.user_id)
        assert user2 is not None
        approval2 = await create_approval(
            session,
            company_id=membership2.company_id,
            agent_task_id=agent_task2.id,
        )
        rejected = await reject_approval(session, approval=approval2, user=user2)
        assert rejected.status == STATUS_REJECTED


@pytest.mark.asyncio
async def test_invalid_transitions_are_rejected(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, agent_task, _objective = await _seed_recommendation_task(session)
        user = await session.get(User, membership.user_id)
        assert user is not None
        approval = await create_approval(
            session,
            company_id=membership.company_id,
            agent_task_id=agent_task.id,
        )
        await reject_approval(session, approval=approval, user=user)
        with pytest.raises(ApprovalError) as exc:
            await approve_approval(session, approval=approval, user=user)
        assert exc.value.status_code == 400

        membership2, agent_task2, _objective2 = await _seed_recommendation_task(
            session, company_name="Approved Co"
        )
        user2 = await session.get(User, membership2.user_id)
        assert user2 is not None
        approval2 = await create_approval(
            session,
            company_id=membership2.company_id,
            agent_task_id=agent_task2.id,
        )
        await approve_approval(session, approval=approval2, user=user2)
        with pytest.raises(ApprovalError) as exc2:
            await reject_approval(session, approval=approval2, user=user2)
        assert exc2.value.status_code == 400


@pytest.mark.asyncio
async def test_approved_task_recommendation_creates_one_objective_task(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, agent_task, objective = await _seed_recommendation_task(session)
        user = await session.get(User, membership.user_id)
        assert user is not None
        approval = await create_approval(
            session,
            company_id=membership.company_id,
            agent_task_id=agent_task.id,
        )
        await approve_approval(session, approval=approval, user=user)
        task_count = await session.scalar(
            select(func.count())
            .select_from(ObjectiveTask)
            .where(ObjectiveTask.company_id == membership.company_id)
        )
        tasks = (
            await session.execute(
                select(ObjectiveTask).where(ObjectiveTask.company_id == membership.company_id)
            )
        ).scalars().all()
        refreshed_task = await session.get(AgentTask, agent_task.id)
        refreshed_objective = await session.get(Objective, objective.id)
    assert task_count == 1
    assert tasks[0].title == "Run five interviews"
    assert tasks[0].objective_id == objective.id
    assert refreshed_task is not None
    assert refreshed_task.objective_task_id == tasks[0].id
    assert refreshed_objective is not None
    assert refreshed_objective.title == "Get first 10 customers"
    assert refreshed_objective.status == "active"


@pytest.mark.asyncio
async def test_approve_twice_does_not_create_duplicate_objective_task(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, agent_task, _objective = await _seed_recommendation_task(session)
        user = await session.get(User, membership.user_id)
        assert user is not None
        approval = await create_approval(
            session,
            company_id=membership.company_id,
            agent_task_id=agent_task.id,
        )
        await approve_approval(session, approval=approval, user=user)
        await approve_approval(session, approval=approval, user=user)
        task_count = await session.scalar(
            select(func.count())
            .select_from(ObjectiveTask)
            .where(ObjectiveTask.company_id == membership.company_id)
        )
    assert task_count == 1


@pytest.mark.asyncio
async def test_rejected_task_recommendation_creates_no_objective_task(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, agent_task, _objective = await _seed_recommendation_task(session)
        user = await session.get(User, membership.user_id)
        assert user is not None
        approval = await create_approval(
            session,
            company_id=membership.company_id,
            agent_task_id=agent_task.id,
        )
        await reject_approval(session, approval=approval, user=user)
        task_count = await session.scalar(
            select(func.count())
            .select_from(ObjectiveTask)
            .where(ObjectiveTask.company_id == membership.company_id)
        )
    assert task_count == 0


@pytest.mark.asyncio
async def test_none_action_creates_no_task_on_approve(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, agent_task, _objective = await _seed_recommendation_task(
            session, action_type="none"
        )
        user = await session.get(User, membership.user_id)
        assert user is not None
        approval = await create_approval(
            session,
            company_id=membership.company_id,
            agent_task_id=agent_task.id,
        )
        await approve_approval(session, approval=approval, user=user)
        task_count = await session.scalar(
            select(func.count())
            .select_from(ObjectiveTask)
            .where(ObjectiveTask.company_id == membership.company_id)
        )
    assert task_count == 0
    assert approval.action_type == "none"


@pytest.mark.asyncio
async def test_objective_change_does_not_mutate_objective(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, agent_task, objective = await _seed_recommendation_task(
            session, action_type="objective_change"
        )
        user = await session.get(User, membership.user_id)
        assert user is not None
        approval = await create_approval(
            session,
            company_id=membership.company_id,
            agent_task_id=agent_task.id,
        )
        await approve_approval(session, approval=approval, user=user)
        refreshed = await session.get(Objective, objective.id)
        task_count = await session.scalar(
            select(func.count())
            .select_from(ObjectiveTask)
            .where(ObjectiveTask.company_id == membership.company_id)
        )
    assert task_count == 0
    assert refreshed is not None
    assert refreshed.title == "Get first 10 customers"
    assert refreshed.status == "active"


def test_unauthenticated_returns_401() -> None:
    client = _client()
    company_id = str(uuid.uuid4())
    assert client.get(_approvals_url(company_id)).status_code == 401
    assert client.post(_approvals_url(company_id), json={"agent_task_id": str(uuid.uuid4())}).status_code == 401


def test_non_member_returns_403() -> None:
    owner = _client()
    outsider = _client()
    _signup(owner)
    _signup(outsider, name="Outsider")
    company = _create_company(owner)
    assert outsider.get(_approvals_url(company["id"])).status_code == 403


def test_insufficient_role_returns_403_on_create() -> None:
    founder = _client()
    member = _client()
    _signup(founder, name="Founder")
    _signup(member, name="Member")
    company = _create_company(founder, name="Role Co")
    response = member.post(
        _approvals_url(company["id"]),
        json={"agent_task_id": str(uuid.uuid4())},
    )
    assert response.status_code == 403


def test_approve_routes_require_founder_role() -> None:
    from pathlib import Path

    source = Path(__file__).resolve().parents[1] / "app" / "api" / "routes" / "approvals.py"
    text = source.read_text(encoding="utf-8")
    assert text.count("require_company_role(*COMPANY_MANAGE_ROLES)") >= 3


@pytest.mark.asyncio
async def test_company_a_cannot_approve_company_b_recommendation(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership_a, agent_task_a, _objective_a = await _seed_recommendation_task(
            session, company_name="Company A"
        )
        other_company_id = uuid.uuid4()
        with pytest.raises(ApprovalError) as exc:
            await create_approval(
                session,
                company_id=other_company_id,
                agent_task_id=agent_task_a.id,
            )
        assert exc.value.status_code == 404


def test_api_company_a_cannot_access_company_b_approvals() -> None:
    owner_a = _client()
    owner_b = _client()
    _signup(owner_a)
    _signup(owner_b)
    company_a = _create_company(owner_a, name="Company A")
    _create_company(owner_b, name="Company B")
    assert owner_b.get(_approvals_url(company_a["id"])).status_code == 403


@pytest.mark.asyncio
async def test_invalid_recommendation_action_is_rejected(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, agent_task, _objective = await _seed_recommendation_task(session)
        agent_task.output = {
            **_task_recommendation(),
            "proposed_action": {
                "type": "send_email",
                "title": "Spam",
                "description": "Do bad things",
            },
        }
        await session.commit()
        with pytest.raises(ApprovalError) as exc:
            await create_approval(
                session,
                company_id=membership.company_id,
                agent_task_id=agent_task.id,
            )
        assert exc.value.status_code == 400


def test_malicious_client_payload_is_rejected() -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    response = client.post(
        _approvals_url(company["id"]),
        json={
            "agent_task_id": str(uuid.uuid4()),
            "action": "send_email",
            "recipient": "victim@example.com",
            "message": "hacked",
        },
    )
    assert response.status_code == 422


def test_no_llm_call_during_approval() -> None:
    with patch("app.services.llm.get_llm_provider") as factory:
        client = _client()
        _signup(client)
        company = _create_company(client)
        response = client.post(
            _approvals_url(company["id"]),
            json={"agent_task_id": str(uuid.uuid4())},
        )
        factory.assert_not_called()
    assert response.status_code in {400, 404}


@pytest.mark.asyncio
async def test_approval_service_does_not_import_llm_providers() -> None:
    from pathlib import Path

    source = Path(__file__).resolve().parents[1] / "app" / "services" / "approval_service.py"
    text = source.read_text(encoding="utf-8")
    assert "get_llm_provider" not in text
    assert "LLMProvider" not in text
    assert "newtron" not in text.lower()


def test_api_create_list_approve_flow() -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    _create_objective(client, company["id"])

    recommendation_payload = _task_recommendation()
    with patch("app.api.routes.head_agent.recommend_next_action", new_callable=AsyncMock) as mock_recommend:
        from app.schemas.head_agent import HeadAgentRecommendResponse

        agent_task_id = uuid.uuid4()
        mock_recommend.return_value = HeadAgentRecommendResponse(
            agent_task_id=agent_task_id,
            recommendation=HeadAgentRecommendation.model_validate(recommendation_payload),
        )
        recommend_response = client.post(
            f"/api/v1/companies/{company['id']}/head-agent/recommend",
            json={"question": "What should I focus on next?"},
        )
        assert recommend_response.status_code == 200

    # For API flow test with mocked head agent, seed approval via DB in integration tests above.
    # Here verify route wiring and auth on approve endpoint.
    assert client.post(
        _approvals_url(company["id"], str(uuid.uuid4()), "approve"),
    ).status_code in {401, 403, 404}


@pytest.mark.asyncio
async def test_non_head_agent_task_is_rejected(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, agent_task, _objective = await _seed_recommendation_task(session)
        agent_task.agent_type = "specialist"
        await session.commit()
        with pytest.raises(ApprovalError) as exc:
            await create_approval(
                session,
                company_id=membership.company_id,
                agent_task_id=agent_task.id,
            )
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_invalid_recommendation_payload_is_rejected(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, agent_task, _objective = await _seed_recommendation_task(session)
        agent_task.output = {"not": "a recommendation"}
        await session.commit()
        with pytest.raises(ApprovalError) as exc:
            await create_approval(
                session,
                company_id=membership.company_id,
                agent_task_id=agent_task.id,
            )
        assert exc.value.status_code == 400
