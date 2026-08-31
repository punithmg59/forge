"""Task 7.4 tests for Learning approval integration."""

from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.main import app
from app.models.approval import Approval
from app.models.company import Company
from app.models.company_belief import CompanyBelief
from app.models.company_fact import CompanyFact
from app.models.company_member import CompanyMember
from app.models.decision import Decision
from app.models.evidence import Evidence
from app.models.learning import Learning
from app.models.objective import Objective
from app.models.objective_task import ObjectiveTask
from app.models.user import User
from app.services.approval_service import (
    ACTION_TYPE_LEARNING,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    ApprovalError,
    approve_approval,
    create_learning_approval,
    reject_approval,
)
from app.services.evidence_service import (
    SOURCE_TYPE_OBJECTIVE_TASK_RESULT,
    build_objective_task_evidence_content,
)
from app.services.learning_proposal_service import (
    STATUS_ACTIVE,
    STATUS_PROPOSED,
    propose_learning_from_evidence,
)
from app.services.llm import CompletionRequest, CompletionResult, LLMProvider
from app.services.objective_task_service import STATUS_COMPLETED
from app.services.retrieval.scope import RetrievalScope
from app.services.retrieval.sql import SqlStructuredRetriever


def _client() -> TestClient:
    return TestClient(app)


def _approvals_url(
    company_id: str,
    approval_id: str | None = None,
    action: str | None = None,
) -> str:
    base = f"/api/v1/companies/{company_id}/approvals"
    if approval_id is None:
        return base
    if action:
        return f"{base}/{approval_id}/{action}"
    return f"{base}/{approval_id}"


class _StubProvider(LLMProvider):
    name = "stub"

    def __init__(self, answer: str) -> None:
        self.answer = answer

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        return CompletionResult(text=self.answer, model="stub-model", finish_reason="stop")

    async def embed(self, request: object) -> object:
        raise AssertionError("stub must not embed")


def _learning_json(source_id: str) -> str:
    return json.dumps(
        {
            "decision": "learning",
            "learning": {
                "content": (
                    "Difficulty with financial operations appears to be a recurring problem "
                    "among the interviewed target customers."
                ),
                "confidence": "medium",
                "reason": "9 of 12 interviewed customers reported the problem.",
            },
            "source_evidence_ids": [source_id],
        }
    )


async def _seed_proposed_learning(
    session: AsyncSession,
    *,
    company_name: str = "Learning Approval Co",
) -> tuple[CompanyMember, Learning, Evidence, ObjectiveTask, Objective, User]:
    user = User(email=f"learning-approval-{uuid.uuid4()}@example.com", name="Founder")
    session.add(user)
    await session.flush()
    company = Company(
        name=company_name,
        slug=f"learning-approval-{uuid.uuid4().hex[:8]}",
        stage="mvp",
    )
    session.add(company)
    await session.flush()
    membership = CompanyMember(company_id=company.id, user_id=user.id, role="founder")
    session.add(membership)
    objective = Objective(
        company_id=company.id,
        title="Get our first 100 customers",
        status="active",
        priority="300",
        created_by=user.id,
    )
    session.add(objective)
    await session.flush()
    task = ObjectiveTask(
        company_id=company.id,
        objective_id=objective.id,
        title="Run five interviews",
        description="Interview founders",
        capability="founder",
        status=STATUS_COMPLETED,
        priority="medium",
        requires_approval=False,
        result_summary="12 customers interviewed.",
        result_metrics={"interviewed": 12, "reported_problem": 9, "willing_to_pay": 7},
    )
    session.add(task)
    await session.flush()
    summary = build_objective_task_evidence_content(
        result_summary=(
            "12 customers interviewed. "
            "9 reported difficulty with financial operations. "
            "7 said they would pay."
        ),
        result_metrics={"interviewed": 12, "reported_problem": 9, "willing_to_pay": 7},
    )
    evidence = Evidence(
        company_id=company.id,
        type="founder_task_result",
        title="Run five interviews",
        content=summary,
        source_type=SOURCE_TYPE_OBJECTIVE_TASK_RESULT,
        source_reference=str(task.id),
    )
    session.add(evidence)
    await session.commit()
    await session.refresh(evidence)

    proposal = await propose_learning_from_evidence(
        session,
        evidence=evidence,
        provider_factory=lambda: _StubProvider(_learning_json(str(evidence.id))),
    )
    assert proposal.proposal is not None
    learning = await session.get(Learning, proposal.proposal.id)
    assert learning is not None

    await session.refresh(membership)
    await session.refresh(evidence)
    await session.refresh(task)
    await session.refresh(objective)
    await session.refresh(user)
    return membership, learning, evidence, task, objective, user


