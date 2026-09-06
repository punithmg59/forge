"""Execution approval verification against persisted Approval records."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta

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

    # Check expiration
    if approval.expires_at is not None:
        expires_dt = datetime.fromisoformat(approval.expires_at)
        if datetime.now(UTC) >= expires_dt:
            raise ExecutionRunnerError("Execution plan has expired.", status_code=409)

    # Verify fingerprint matches current plan
    agent_task = await get_agent_task_for_company(
        db,
        company_id=company_id,
        agent_task_id=plan_agent_task_id,
    )
    if agent_task is None:
        raise ExecutionRunnerError("Execution plan not found.", status_code=404)

    current_plan = parse_plan_from_agent_task(agent_task)
    current_fingerprint = compute_plan_fingerprint(current_plan)

    if approval.plan_fingerprint != current_fingerprint:
        raise ExecutionRunnerError(
            "Execution plan has changed since approval. New approval required.",
            status_code=409,
        )

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

    plan = parse_plan_from_agent_task(agent_task)
    fingerprint = compute_plan_fingerprint(plan)

    # Plan expires 24 hours after request
    expires_at = (datetime.now(UTC) + timedelta(hours=24)).replace(microsecond=0).isoformat()

    description = _plan_description(agent_task)
    approval = Approval(
        company_id=company_id,
        agent_task_id=plan_agent_task_id,
        action_type=ACTION_TYPE_EXECUTION,
        description=description,
        risk_level=_plan_risk_level(agent_task),
        status=STATUS_PENDING,
        requested_at=_utcnow_iso(),
        plan_fingerprint=fingerprint,
        expires_at=expires_at,
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


def compute_plan_fingerprint(plan: ExecutionPlan) -> str:
    """
    Compute a deterministic SHA256 fingerprint of an execution plan.

    The fingerprint ensures plan immutability - if any material field changes,
    the fingerprint will not match and the approval becomes invalid.
    """
    canonical = json.dumps(
        {
            "goal": plan.goal,
            "rationale": plan.rationale,
            "risk_level": plan.risk_level,
            "steps": [
                {
                    "step_id": step.step_id,
                    "sequence": step.sequence,
                    "tool_name": step.tool_name,
                    "tool_version": step.tool_version,
                    "purpose": step.purpose,
                    "input": step.input,
                    "risk_level": step.risk_level,
                }
                for step in sorted(plan.steps, key=lambda s: s.sequence)
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
