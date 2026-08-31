"""Execution approval verification against persisted Approval records."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_task import AgentTask
from app.models.approval import Approval
from app.schemas.execution import ExecutionPlan
from app.services.approval_service import (
    ACTION_TYPE_EXECUTION,
    STATUS_APPROVED,
    STATUS_PENDING,
    get_agent_task_for_company,
)
from app.services.execution.audit import EXECUTION_PLAN_TASK_TYPE
from app.services.execution.errors import ExecutionNotApprovedError, ExecutionRunnerError


async def get_approved_execution_approval(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    plan_agent_task_id: uuid.UUID,
) -> Approval | None:
    result = await db.execute(
        select(Approval).where(
            Approval.company_id == company_id,
            Approval.agent_task_id == plan_agent_task_id,
            Approval.action_type == ACTION_TYPE_EXECUTION,
            Approval.status == STATUS_APPROVED,
        )
    )
    return result.scalar_one_or_none()


async def verify_execution_approved(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    plan_agent_task_id: uuid.UUID,
) -> Approval:
    approval = await get_approved_execution_approval(
        db,
        company_id=company_id,
        plan_agent_task_id=plan_agent_task_id,
    )
    if approval is None:
        raise ExecutionNotApprovedError()
    return approval


async def create_execution_approval(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    plan_agent_task_id: uuid.UUID,
) -> Approval:
    """Request founder approval for a persisted execution plan. Does not auto-approve."""
    agent_task = await get_agent_task_for_company(
        db,
        company_id=company_id,
        agent_task_id=plan_agent_task_id,
    )
    if agent_task is None:
        raise ExecutionRunnerError("Execution plan not found.", status_code=404)
    if agent_task.task_type != EXECUTION_PLAN_TASK_TYPE:
        raise ExecutionRunnerError("Agent task is not an execution plan.", status_code=400)

    existing = await db.execute(
        select(Approval).where(
            Approval.company_id == company_id,
            Approval.agent_task_id == plan_agent_task_id,
            Approval.status == STATUS_PENDING,
        )
    )
    pending = existing.scalar_one_or_none()
    if pending is not None:
        return pending

    description = _plan_description(agent_task)
    approval = Approval(
        company_id=company_id,
        agent_task_id=plan_agent_task_id,
        action_type=ACTION_TYPE_EXECUTION,
        description=description,
        risk_level=_plan_risk_level(agent_task),
        status=STATUS_PENDING,
        requested_at=_utcnow_iso(),
    )
    db.add(approval)
    await db.flush()
    return approval


def _plan_description(agent_task: AgentTask) -> str:
    if isinstance(agent_task.output, dict):
        goal = agent_task.output.get("goal")
        if isinstance(goal, str) and goal.strip():
            return goal.strip()
    return "Execution plan approval"


def _plan_risk_level(agent_task: AgentTask) -> str:
    if isinstance(agent_task.output, dict):
        risk = agent_task.output.get("risk_level")
        if risk in {"low", "medium", "high", "critical"}:
            return "medium" if risk == "critical" else risk
    return "low"


def _utcnow_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(microsecond=0).isoformat()


def parse_plan_from_agent_task(agent_task: AgentTask) -> ExecutionPlan:
    if not isinstance(agent_task.output, dict):
        raise ExecutionRunnerError("Execution plan payload is invalid.", status_code=400)
    try:
        return ExecutionPlan.model_validate(agent_task.output)
    except Exception as exc:
        raise ExecutionRunnerError("Execution plan payload is invalid.", status_code=400) from exc
