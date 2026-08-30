"""ObjectiveTask queries, execution state machine, and founder result capture."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_task import AgentTask
from app.models.approval import Approval
from app.models.evidence import Evidence
from app.models.learning import Learning
from app.models.objective import Objective
from app.models.objective_task import ObjectiveTask
from app.models.user import User
from app.services.evidence_service import (
    create_evidence_from_objective_task,
    get_evidence_for_objective_task,
)

STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_BLOCKED = "blocked"
STATUS_COMPLETED = "completed"

ALL_STATUSES = frozenset(
    {STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_BLOCKED, STATUS_COMPLETED}
)
COMPLETABLE_STATUSES = frozenset(
    {STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_BLOCKED}
)

_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    STATUS_PENDING: frozenset({STATUS_IN_PROGRESS, STATUS_COMPLETED}),
    STATUS_IN_PROGRESS: frozenset({STATUS_BLOCKED, STATUS_COMPLETED}),
    STATUS_BLOCKED: frozenset({STATUS_IN_PROGRESS, STATUS_COMPLETED}),
    STATUS_COMPLETED: frozenset(),
}


class ObjectiveTaskError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


@dataclass(frozen=True)
class ObjectiveTaskDetailData:
    task: ObjectiveTask
    objective: Objective | None
    evidence: Evidence | None
    learnings: list[Learning]
    agent_task: AgentTask | None
    approval: Approval | None


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def validate_status_transition(current_status: str, new_status: str) -> None:
    if current_status == new_status:
        return
    allowed = _ALLOWED_TRANSITIONS.get(current_status, frozenset())
    if new_status not in allowed:
        raise ObjectiveTaskError(
            f"Cannot transition task from '{current_status}' to '{new_status}'",
            400,
        )


async def list_objective_tasks(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
) -> list[ObjectiveTask]:
    result = await db.execute(
        select(ObjectiveTask)
        .where(ObjectiveTask.company_id == company_id)
        .order_by(ObjectiveTask.created_at.desc())
    )
    return list(result.scalars().all())


async def get_objective_task_for_company(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    task_id: uuid.UUID,
) -> ObjectiveTask | None:
    task = await db.get(ObjectiveTask, task_id)
    if task is None or task.company_id != company_id:
        return None
    return task


async def get_objective_task_detail(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    task_id: uuid.UUID,
) -> ObjectiveTaskDetailData | None:
    task = await get_objective_task_for_company(
        db,
        company_id=company_id,
        task_id=task_id,
    )
    if task is None:
        return None

    objective = await db.get(Objective, task.objective_id)
    if objective is not None and objective.company_id != company_id:
        objective = None

    evidence = await get_evidence_for_objective_task(
        db,
        company_id=company_id,
        task_id=task.id,
    )

    learnings: list[Learning] = []
    if evidence is not None:
        learning_result = await db.execute(
            select(Learning)
            .where(
                Learning.company_id == company_id,
                Learning.evidence_id == evidence.id,
            )
            .order_by(Learning.created_at.desc(), Learning.id.desc())
        )
        learnings = list(learning_result.scalars().all())

    agent_task_result = await db.execute(
        select(AgentTask)
        .where(
            AgentTask.company_id == company_id,
            AgentTask.objective_task_id == task.id,
        )
        .order_by(AgentTask.created_at.desc(), AgentTask.id.desc())
        .limit(1)
    )
    agent_task = agent_task_result.scalar_one_or_none()

    approval: Approval | None = None
    if agent_task is not None:
        approval_result = await db.execute(
            select(Approval)
            .where(
                Approval.company_id == company_id,
                Approval.agent_task_id == agent_task.id,
            )
            .order_by(Approval.requested_at.desc(), Approval.id.desc())
            .limit(1)
        )
        approval = approval_result.scalar_one_or_none()

    return ObjectiveTaskDetailData(
        task=task,
        objective=objective,
        evidence=evidence,
        learnings=learnings,
        agent_task=agent_task,
        approval=approval,
    )


async def update_objective_task(
    db: AsyncSession,
    *,
    task: ObjectiveTask,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
) -> ObjectiveTask:
    if title is not None:
        task.title = title
    if description is not None:
        task.description = description
    if priority is not None:
        task.priority = priority

    await db.commit()
    await db.refresh(task)
    return task


async def complete_objective_task(
    db: AsyncSession,
    *,
    task: ObjectiveTask,
    user: User,
    result_summary: str,
    result_metrics: dict[str, float] | None = None,
    result_notes: str | None = None,
) -> ObjectiveTask:
    if task.status == STATUS_COMPLETED:
        return task

    if task.status not in COMPLETABLE_STATUSES:
        raise ObjectiveTaskError(
            f"Cannot complete task with status '{task.status}'",
            400,
        )

    task.status = STATUS_COMPLETED
    task.result_summary = result_summary
    task.result_metrics = result_metrics
    task.result_notes = result_notes
    task.completed_by = user.id
    task.completed_at = _utcnow_iso()
    await create_evidence_from_objective_task(db, task=task)
    await db.commit()
    await db.refresh(task)
    return task


async def transition_objective_task_status(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    task_id: uuid.UUID,
    user: User,
    new_status: str,
    blocked_reason: str | None = None,
    result_summary: str | None = None,
    result_metrics: dict[str, float] | None = None,
    result_notes: str | None = None,
) -> ObjectiveTask:
    if new_status not in ALL_STATUSES:
        raise ObjectiveTaskError(f"Unsupported status '{new_status}'", 400)

    task = await get_objective_task_for_company(
        db,
        company_id=company_id,
        task_id=task_id,
    )
    if task is None:
        raise ObjectiveTaskError("Task not found", 404)

    if new_status == STATUS_COMPLETED:
        if result_summary is None or not result_summary.strip():
            raise ObjectiveTaskError("result_summary is required to complete a task", 400)
        return await complete_objective_task(
            db,
            task=task,
            user=user,
            result_summary=result_summary.strip(),
            result_metrics=result_metrics,
            result_notes=result_notes,
        )

    if task.status == new_status:
        return task

    validate_status_transition(task.status, new_status)

    if new_status == STATUS_BLOCKED:
        if blocked_reason is None or not blocked_reason.strip():
            raise ObjectiveTaskError(
                "blocked_reason is required when blocking a task",
                400,
            )
        task.blocked_reason = blocked_reason.strip()
        task.status = STATUS_BLOCKED
    elif new_status == STATUS_IN_PROGRESS:
        if task.status == STATUS_BLOCKED:
            task.blocked_reason = None
        if task.started_at is None:
            task.started_at = _utcnow_iso()
        task.status = STATUS_IN_PROGRESS
    else:
        raise ObjectiveTaskError(f"Unsupported status '{new_status}'", 400)

    await db.commit()
    await db.refresh(task)
    return task
