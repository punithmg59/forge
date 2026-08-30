"""Task 7.2 tests for deterministic Evidence capture from completed ObjectiveTasks."""

from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.company import Company
from app.models.company_member import CompanyMember
from app.models.evidence import Evidence
from app.models.learning import Learning
from app.models.objective import Objective
from app.models.objective_task import ObjectiveTask
from app.models.user import User
from app.services.brain_context import build_company_brain_context
from app.services.evidence_service import (
    EVIDENCE_TYPE_FOUNDER_TASK_RESULT,
    SOURCE_TYPE_OBJECTIVE_TASK_RESULT,
    create_evidence_from_objective_task,
    get_evidence_for_objective_task,
    parse_objective_task_evidence_content,
)
from app.services.objective_task_service import (
    STATUS_COMPLETED,
    STATUS_PENDING,
    complete_objective_task,
)
from app.services.retrieval.scope import RetrievalScope
from app.services.retrieval.sql import SqlStructuredRetriever


async def _seed_pending_task(
    session: AsyncSession,
    *,
    company_name: str = "Evidence Seed Co",
) -> tuple[CompanyMember, ObjectiveTask, User]:
    user = User(email=f"evidence-{uuid.uuid4()}@example.com", name="Founder")
    session.add(user)
    await session.flush()
    company = Company(
        name=company_name,
        slug=f"evidence-{uuid.uuid4().hex[:8]}",
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
        description="Ask about onboarding pain.",
        capability="founder",
        status=STATUS_PENDING,
        priority="medium",
        requires_approval=False,
    )
    session.add(task)
    await session.commit()
    await session.refresh(membership)
    await session.refresh(task)
    await session.refresh(user)
    return membership, task, user


@pytest.mark.asyncio
async def test_completing_task_creates_evidence(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary="12 customers interviewed.",
            result_metrics={"interviewed": 12, "reported_problem": 9},
            result_notes="Most were technical founders.",
        )
        evidence = await get_evidence_for_objective_task(
            session,
            company_id=membership.company_id,
            task_id=task.id,
        )
    assert evidence is not None
    assert evidence.company_id == membership.company_id
    assert evidence.source_type == SOURCE_TYPE_OBJECTIVE_TASK_RESULT
    assert evidence.source_reference == str(task.id)
    assert evidence.type == EVIDENCE_TYPE_FOUNDER_TASK_RESULT
    assert evidence.title == "Run five interviews"


@pytest.mark.asyncio
async def test_evidence_preserves_original_result_fields(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    summary = (
        "12 customers interviewed. 9 reported difficulty with financial operations. "
        "7 said they would pay."
    )
    metrics = {"interviewed": 12, "reported_problem": 9, "willing_to_pay": 7}
    notes = "Most interviews were with technical founders."

    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary=summary,
            result_metrics=metrics,
            result_notes=notes,
        )
        evidence = await get_evidence_for_objective_task(
            session,
            company_id=membership.company_id,
            task_id=task.id,
        )
    assert evidence is not None
    payload = parse_objective_task_evidence_content(evidence.content)
    assert payload["result_summary"] == summary
    assert payload["result_metrics"] == metrics
    assert payload["result_notes"] == notes


@pytest.mark.asyncio
async def test_repeated_completion_does_not_create_duplicate_evidence(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary="First completion.",
        )
        await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary="Should not duplicate evidence.",
        )
        count = await session.scalar(
            select(func.count())
            .select_from(Evidence)
            .where(
                Evidence.company_id == membership.company_id,
                Evidence.source_type == SOURCE_TYPE_OBJECTIVE_TASK_RESULT,
                Evidence.source_reference == str(task.id),
            )
        )
    assert count == 1


@pytest.mark.asyncio
async def test_evidence_belongs_to_task_company_not_other_company(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership_a, task_a, user_a = await _seed_pending_task(session, company_name="Company A")
        membership_b, _task_b, _user_b = await _seed_pending_task(session, company_name="Company B")
        await complete_objective_task(
            session,
            task=task_a,
            user=user_a,
            result_summary="Company A result.",
        )
        cross_lookup = await get_evidence_for_objective_task(
            session,
            company_id=membership_b.company_id,
            task_id=task_a.id,
        )
        evidence_a = await get_evidence_for_objective_task(
            session,
            company_id=membership_a.company_id,
            task_id=task_a.id,
        )
    assert cross_lookup is None
    assert evidence_a is not None
    assert evidence_a.company_id == membership_a.company_id


@pytest.mark.asyncio
async def test_brain_retrieval_returns_new_evidence(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    summary = "12 customers interviewed. 9 reported difficulty with financial operations."
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary=summary,
            result_metrics={"interviewed": 12, "reported_problem": 9},
        )
        context = await build_company_brain_context(
            session,
            membership=membership,
            query="What evidence do we have about our customers?",
        )
    assert len(context.evidence) >= 1
    matched = next(
        (row for row in context.evidence if row.title == "Run five interviews"),
        None,
    )
    assert matched is not None
    payload = json.loads(matched.content or "{}")
    assert payload["result_summary"] == summary
    assert payload["result_metrics"] == {"interviewed": 12, "reported_problem": 9}
    evidence_sources = [s for s in context.sources if s.entity_type == "evidence"]
    assert any(s.source_type == SOURCE_TYPE_OBJECTIVE_TASK_RESULT for s in evidence_sources)


@pytest.mark.asyncio
async def test_structured_retriever_returns_objective_task_evidence(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        task.result_summary = "Founder result for retrieval."
        task.result_metrics = {"interviewed": 5}
        task.result_notes = "Notes for retrieval."
        task.status = STATUS_COMPLETED
        task.completed_at = "2026-08-24T12:00:00+00:00"
        await create_evidence_from_objective_task(session, task=task)
        await session.commit()
        retrieved = await SqlStructuredRetriever(session).retrieve(
            RetrievalScope.from_membership(membership),
            query="What evidence do we have?",
        )
    assert any(row.title == "Run five interviews" for row in retrieved.evidence)


@pytest.mark.asyncio
async def test_completion_does_not_create_learning(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        learning_before = await session.scalar(select(func.count()).select_from(Learning))
        await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary="No learning yet.",
        )
        learning_after = await session.scalar(select(func.count()).select_from(Learning))
    assert learning_before == learning_after


@pytest.mark.asyncio
async def test_failed_evidence_creation_leaves_task_pending(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        task_id = task.id
        company_id = membership.company_id
        with patch(
            "app.services.objective_task_service.create_evidence_from_objective_task",
            side_effect=RuntimeError("evidence failed"),
        ):
            try:
                await complete_objective_task(
                    session,
                    task=task,
                    user=user,
                    result_summary="Should not persist.",
                )
            except RuntimeError:
                await session.rollback()

        refreshed = await session.get(ObjectiveTask, task_id)
        evidence_count = await session.scalar(
            select(func.count())
            .select_from(Evidence)
            .where(Evidence.company_id == company_id)
        )
    assert refreshed is not None
    assert refreshed.status == STATUS_PENDING
    assert evidence_count == 0
