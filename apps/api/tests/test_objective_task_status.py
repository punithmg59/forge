"""Task 8.1 tests for ObjectiveTask execution state machine."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.main import app
from app.models.company import Company
from app.models.company_member import CompanyMember
from app.models.evidence import Evidence
from app.models.objective import Objective
from app.models.objective_task import ObjectiveTask
from app.models.user import User
from app.services.evidence_service import get_evidence_for_objective_task
from app.services.objective_task_service import (
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
    ObjectiveTaskError,
    transition_objective_task_status,
)

COMPLETION_SUMMARY = (
    "12 customers interviewed. 9 reported difficulty with financial operations. "
    "7 said they would pay."
)
COMPLETION_METRICS = {
    "interviewed": 12,
    "reported_problem": 9,
    "willing_to_pay": 7,
}
COMPLETION_NOTES = "Most interviews were with technical founders."
BLOCKED_REASON = "Waiting for customer interview access."


def _client() -> TestClient:
    return TestClient(app)


def _signup(client: TestClient, prefix: str = "status") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Founder",
            "email": f"{prefix}-{uuid.uuid4()}@example.com",
            "password": "valid-pass-1",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_company(client: TestClient, name: str = "Status Co") -> dict:
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


def _status_url(company_id: str, task_id: str) -> str:
    return f"/api/v1/companies/{company_id}/objective-tasks/{task_id}/status"


def _completion_status_payload() -> dict:
    return {
        "status": STATUS_COMPLETED,
        "result_summary": COMPLETION_SUMMARY,
        "result_metrics": COMPLETION_METRICS,
        "result_notes": COMPLETION_NOTES,
    }


async def _seed_pending_task(
    session: AsyncSession,
    *,
    company_name: str = "Seed Co",
    company_id: uuid.UUID | None = None,
) -> tuple[CompanyMember, ObjectiveTask, User]:
    user = User(email=f"status-{uuid.uuid4()}@example.com", name="Founder")
    session.add(user)
    await session.flush()
    if company_id is None:
        company = Company(
            name=company_name,
            slug=f"status-{uuid.uuid4().hex[:8]}",
            stage="mvp",
        )
        session.add(company)
        await session.flush()
    else:
        company = await session.get(Company, company_id)
        assert company is not None
    membership = CompanyMember(company_id=company.id, user_id=user.id, role="founder")
    session.add(membership)
    objective = Objective(
        company_id=company.id,
        title="Get customers",
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
async def test_pending_to_in_progress(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        updated = await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_IN_PROGRESS,
        )
    assert updated.status == STATUS_IN_PROGRESS
    assert updated.started_at is not None


@pytest.mark.asyncio
async def test_pending_to_completed(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        updated = await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_COMPLETED,
            result_summary=COMPLETION_SUMMARY,
            result_metrics=COMPLETION_METRICS,
            result_notes=COMPLETION_NOTES,
        )
    assert updated.status == STATUS_COMPLETED
    assert updated.result_summary == COMPLETION_SUMMARY


@pytest.mark.asyncio
async def test_in_progress_to_blocked_requires_reason(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_IN_PROGRESS,
        )
        with pytest.raises(ObjectiveTaskError) as exc_info:
            await transition_objective_task_status(
                session,
                company_id=membership.company_id,
                task_id=task.id,
                user=user,
                new_status=STATUS_BLOCKED,
            )
        assert exc_info.value.status_code == 400
        assert "blocked_reason" in exc_info.value.detail


@pytest.mark.asyncio
async def test_in_progress_to_blocked_with_reason(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_IN_PROGRESS,
        )
        blocked = await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_BLOCKED,
            blocked_reason=BLOCKED_REASON,
        )
    assert blocked.status == STATUS_BLOCKED
    assert blocked.blocked_reason == BLOCKED_REASON


@pytest.mark.asyncio
async def test_blocked_to_in_progress_clears_reason(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_IN_PROGRESS,
        )
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_BLOCKED,
            blocked_reason=BLOCKED_REASON,
        )
        resumed = await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_IN_PROGRESS,
        )
    assert resumed.status == STATUS_IN_PROGRESS
    assert resumed.blocked_reason is None


@pytest.mark.asyncio
async def test_in_progress_to_completed(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_IN_PROGRESS,
        )
        completed = await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_COMPLETED,
            result_summary=COMPLETION_SUMMARY,
        )
    assert completed.status == STATUS_COMPLETED


@pytest.mark.asyncio
async def test_blocked_to_completed(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_IN_PROGRESS,
        )
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_BLOCKED,
            blocked_reason=BLOCKED_REASON,
        )
        completed = await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_COMPLETED,
            result_summary=COMPLETION_SUMMARY,
        )
    assert completed.status == STATUS_COMPLETED
    assert completed.blocked_reason == BLOCKED_REASON


@pytest.mark.asyncio
async def test_completed_is_terminal(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_COMPLETED,
            result_summary=COMPLETION_SUMMARY,
        )
        for target in (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_BLOCKED):
            with pytest.raises(ObjectiveTaskError) as exc_info:
                await transition_objective_task_status(
                    session,
                    company_id=membership.company_id,
                    task_id=task.id,
                    user=user,
                    new_status=target,
                    blocked_reason=BLOCKED_REASON if target == STATUS_BLOCKED else None,
                    result_summary=COMPLETION_SUMMARY if target == STATUS_COMPLETED else None,
                )
            assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_invalid_transitions_rejected(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_IN_PROGRESS,
        )
        with pytest.raises(ObjectiveTaskError):
            await transition_objective_task_status(
                session,
                company_id=membership.company_id,
                task_id=task.id,
                user=user,
                new_status=STATUS_PENDING,
            )
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_BLOCKED,
            blocked_reason=BLOCKED_REASON,
        )
        with pytest.raises(ObjectiveTaskError):
            await transition_objective_task_status(
                session,
                company_id=membership.company_id,
                task_id=task.id,
                user=user,
                new_status=STATUS_PENDING,
            )


@pytest.mark.asyncio
async def test_same_status_transition_is_idempotent(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        first = await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_IN_PROGRESS,
        )
        second = await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_IN_PROGRESS,
        )
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_COMPLETED,
            result_summary=COMPLETION_SUMMARY,
        )
        third = await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_COMPLETED,
            result_summary="Should not overwrite.",
        )
    assert first.started_at == second.started_at
    assert third.result_summary == COMPLETION_SUMMARY


@pytest.mark.asyncio
async def test_cross_company_transition_blocked(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership_a, task_a, user_a = await _seed_pending_task(session, company_name="Company A")
        membership_b, _, _ = await _seed_pending_task(session, company_name="Company B")
        with pytest.raises(ObjectiveTaskError) as exc_info:
            await transition_objective_task_status(
                session,
                company_id=membership_b.company_id,
                task_id=task_a.id,
                user=user_a,
                new_status=STATUS_IN_PROGRESS,
            )
        assert exc_info.value.status_code == 404


def test_unauthorized_user_blocked() -> None:
    owner = _client()
    outsider = _client()
    _signup(owner, "owner-status")
    _signup(outsider, "outsider-status")
    company = _create_company(owner, "Owner Status Co")
    response = outsider.patch(
        _status_url(company["id"], str(uuid.uuid4())),
        json={"status": STATUS_IN_PROGRESS},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_completion_creates_evidence(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_COMPLETED,
            result_summary=COMPLETION_SUMMARY,
        )
        evidence = await get_evidence_for_objective_task(
            session,
            company_id=membership.company_id,
            task_id=task.id,
        )
    assert evidence is not None


@pytest.mark.asyncio
async def test_completion_from_in_progress_creates_evidence(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_IN_PROGRESS,
        )
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_COMPLETED,
            result_summary=COMPLETION_SUMMARY,
        )
        evidence = await get_evidence_for_objective_task(
            session,
            company_id=membership.company_id,
            task_id=task.id,
        )
    assert evidence is not None


@pytest.mark.asyncio
async def test_completion_from_blocked_creates_evidence(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_IN_PROGRESS,
        )
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_BLOCKED,
            blocked_reason=BLOCKED_REASON,
        )
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_COMPLETED,
            result_summary=COMPLETION_SUMMARY,
        )
        evidence = await get_evidence_for_objective_task(
            session,
            company_id=membership.company_id,
            task_id=task.id,
        )
    assert evidence is not None


@pytest.mark.asyncio
async def test_completion_creates_exactly_one_evidence(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_COMPLETED,
            result_summary=COMPLETION_SUMMARY,
        )
        count = await session.scalar(
            select(func.count())
            .select_from(Evidence)
            .where(Evidence.company_id == membership.company_id)
        )
    assert count == 1


@pytest.mark.asyncio
async def test_repeated_completion_does_not_duplicate_evidence(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_COMPLETED,
            result_summary=COMPLETION_SUMMARY,
        )
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_COMPLETED,
            result_summary="Retry should not duplicate.",
        )
        count = await session.scalar(
            select(func.count())
            .select_from(Evidence)
            .where(Evidence.company_id == membership.company_id)
        )
    assert count == 1


@pytest.mark.asyncio
async def test_evidence_failure_rolls_back_completion(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        task_id = task.id
        company_id = membership.company_id
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_IN_PROGRESS,
        )
        with patch(
            "app.services.objective_task_service.create_evidence_from_objective_task",
            side_effect=RuntimeError("evidence failed"),
        ):
            try:
                await transition_objective_task_status(
                    session,
                    company_id=membership.company_id,
                    task_id=task.id,
                    user=user,
                    new_status=STATUS_COMPLETED,
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
    assert refreshed.status == STATUS_IN_PROGRESS
    assert evidence_count == 0


@pytest.mark.asyncio
async def test_transitions_do_not_call_llm(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        with patch("app.services.llm.get_llm_provider") as mock_llm:
            await transition_objective_task_status(
                session,
                company_id=membership.company_id,
                task_id=task.id,
                user=user,
                new_status=STATUS_IN_PROGRESS,
            )
            await transition_objective_task_status(
                session,
                company_id=membership.company_id,
                task_id=task.id,
                user=user,
                new_status=STATUS_COMPLETED,
                result_summary=COMPLETION_SUMMARY,
            )
        mock_llm.assert_not_called()


def test_status_request_rejects_completed_by() -> None:
    client = _client()
    _signup(client, "reject-completed-by")
    company = _create_company(client, "Reject Co")
    response = client.patch(
        _status_url(company["id"], str(uuid.uuid4())),
        json={"status": STATUS_IN_PROGRESS, "completed_by": str(uuid.uuid4())},
    )
    assert response.status_code == 422


def test_status_request_rejects_completed_at() -> None:
    client = _client()
    _signup(client, "reject-completed-at")
    company = _create_company(client, "Reject At Co")
    response = client.patch(
        _status_url(company["id"], str(uuid.uuid4())),
        json={"status": STATUS_IN_PROGRESS, "completed_at": "2026-01-01T00:00:00Z"},
    )
    assert response.status_code == 422


def test_status_request_rejects_unexpected_fields() -> None:
    client = _client()
    _signup(client, "reject-extra")
    company = _create_company(client, "Extra Status Co")
    response = client.patch(
        _status_url(company["id"], str(uuid.uuid4())),
        json={"status": STATUS_IN_PROGRESS, "company_id": str(uuid.uuid4())},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_patch_status_full_flow(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    client = _client()
    signup = _signup(client, "api-flow")
    company = _create_company(client, "API Flow Co")
    async with async_session_factory() as session:
        membership, task, _ = await _seed_pending_task(
            session,
            company_id=uuid.UUID(company["id"]),
        )
        company_id = str(membership.company_id)
        task_id = str(task.id)

    start = client.patch(
        _status_url(company_id, task_id),
        json={"status": STATUS_IN_PROGRESS},
    )
    assert start.status_code == 200
    assert start.json()["status"] == STATUS_IN_PROGRESS
    assert start.json()["started_at"] is not None

    blocked = client.patch(
        _status_url(company_id, task_id),
        json={"status": STATUS_BLOCKED, "blocked_reason": BLOCKED_REASON},
    )
    assert blocked.status_code == 200
    assert blocked.json()["blocked_reason"] == BLOCKED_REASON

    resumed = client.patch(
        _status_url(company_id, task_id),
        json={"status": STATUS_IN_PROGRESS},
    )
    assert resumed.status_code == 200
    assert resumed.json()["blocked_reason"] is None

    completed = client.patch(
        _status_url(company_id, task_id),
        json=_completion_status_payload(),
    )
    assert completed.status_code == 200
    body = completed.json()
    assert body["status"] == STATUS_COMPLETED
    assert body["completed_by"] == signup["user"]["id"]
    assert body["completed_at"] is not None

    retry = client.patch(
        _status_url(company_id, task_id),
        json=_completion_status_payload(),
    )
    assert retry.status_code == 200

    invalid = client.patch(
        _status_url(company_id, task_id),
        json={"status": STATUS_IN_PROGRESS},
    )
    assert invalid.status_code == 400