@pytest.mark.asyncio
async def test_proposed_learning_can_create_pending_approval(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, learning, _evidence, _task, _objective, _user = await _seed_proposed_learning(
            session
        )
        approval = await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=learning.id,
        )
    assert approval.status == STATUS_PENDING
    assert approval.action_type == ACTION_TYPE_LEARNING
    assert approval.learning_id == learning.id
    assert learning.status == STATUS_PROPOSED


@pytest.mark.asyncio
async def test_founder_approve_activates_learning(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, learning, evidence, task, objective, user = await _seed_proposed_learning(
            session
        )
        approval = await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=learning.id,
        )
        updated, objective_task = await approve_approval(session, approval=approval, user=user)
        refreshed_learning = await session.get(Learning, learning.id)
        refreshed_evidence = await session.get(Evidence, evidence.id)
        refreshed_task = await session.get(ObjectiveTask, task.id)
        refreshed_objective = await session.get(Objective, objective.id)
    assert objective_task is None
    assert updated.status == STATUS_APPROVED
    assert refreshed_learning is not None
    assert refreshed_learning.status == STATUS_ACTIVE
    assert refreshed_evidence is not None
    assert refreshed_evidence.content == evidence.content
    assert refreshed_task is not None
    assert refreshed_task.status == STATUS_COMPLETED
    assert refreshed_objective is not None
    assert refreshed_objective.title == "Get our first 100 customers"


@pytest.mark.asyncio
async def test_approved_learning_appears_in_brain_retrieval(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, learning, _evidence, _task, _objective, user = await _seed_proposed_learning(
            session
        )
        approval = await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=learning.id,
        )
        await approve_approval(session, approval=approval, user=user)
        context = await SqlStructuredRetriever(session).retrieve(
            RetrievalScope.from_membership(membership),
            query="What have we learned?",
        )
    assert any(item.statement == learning.statement for item in context.learnings)


@pytest.mark.asyncio
async def test_founder_reject_keeps_learning_non_active(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, learning, _evidence, _task, _objective, user = await _seed_proposed_learning(
            session
        )
        approval = await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=learning.id,
        )
        updated = await reject_approval(session, approval=approval, user=user)
        refreshed_learning = await session.get(Learning, learning.id)
        context = await SqlStructuredRetriever(session).retrieve(
            RetrievalScope.from_membership(membership),
            query="What have we learned?",
        )
    assert updated.status == STATUS_REJECTED
    assert refreshed_learning is not None
    assert refreshed_learning.status == "rejected"
    assert refreshed_learning.status != STATUS_ACTIVE
    assert not any(item.statement == learning.statement for item in context.learnings)


@pytest.mark.asyncio
async def test_proposed_learning_stays_non_active_before_approval(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, learning, _evidence, _task, _objective, _user = await _seed_proposed_learning(
            session
        )
        await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=learning.id,
        )
        context = await SqlStructuredRetriever(session).retrieve(
            RetrievalScope.from_membership(membership),
            query="What have we learned?",
        )
        refreshed_learning = await session.get(Learning, learning.id)
    assert refreshed_learning is not None
    assert refreshed_learning.status == STATUS_PROPOSED
    assert not any(item.statement == learning.statement for item in context.learnings)


@pytest.mark.asyncio
async def test_terminal_approval_transitions_are_blocked(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, learning, _evidence, _task, _objective, user = await _seed_proposed_learning(
            session
        )
        approval = await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=learning.id,
        )
        await approve_approval(session, approval=approval, user=user)
        with pytest.raises(ApprovalError):
            await reject_approval(session, approval=approval, user=user)

        membership2, learning2, _evidence2, _task2, _objective2, user2 = (
            await _seed_proposed_learning(
                session,
                company_name="Reject Terminal Co",
            )
        )
        approval2 = await create_learning_approval(
            session,
            company_id=membership2.company_id,
            learning_id=learning2.id,
        )
        await reject_approval(session, approval=approval2, user=user2)
        with pytest.raises(ApprovalError):
            await approve_approval(session, approval=approval2, user=user2)


@pytest.mark.asyncio
async def test_double_approval_is_idempotent(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, learning, _evidence, _task, _objective, user = await _seed_proposed_learning(
            session
        )
        approval = await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=learning.id,
        )
        await approve_approval(session, approval=approval, user=user)
        await approve_approval(session, approval=approval, user=user)
        count = await session.scalar(
            select(func.count())
            .select_from(Learning)
            .where(
                Learning.company_id == membership.company_id,
                Learning.status == STATUS_ACTIVE,
            )
        )
    assert count == 1


