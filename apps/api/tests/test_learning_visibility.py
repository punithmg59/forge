"""Task 7.5 tests for Brain visibility and Learning correction."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from test_learning_approval import _seed_proposed_learning

from app.main import app
from app.models.company_belief import CompanyBelief
from app.models.company_fact import CompanyFact
from app.models.decision import Decision
from app.models.evidence import Evidence
from app.models.learning import Learning
from app.models.objective import Objective
from app.models.objective_task import ObjectiveTask
from app.models.user import User
from app.services.approval_service import approve_approval, create_learning_approval
from app.services.learning_proposal_service import (
    STATUS_ACTIVE,
    STATUS_PROPOSED,
    STATUS_REJECTED,
    STATUS_SUPERSEDED,
)
from app.services.learning_service import (
    LearningError,
    correct_learning,
    learning_to_public,
    list_learnings,
)
from app.services.llm import CompletionRequest, CompletionResult, LLMProvider
from app.services.objective_task_service import STATUS_COMPLETED
from app.services.retrieval.scope import RetrievalScope
from app.services.retrieval.sql import SqlStructuredRetriever


def _client() -> TestClient:
    return TestClient(app)


def _learnings_url(
    company_id: str,
    learning_id: str | None = None,
    action: str | None = None,
) -> str:
    base = f"/api/v1/companies/{company_id}/learnings"
    if learning_id is None:
        return base
    if action:
        return f"{base}/{learning_id}/{action}"
    return f"{base}/{learning_id}"


class _StubProvider(LLMProvider):
    name = "stub"

    def __init__(self, answer: str) -> None:
        self.answer = answer

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        return CompletionResult(text=self.answer, model="stub-model", finish_reason="stop")

    async def embed(self, request: object) -> object:
        raise AssertionError("stub must not embed")


async def _seed_active_learning(
    session: AsyncSession,
    *,
    company_name: str = "Visibility Co",
) -> tuple[Learning, Evidence, ObjectiveTask, Objective, User]:
    membership, learning, evidence, task, objective, user = await _seed_proposed_learning(
        session,
        company_name=company_name,
    )
    approval = await create_learning_approval(
        session,
        company_id=membership.company_id,
        learning_id=learning.id,
    )
    await approve_approval(session, approval=approval, user=user)
    refreshed = await session.get(Learning, learning.id)
    assert refreshed is not None
    await session.refresh(refreshed)
    return refreshed, evidence, task, objective, user


@pytest.mark.asyncio
async def test_list_learnings_returns_company_scoped_records(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, proposed, _evidence, _task, _objective, user = await _seed_proposed_learning(
            session
        )
        approval = await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=proposed.id,
        )
        await approve_approval(session, approval=approval, user=user)
        learnings = await list_learnings(session, company_id=membership.company_id)
    statuses = {item.status for item in learnings}
    assert STATUS_ACTIVE in statuses
    assert STATUS_PROPOSED in statuses or len(learnings) >= 1


@pytest.mark.asyncio
async def test_learning_public_distinguishes_lifecycle_statuses(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, proposed, _evidence, _task, _objective, user = await _seed_proposed_learning(
            session,
            company_name="Lifecycle Co",
        )
        proposed_public = await learning_to_public(session, proposed)
        approval = await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=proposed.id,
        )
        await approve_approval(session, approval=approval, user=user)
        active = await session.get(Learning, proposed.id)
        assert active is not None
        await session.refresh(active)
        active_public = await learning_to_public(session, active)

        membership2, proposed2, _evidence2, _task2, _objective2, user2 = (
            await _seed_proposed_learning(session, company_name="Reject Co")
        )
        approval2 = await create_learning_approval(
            session,
            company_id=membership2.company_id,
            learning_id=proposed2.id,
        )
        from app.services.approval_service import reject_approval

        await reject_approval(session, approval=approval2, user=user2)
        rejected = await session.get(Learning, proposed2.id)
        assert rejected is not None
        await session.refresh(rejected)
        rejected_public = await learning_to_public(session, rejected)
    assert proposed_public.status == STATUS_PROPOSED
    assert active_public.status == STATUS_ACTIVE
    assert rejected_public.status == STATUS_REJECTED


@pytest.mark.asyncio
async def test_active_learning_in_brain_retrieval(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, proposed, _evidence, _task, _objective, user = await _seed_proposed_learning(
            session
        )
        approval = await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=proposed.id,
        )
        await approve_approval(session, approval=approval, user=user)
        context = await SqlStructuredRetriever(session).retrieve(
            RetrievalScope.from_membership(membership),
            query="What have we learned?",
        )
    assert any("financial operations" in item.statement.lower() for item in context.learnings)


@pytest.mark.asyncio
async def test_proposed_learning_not_in_active_brain_retrieval(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, proposed, _evidence, _task, _objective, _user = await _seed_proposed_learning(
            session
        )
        context = await SqlStructuredRetriever(session).retrieve(
            RetrievalScope.from_membership(membership),
            query="What have we learned?",
        )
    assert not any(item.statement == proposed.statement for item in context.learnings)


@pytest.mark.asyncio
async def test_founder_can_correct_active_learning(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        learning, evidence, task, objective, user = await _seed_active_learning(session)
        corrected = await correct_learning(
            session,
            learning=learning,
            user=user,
            reason="Customer interviews were from an outdated market segment.",
        )
        refreshed_evidence = await session.get(Evidence, evidence.id)
        refreshed_task = await session.get(ObjectiveTask, task.id)
        refreshed_objective = await session.get(Objective, objective.id)
    assert corrected.status == STATUS_SUPERSEDED
    assert (
        corrected.correction_reason
        == "Customer interviews were from an outdated market segment."
    )
    assert corrected.corrected_by == user.id
    assert corrected.corrected_at is not None
    assert refreshed_evidence is not None
    assert refreshed_evidence.content == evidence.content
    assert refreshed_task is not None
    assert refreshed_task.status == STATUS_COMPLETED
    assert refreshed_objective is not None
    assert refreshed_objective.title == objective.title


@pytest.mark.asyncio
async def test_corrected_learning_removed_from_brain_retrieval(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, proposed, _evidence, _task, _objective, user = await _seed_proposed_learning(
            session
        )
        approval = await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=proposed.id,
        )
        await approve_approval(session, approval=approval, user=user)
        learning = await session.get(Learning, proposed.id)
        assert learning is not None
        await correct_learning(
            session,
            learning=learning,
            user=user,
            reason="Outdated segment.",
        )
        context = await SqlStructuredRetriever(session).retrieve(
            RetrievalScope.from_membership(membership),
            query="What have we learned?",
        )
    assert not any(item.statement == learning.statement for item in context.learnings)


@pytest.mark.asyncio
async def test_correction_does_not_create_fact_belief_or_decision(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        learning, _evidence, _task, _objective, user = await _seed_active_learning(session)
        facts_before = await session.scalar(select(func.count()).select_from(CompanyFact))
        beliefs_before = await session.scalar(select(func.count()).select_from(CompanyBelief))
        decisions_before = await session.scalar(select(func.count()).select_from(Decision))
        await correct_learning(
            session,
            learning=learning,
            user=user,
            reason="No longer accurate.",
        )
        facts_after = await session.scalar(select(func.count()).select_from(CompanyFact))
        beliefs_after = await session.scalar(select(func.count()).select_from(CompanyBelief))
        decisions_after = await session.scalar(select(func.count()).select_from(Decision))
    assert facts_before == facts_after
    assert beliefs_before == beliefs_after
    assert decisions_before == decisions_after


@patch("app.services.learning_proposal_service.get_llm_provider")
@pytest.mark.asyncio
async def test_no_llm_during_visibility_or_correction(
    mock_provider: object,
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        learning, _evidence, _task, _objective, user = await _seed_active_learning(session)
        await list_learnings(session, company_id=learning.company_id)
        await learning_to_public(session, learning)
        await correct_learning(
            session,
            learning=learning,
            user=user,
            reason="Outdated.",
        )
    mock_provider.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_correction_transition_rejected(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, proposed, _evidence, _task, _objective, user = await _seed_proposed_learning(
            session
        )
        with pytest.raises(LearningError) as exc:
            await correct_learning(
                session,
                learning=proposed,
                user=user,
                reason="Should fail.",
            )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_repeated_correction_is_idempotent(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        learning, _evidence, _task, _objective, user = await _seed_active_learning(session)
        first = await correct_learning(
            session,
            learning=learning,
            user=user,
            reason="Outdated segment.",
        )
        second = await correct_learning(
            session,
            learning=first,
            user=user,
            reason="Outdated segment.",
        )
    assert first.id == second.id
    assert second.status == STATUS_SUPERSEDED


@pytest.mark.asyncio
async def test_learning_provenance_points_to_evidence_chain(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        learning, evidence, task, objective, _user = await _seed_active_learning(session)
        public = await learning_to_public(session, learning)
    assert public.provenance is not None
    assert public.provenance.evidence_id == evidence.id
    assert public.provenance.objective_task_id == task.id
    assert public.provenance.objective_id == objective.id
    assert public.provenance.objective_task_title == "Run five interviews"
    assert public.provenance.objective_title == "Get our first 100 customers"


def test_cross_company_learning_access_blocked(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    import asyncio

    async def seed() -> tuple[str, str]:
        async with async_session_factory() as session:
            learning, _evidence, _task, _objective, _user = await _seed_active_learning(session)
            return str(learning.company_id), str(learning.id)

    company_id, learning_id = asyncio.run(seed())

    outsider = _client()
    outsider.post(
        "/api/v1/auth/register",
        json={
            "name": "Outsider",
            "email": f"out-vis-{uuid.uuid4()}@example.com",
            "password": "valid-pass-1",
        },
    )
    blocked = outsider.get(_learnings_url(company_id, learning_id))
    assert blocked.status_code == 403


def test_cross_company_learning_list_blocked(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    import asyncio

    async def seed() -> str:
        async with async_session_factory() as session:
            learning, _evidence, _task, _objective, _user = await _seed_active_learning(session)
            return str(learning.company_id)

    company_id = asyncio.run(seed())

    outsider = _client()
    outsider.post(
        "/api/v1/auth/register",
        json={
            "name": "Outsider List",
            "email": f"out-list-{uuid.uuid4()}@example.com",
            "password": "valid-pass-1",
        },
    )
    blocked = outsider.get(_learnings_url(company_id))
    assert blocked.status_code == 403


def test_unauthenticated_list_returns_401() -> None:
    client = _client()
    response = client.get(_learnings_url(str(uuid.uuid4())))
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_proposed_learning_shows_approval_status(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, proposed, _evidence, _task, _objective, _user = await _seed_proposed_learning(
            session
        )
        await create_learning_approval(
            session,
            company_id=membership.company_id,
            learning_id=proposed.id,
        )
        public = await learning_to_public(session, proposed)
    assert public.status == STATUS_PROPOSED
    assert public.approval_status == "pending"
