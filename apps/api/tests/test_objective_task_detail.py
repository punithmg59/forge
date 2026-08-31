"""Task 8.2 tests for ObjectiveTask detail and metadata update APIs."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.main import app
from app.models.agent_task import AgentTask
from app.models.approval import Approval
from app.models.company import Company
from app.models.company_member import CompanyMember
from app.models.evidence import Evidence
from app.models.learning import Learning
from app.models.objective import Objective
from app.models.objective_task import ObjectiveTask
from app.models.user import User
from app.schemas.objective_task import ObjectiveTaskDetailResponse
from app.services.evidence_service import get_evidence_for_objective_task
from app.services.objective_task_service import (
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
    complete_objective_task,
    get_objective_task_detail,
    transition_objective_task_status,
)

COMPLETION_SUMMARY = "12 customers interviewed."
BLOCKED_REASON = "Waiting for customer interview access."


def _client() -> TestClient:
    return TestClient(app)


def _signup(client: TestClient, prefix: str = "detail") -> dict:
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


def _create_company(client: TestClient, name: str = "Detail Co") -> dict:
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


def _task_url(company_id: str, task_id: str, suffix: str | None = None) -> str:
    base = f"/api/v1/companies/{company_id}/objective-tasks/{task_id}"
    if suffix:
        return f"{base}/{suffix}"
    return base


async def _seed_pending_task(
    session: AsyncSession,
    *,
    company_name: str = "Seed Co",
    company_id: uuid.UUID | None = None,
    with_provenance: bool = False,
) -> tuple[CompanyMember, ObjectiveTask, User]:
    user = User(email=f"detail-{uuid.uuid4()}@example.com", name="Founder")
    session.add(user)
    await session.flush()
    if company_id is None:
        company = Company(
            name=company_name,
            slug=f"detail-{uuid.uuid4().hex[:8]}",
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
    await session.flush()

    if with_provenance:
        agent_task = AgentTask(
            company_id=company.id,
            agent_run_id=None,
            objective_task_id=task.id,
            agent_type="head",
            task_type="recommendation",
            status="completed",
            input={"question": "What should I focus on next?"},
            output={
                "title": "Interview potential customers",
                "recommendation": "Interview 12 potential customers before increasing acquisition spend.",
                "rationale": "Validate the customer problem before investing further in acquisition.",
                "proposed_action": {
                    "type": "task",
                    "title": "Run five interviews",
                    "description": "Ask about onboarding pain.",
                },
                "sources": [],
                "confidence": "high",
            },
        )
        session.add(agent_task)
        await session.flush()
        approval = Approval(
            company_id=company.id,
            agent_task_id=agent_task.id,
            action_type="task",
            description="Approve founder task",
            risk_level="low",
            status="approved",
            requested_at="2026-01-01T00:00:00+00:00",
            resolved_at="2026-01-01T00:00:00+00:00",
            resolved_by=user.id,
        )
        session.add(approval)

    await session.commit()
    await session.refresh(membership)
    await session.refresh(task)
    await session.refresh(user)
    return membership, task, user


@pytest.mark.asyncio
async def test_member_can_retrieve_own_company_task(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    client = _client()
    _signup(client, "member-get")
    company = _create_company(client, "Member Get Co")
    async with async_session_factory() as session:
        membership, task, _ = await _seed_pending_task(
            session,
            company_id=uuid.UUID(company["id"]),
        )
        company_id = str(membership.company_id)
        task_id = str(task.id)

    response = client.get(_task_url(company_id, task_id))
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == task_id
    assert body["title"] == "Run five interviews"


def test_non_member_cannot_retrieve_task() -> None:
    owner = _client()
    outsider = _client()
    _signup(owner, "owner-detail")
    _signup(outsider, "outsider-detail")
    company = _create_company(owner, "Owner Detail Co")
    response = outsider.get(_task_url(company["id"], str(uuid.uuid4())))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_wrong_company_task_is_blocked(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    client = _client()
    _signup(client, "wrong-company")
    company = _create_company(client, "Wrong Co")
    async with async_session_factory() as session:
        membership_a, task_a, _ = await _seed_pending_task(session, company_name="Company A")
        _membership_b, _, _ = await _seed_pending_task(session, company_name="Company B")
        wrong_company_id = str(membership_a.company_id)
        task_a_id = str(task_a.id)

    response = client.get(_task_url(company["id"], task_a_id))
    assert response.status_code == 404
    assert wrong_company_id != company["id"]


def test_missing_task_returns_404() -> None:
    client = _client()
    _signup(client, "missing-detail")
    company = _create_company(client, "Missing Co")
    response = client.get(_task_url(company["id"], str(uuid.uuid4())))
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_detail_includes_objective_information(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, _ = await _seed_pending_task(session)
        detail = await get_objective_task_detail(
            session,
            company_id=membership.company_id,
            task_id=task.id,
        )
    assert detail is not None
    response = ObjectiveTaskDetailResponse.from_detail(detail)
    assert response.objective is not None
    assert response.objective.title == "Get customers"
    assert response.objective.status == "active"


@pytest.mark.asyncio
async def test_detail_includes_status_and_execution_timestamps(
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
        detail = await get_objective_task_detail(
            session,
            company_id=membership.company_id,
            task_id=task.id,
        )
    assert detail is not None
    assert detail.task.status == STATUS_IN_PROGRESS
    assert detail.task.started_at is not None


@pytest.mark.asyncio
async def test_completed_task_includes_result_fields(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary=COMPLETION_SUMMARY,
            result_metrics={"interviewed": 12},
            result_notes="Notes",
        )
        detail = await get_objective_task_detail(
            session,
            company_id=membership.company_id,
            task_id=task.id,
        )
    response = ObjectiveTaskDetailResponse.from_detail(detail)
    assert response.result is not None
    assert response.result.summary == COMPLETION_SUMMARY
    assert response.result.metrics == {"interviewed": 12.0}


@pytest.mark.asyncio
async def test_completed_task_exposes_evidence_and_provenance(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(
            session,
            with_provenance=True,
        )
        await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary=COMPLETION_SUMMARY,
        )
        detail = await get_objective_task_detail(
            session,
            company_id=membership.company_id,
            task_id=task.id,
        )
    response = ObjectiveTaskDetailResponse.from_detail(detail)
    assert len(response.evidence) == 1
    assert response.provenance is not None
    assert response.provenance.agent_task_id is not None
    assert response.provenance.approval_id is not None


@pytest.mark.asyncio
async def test_detail_exposes_recommendation_and_approval_context(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, _ = await _seed_pending_task(
            session,
            with_provenance=True,
        )
        detail = await get_objective_task_detail(
            session,
            company_id=membership.company_id,
            task_id=task.id,
        )
    response = ObjectiveTaskDetailResponse.from_detail(detail)
    assert response.recommendation is not None
    assert "Interview 12 potential customers" in response.recommendation.recommendation
    assert response.recommendation_question == "What should I focus on next?"
    assert response.approval_context is not None
    assert response.approval_context.status == "approved"
    assert response.approval_context.resolved_at is not None


@pytest.mark.asyncio
async def test_detail_without_provenance_has_no_recommendation_context(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, _ = await _seed_pending_task(session)
        detail = await get_objective_task_detail(
            session,
            company_id=membership.company_id,
            task_id=task.id,
        )
    response = ObjectiveTaskDetailResponse.from_detail(detail)
    assert response.recommendation is None
    assert response.approval_context is None
    assert response.recommendation_question is None


@pytest.mark.asyncio
async def test_founder_can_update_allowed_fields(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    client = _client()
    _signup(client, "founder-update")
    company = _create_company(client, "Update Co")
    async with async_session_factory() as session:
        membership, task, _ = await _seed_pending_task(
            session,
            company_id=uuid.UUID(company["id"]),
        )
        company_id = str(membership.company_id)
        task_id = str(task.id)

    response = client.patch(
        _task_url(company_id, task_id),
        json={
            "title": "Interview 12 potential customers",
            "description": "Updated description.",
            "priority": "high",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Interview 12 potential customers"
    assert body["description"] == "Updated description."
    assert body["priority"] == "high"


@pytest.mark.asyncio
async def test_member_cannot_update_task_metadata(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    founder_client = _client()
    _signup(founder_client, "founder-for-member-update")
    company = _create_company(founder_client, "Member Update Co")

    member_client = _client()
    member_payload = _signup(member_client, "member-update")

    async with async_session_factory() as session:
        membership, task, _ = await _seed_pending_task(
            session,
            company_id=uuid.UUID(company["id"]),
        )
        member_user = await session.get(User, uuid.UUID(member_payload["user"]["id"]))
        assert member_user is not None
        session.add(
            CompanyMember(
                company_id=membership.company_id,
                user_id=member_user.id,
                role="member",
            )
        )
        await session.commit()
        company_id = str(membership.company_id)
        task_id = str(task.id)

    response = member_client.patch(
        _task_url(company_id, task_id),
        json={"title": "Blocked update"},
    )
    assert response.status_code == 403


def test_update_rejects_company_id() -> None:
    client = _client()
    _signup(client, "reject-company")
    company = _create_company(client, "Reject Company Co")
    response = client.patch(
        _task_url(company["id"], str(uuid.uuid4())),
        json={"company_id": str(uuid.uuid4()), "title": "Hack"},
    )
    assert response.status_code == 422


def test_update_rejects_objective_id() -> None:
    client = _client()
    _signup(client, "reject-objective")
    company = _create_company(client, "Reject Objective Co")
    response = client.patch(
        _task_url(company["id"], str(uuid.uuid4())),
        json={"objective_id": str(uuid.uuid4()), "title": "Hack"},
    )
    assert response.status_code == 422


def test_update_rejects_status() -> None:
    client = _client()
    _signup(client, "reject-status")
    company = _create_company(client, "Reject Status Co")
    response = client.patch(
        _task_url(company["id"], str(uuid.uuid4())),
        json={"status": STATUS_COMPLETED, "title": "Hack"},
    )
    assert response.status_code == 422


def test_update_rejects_completed_by() -> None:
    client = _client()
    _signup(client, "reject-completed-by")
    company = _create_company(client, "Reject Completed By Co")
    response = client.patch(
        _task_url(company["id"], str(uuid.uuid4())),
        json={"completed_by": str(uuid.uuid4())},
    )
    assert response.status_code == 422


def test_update_rejects_completed_at() -> None:
    client = _client()
    _signup(client, "reject-completed-at")
    company = _create_company(client, "Reject Completed At Co")
    response = client.patch(
        _task_url(company["id"], str(uuid.uuid4())),
        json={"completed_at": "2026-01-01T00:00:00Z"},
    )
    assert response.status_code == 422


def test_status_endpoint_uses_transition_service() -> None:
    from datetime import UTC, datetime

    client = _client()
    _signup(client, "status-service")
    company = _create_company(client, "Status Service Co")
    with patch(
        "app.api.routes.objective_tasks.objective_task_service.transition_objective_task_status",
        new_callable=AsyncMock,
    ) as mock_transition:
        from app.models.objective_task import ObjectiveTask

        now = datetime.now(UTC)
        mock_task = ObjectiveTask(
            id=uuid.uuid4(),
            company_id=uuid.UUID(company["id"]),
            objective_id=uuid.uuid4(),
            title="Mock",
            description=None,
            capability="founder",
            status=STATUS_IN_PROGRESS,
            priority="medium",
            requires_approval=False,
            created_at=now,
            updated_at=now,
        )
        mock_transition.return_value = mock_task
        response = client.patch(
            _task_url(company["id"], str(uuid.uuid4()), "status"),
            json={"status": STATUS_IN_PROGRESS},
        )
    assert response.status_code == 200
    mock_transition.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_transition_still_rejected(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    client = _client()
    _signup(client, "invalid-transition")
    company = _create_company(client, "Invalid Transition Co")
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(
            session,
            company_id=uuid.UUID(company["id"]),
        )
        await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary=COMPLETION_SUMMARY,
        )
        company_id = str(membership.company_id)
        task_id = str(task.id)

    response = client.patch(
        _task_url(company_id, task_id, "status"),
        json={"status": STATUS_IN_PROGRESS},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_blocked_reason_validation_still_enforced(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    client = _client()
    _signup(client, "blocked-reason")
    company = _create_company(client, "Blocked Reason Co")
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(
            session,
            company_id=uuid.UUID(company["id"]),
        )
        await transition_objective_task_status(
            session,
            company_id=membership.company_id,
            task_id=task.id,
            user=user,
            new_status=STATUS_IN_PROGRESS,
        )
        company_id = str(membership.company_id)
        task_id = str(task.id)

    response = client.patch(
        _task_url(company_id, task_id, "status"),
        json={"status": STATUS_BLOCKED},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_complete_endpoint_still_works(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    client = _client()
    _signup(client, "complete-still")
    company = _create_company(client, "Complete Still Co")
    async with async_session_factory() as session:
        membership, task, _ = await _seed_pending_task(
            session,
            company_id=uuid.UUID(company["id"]),
        )
        company_id = str(membership.company_id)
        task_id = str(task.id)

    response = client.post(
        _task_url(company_id, task_id, "complete"),
        json={"result_summary": COMPLETION_SUMMARY},
    )
    assert response.status_code == 200
    assert response.json()["status"] == STATUS_COMPLETED


@pytest.mark.asyncio
async def test_completion_creates_evidence(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary=COMPLETION_SUMMARY,
        )
        evidence = await get_evidence_for_objective_task(
            session,
            company_id=membership.company_id,
            task_id=task.id,
        )
    assert evidence is not None


@pytest.mark.asyncio
async def test_repeated_completion_does_not_duplicate_evidence(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary=COMPLETION_SUMMARY,
        )
        await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary="Retry",
        )
        count = await session.scalar(
            select(func.count())
            .select_from(Evidence)
            .where(Evidence.company_id == membership.company_id)
        )
    assert count == 1


@pytest.mark.asyncio
async def test_completion_rollback_remains_safe(
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


def test_company_b_cannot_read_company_a_task() -> None:
    owner = _client()
    outsider = _client()
    _signup(owner, "owner-a")
    _signup(outsider, "outsider-b")
    company_a = _create_company(owner, "Company A Detail")
    company_b = _create_company(outsider, "Company B Detail")
    response = outsider.get(_task_url(company_a["id"], str(uuid.uuid4())))
    assert response.status_code == 403
    assert company_a["id"] != company_b["id"]


def test_company_b_cannot_update_company_a_task() -> None:
    owner = _client()
    outsider = _client()
    _signup(owner, "owner-a-update")
    _signup(outsider, "outsider-b-update")
    company_a = _create_company(owner, "Company A Update")
    _create_company(outsider, "Company B Update")
    response = outsider.patch(
        _task_url(company_a["id"], str(uuid.uuid4())),
        json={"title": "Hack"},
    )
    assert response.status_code == 403


def test_company_b_cannot_complete_company_a_task() -> None:
    owner = _client()
    outsider = _client()
    _signup(owner, "owner-a-complete")
    _signup(outsider, "outsider-b-complete")
    company_a = _create_company(owner, "Company A Complete")
    _create_company(outsider, "Company B Complete")
    response = outsider.post(
        _task_url(company_a["id"], str(uuid.uuid4()), "complete"),
        json={"result_summary": COMPLETION_SUMMARY},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_does_not_mutate_database(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, _ = await _seed_pending_task(session)
        evidence_before = await session.scalar(select(func.count()).select_from(Evidence))
        learning_before = await session.scalar(select(func.count()).select_from(Learning))
        await get_objective_task_detail(
            session,
            company_id=membership.company_id,
            task_id=task.id,
        )
        evidence_after = await session.scalar(select(func.count()).select_from(Evidence))
        learning_after = await session.scalar(select(func.count()).select_from(Learning))
    assert evidence_before == evidence_after
    assert learning_before == learning_after


@pytest.mark.asyncio
async def test_patch_metadata_does_not_create_evidence(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    client = _client()
    _signup(client, "patch-no-evidence")
    company = _create_company(client, "Patch No Evidence Co")
    async with async_session_factory() as session:
        membership, task, _ = await _seed_pending_task(
            session,
            company_id=uuid.UUID(company["id"]),
        )
        company_id = membership.company_id
        task_id = str(task.id)

    response = client.patch(
        _task_url(str(company_id), task_id),
        json={"title": "Updated without evidence"},
    )
    assert response.status_code == 200
    async with async_session_factory() as session:
        evidence_count = await session.scalar(
            select(func.count())
            .select_from(Evidence)
            .where(Evidence.company_id == company_id)
        )
    assert evidence_count == 0


@pytest.mark.asyncio
async def test_get_does_not_call_llm(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, _ = await _seed_pending_task(session)
        with patch("app.services.llm.get_llm_provider") as mock_llm:
            await get_objective_task_detail(
                session,
                company_id=membership.company_id,
                task_id=task.id,
            )
        mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_patch_does_not_call_llm(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    client = _client()
    _signup(client, "patch-no-llm")
    company = _create_company(client, "Patch No LLM Co")
    async with async_session_factory() as session:
        membership, task, _ = await _seed_pending_task(
            session,
            company_id=uuid.UUID(company["id"]),
        )
        company_id = str(membership.company_id)
        task_id = str(task.id)

    with patch("app.services.llm.get_llm_provider") as mock_llm:
        response = client.patch(
            _task_url(company_id, task_id),
            json={"title": "No LLM title"},
        )
    assert response.status_code == 200
    mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_detail_query_count_is_bounded(
    async_session_factory: async_sessionmaker[AsyncSession],
    engine: AsyncEngine,
) -> None:
    query_count = 0

    def _before_cursor_execute(
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ) -> None:
        nonlocal query_count
        query_count += 1

    event.listen(engine.sync_engine, "before_cursor_execute", _before_cursor_execute)
    try:
        async with async_session_factory() as session:
            membership, task, user = await _seed_pending_task(
                session,
                with_provenance=True,
            )
            await complete_objective_task(
                session,
                task=task,
                user=user,
                result_summary=COMPLETION_SUMMARY,
            )
            query_count = 0
            await get_objective_task_detail(
                session,
                company_id=membership.company_id,
                task_id=task.id,
            )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", _before_cursor_execute)

    assert query_count <= 6