@pytest.mark.asyncio
async def test_duplicate_pending_approval_is_reused(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, learning, _evidence, _task, _objective, _user = await _seed_proposed_learning(
            session
        )
        first = await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=learning.id,
        )
        second = await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=learning.id,
        )
        pending_count = await session.scalar(
            select(func.count())
            .select_from(Approval)
            .where(
                Approval.company_id == membership.company_id,
                Approval.learning_id == learning.id,
            )
        )
    assert first.id == second.id
    assert pending_count == 1


@pytest.mark.asyncio
async def test_no_fact_belief_or_decision_created_on_approve(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, learning, _evidence, _task, _objective, user = await _seed_proposed_learning(
            session
        )
        facts_before = await session.scalar(select(func.count()).select_from(CompanyFact))
        beliefs_before = await session.scalar(select(func.count()).select_from(CompanyBelief))
        decisions_before = await session.scalar(select(func.count()).select_from(Decision))
        approval = await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=learning.id,
        )
        await approve_approval(session, approval=approval, user=user)
        facts_after = await session.scalar(select(func.count()).select_from(CompanyFact))
        beliefs_after = await session.scalar(select(func.count()).select_from(CompanyBelief))
        decisions_after = await session.scalar(select(func.count()).select_from(Decision))
    assert facts_before == facts_after
    assert beliefs_before == beliefs_after
    assert decisions_before == decisions_after


@patch("app.services.learning_proposal_service.get_llm_provider")
@pytest.mark.asyncio
async def test_no_llm_call_during_learning_approval(
    mock_provider: object,
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, learning, _evidence, _task, _objective, user = await _seed_proposed_learning(
            session
        )
        approval = await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=learning.id,
        )
        await approve_approval(session, approval=approval, user=user)
    mock_provider.assert_not_called()


def test_company_a_cannot_approve_company_b_learning(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    import asyncio

    async def seed() -> tuple[str, str]:
        async with async_session_factory() as session:
            membership, learning, _evidence, _task, _objective, _user = (
                await _seed_proposed_learning(session)
            )
            approval = await create_learning_approval(
                session,
                company_id=membership.company_id,
                learning_id=learning.id,
            )
            return str(membership.company_id), str(approval.id)

    company_id, approval_id = asyncio.run(seed())

    outsider = _client()
    outsider.post(
        "/api/v1/auth/register",
        json={
            "name": "Outsider",
            "email": f"out-{uuid.uuid4()}@example.com",
            "password": "valid-pass-1",
        },
    )
    outsider.post(
        "/api/v1/companies",
        json={
            "name": "Other Co",
            "description": "desc",
            "target_customer": "founders",
            "stage": "mvp",
        },
    )
    blocked = outsider.post(_approvals_url(company_id, approval_id, "approve"))
    assert blocked.status_code == 403


def test_create_learning_approval_via_api(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    import asyncio

    async def seed() -> tuple[str, str]:
        async with async_session_factory() as session:
            membership, learning, _evidence, _task, _objective, _user = (
                await _seed_proposed_learning(session)
            )
            return str(membership.company_id), str(learning.id)

    company_id, learning_id = asyncio.run(seed())

    client = _client()
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Founder",
            "email": f"api-learning-approval-{uuid.uuid4()}@example.com",
            "password": "valid-pass-1",
        },
    )
    client.post(
        "/api/v1/companies",
        json={
            "name": "API Learning Approval Co",
            "description": "desc",
            "target_customer": "founders",
            "stage": "mvp",
        },
    )

    outsider = _client()
    outsider.post(
        "/api/v1/auth/register",
        json={
            "name": "Outsider",
            "email": f"out-api-{uuid.uuid4()}@example.com",
            "password": "valid-pass-1",
        },
    )
    blocked = outsider.post(
        _approvals_url(company_id),
        json={"learning_id": learning_id},
    )
    assert blocked.status_code == 403


def test_approval_create_request_rejects_both_references() -> None:
    client = _client()
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Founder",
            "email": f"both-refs-{uuid.uuid4()}@example.com",
            "password": "valid-pass-1",
        },
    )
    company = client.post(
        "/api/v1/companies",
        json={
            "name": "Both Refs Co",
            "description": "desc",
            "target_customer": "founders",
            "stage": "mvp",
        },
    ).json()
    response = client.post(
        _approvals_url(company["id"]),
        json={
            "agent_task_id": str(uuid.uuid4()),
            "learning_id": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_non_proposed_learning_cannot_create_approval(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, learning, _evidence, _task, _objective, user = await _seed_proposed_learning(
            session
        )
        approval = await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=learning.id,
        )
        await approve_approval(session, approval=approval, user=user)
        with pytest.raises(ApprovalError) as exc:
            await create_learning_approval(
                session,
                company_id=membership.company_id,
                learning_id=learning.id,
            )
    assert exc.value.status_code == 400
