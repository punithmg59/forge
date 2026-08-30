"""Task 7.1 tests for ObjectiveTask completion and founder result capture."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.main import app
from app.models.company import Company
from app.models.company_member import CompanyMember
from app.models.evidence import Evidence
from app.models.learning import Learning
from app.models.objective import Objective
from app.models.objective_task import ObjectiveTask
from app.models.user import User
from app.services.objective_task_service import (
    STATUS_COMPLETED,
    STATUS_PENDING,
    complete_objective_task,
    get_objective_task_for_company,
    list_objective_tasks,
)


def _client() -> TestClient:
    return TestClient(app)


def _signup(client: TestClient, prefix: str = "complete") -> dict:
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


def _create_company(client: TestClient, name: str = "Complete Co") -> dict:
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


def _tasks_url(company_id: str, task_id: str | None = None, action: str | None = None) -> str:
    base = f"/api/v1/companies/{company_id}/objective-tasks"
    if task_id is None:
        return base
    if action:
        return f"{base}/{task_id}/{action}"
    return f"{base}/{task_id}"


async def _seed_pending_task(
    session: AsyncSession,
    *,
    company_name: str = "Seed Co",
    company_id: uuid.UUID | None = None,
) -> tuple[CompanyMember, ObjectiveTask, User]:
    user = User(email=f"complete-{uuid.uuid4()}@example.com", name="Founder")
    session.add(user)
    await session.flush()
    if company_id is None:
        company = Company(
            name=company_name,
            slug=f"complete-{uuid.uuid4().hex[:8]}",
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
async def test_authorized_user_can_complete_task(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session)
        completed = await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary="12 customers interviewed.",
            result_metrics={"interviewed": 12, "reported_problem": 9},
            result_notes="Most were technical founders.",
        )
    assert completed.status == STATUS_COMPLETED
    assert completed.result_summary == "12 customers interviewed."
    assert completed.result_metrics == {"interviewed": 12.0, "reported_problem": 9.0}
    assert completed.result_notes == "Most were technical founders."
    assert completed.completed_by == user.id
    assert completed.completed_at is not None


@pytest.mark.asyncio
async def test_service_persists_result_fields(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session, company_name="Service Co")
        completed = await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary="12 customers interviewed. 9 reported the same problem.",
            result_metrics={
                "interviewed": 12,
                "reported_problem": 9,
                "willing_to_pay": 7,
            },
            result_notes="Most interviews were with technical founders.",
        )
    assert completed.status == STATUS_COMPLETED
    assert completed.result_summary == (
        "12 customers interviewed. 9 reported the same problem."
    )
    assert completed.result_metrics == {
        "interviewed": 12.0,
        "reported_problem": 9.0,
        "willing_to_pay": 7.0,
    }
    assert completed.completed_by == user.id
    assert completed.completed_at is not None


@pytest.mark.asyncio
async def test_api_route_completes_task(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    client = _client()
    _signup(client, "api-route")
    company = _create_company(client, "Route Co")
    async with async_session_factory() as session:
        membership, task, _ = await _seed_pending_task(
            session,
            company_id=uuid.UUID(company["id"]),
        )
        route_company_id = str(membership.company_id)
        route_task_id = str(task.id)

    response = client.post(
        _tasks_url(route_company_id, route_task_id, "complete"),
        json={
            "result_summary": "Route completion summary.",
            "result_metrics": {"interviewed": 3},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == STATUS_COMPLETED
    assert body["result_summary"] == "Route completion summary."
    assert body["completed_by"] is not None
    assert body["completed_at"] is not None


def test_empty_result_summary_is_rejected() -> None:
    client = _client()
    _signup(client, "blank-summary")
    company = _create_company(client, "Blank Co")
    response = client.post(
        _tasks_url(company["id"], str(uuid.uuid4()), "complete"),
        json={"result_summary": "   "},
    )
    assert response.status_code == 422


def test_invalid_result_metrics_is_rejected() -> None:
    client = _client()
    _signup(client, "bad-metrics")
    company = _create_company(client, "Metrics Co")
    response = client.post(
        _tasks_url(company["id"], str(uuid.uuid4()), "complete"),
        json={
            "result_summary": "Done",
            "result_metrics": {"count": "not-a-number"},
        },
    )
    assert response.status_code == 422


def test_non_member_cannot_complete_another_company_task() -> None:
    owner = _client()
    outsider = _client()
    _signup(owner, "owner")
    _signup(outsider, "outsider")
    company = _create_company(owner, "Owner Co")
    response = outsider.post(
        _tasks_url(company["id"], str(uuid.uuid4()), "complete"),
        json={"result_summary": "Hacked"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_member_can_complete_company_task(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    founder_client = _client()
    _signup(founder_client, "founder-for-member")
    company = _create_company(founder_client, "Member Co")

    member_client = _client()
    member_payload = _signup(member_client, "plain-member")

    async with async_session_factory() as session:
        membership, task, _founder = await _seed_pending_task(
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

    response = member_client.post(
        _tasks_url(company_id, task_id, "complete"),
        json={"result_summary": "Completed by member."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == STATUS_COMPLETED


def test_invalid_task_id_returns_404() -> None:
    client = _client()
    _signup(client, "missing-task")
    company = _create_company(client, "Missing Co")
    response = client.post(
        _tasks_url(company["id"], str(uuid.uuid4()), "complete"),
        json={"result_summary": "Done"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_completing_already_completed_task_is_idempotent(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session, company_name="Idempotent Co")
        first = await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary="First completion.",
        )
        second = await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary="Should not overwrite.",
        )
    assert first.id == second.id
    assert second.status == STATUS_COMPLETED
    assert second.result_summary == "First completion."
    assert second.completed_by == user.id


@pytest.mark.asyncio
async def test_completion_creates_evidence_not_learning(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session, company_name="Evidence Co")
        evidence_before = await session.scalar(select(func.count()).select_from(Evidence))
        learning_before = await session.scalar(select(func.count()).select_from(Learning))
        await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary="12 customers interviewed.",
            result_metrics={"interviewed": 12},
        )
        evidence_after = await session.scalar(select(func.count()).select_from(Evidence))
        learning_after = await session.scalar(select(func.count()).select_from(Learning))
    assert evidence_after == evidence_before + 1
    assert learning_before == learning_after


@pytest.mark.asyncio
async def test_cross_company_task_lookup_returns_none(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership_a, task_a, _user_a = await _seed_pending_task(session, company_name="Company A")
        membership_b, _task_b, _user_b = await _seed_pending_task(session, company_name="Company B")
        fetched = await get_objective_task_for_company(
            session,
            company_id=membership_b.company_id,
            task_id=task_a.id,
        )
    assert fetched is None
    assert membership_a.company_id != membership_b.company_id


def test_unauthenticated_complete_returns_401() -> None:
    client = _client()
    response = client.post(
        _tasks_url(str(uuid.uuid4()), str(uuid.uuid4()), "complete"),
        json={"result_summary": "Done"},
    )
    assert response.status_code == 401


def test_malicious_extra_fields_rejected() -> None:
    client = _client()
    _signup(client, "extra-fields")
    company = _create_company(client, "Extra Co")
    response = client.post(
        _tasks_url(company["id"], str(uuid.uuid4()), "complete"),
        json={
            "result_summary": "Done",
            "completed_by": str(uuid.uuid4()),
            "company_id": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_task6_approval_created_task_can_still_be_listed(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, task, user = await _seed_pending_task(session, company_name="Regression Co")
        await complete_objective_task(
            session,
            task=task,
            user=user,
            result_summary="Regression complete.",
        )
        tasks = await list_objective_tasks(session, company_id=membership.company_id)
    assert len(tasks) == 1
    assert tasks[0].status == STATUS_COMPLETED
