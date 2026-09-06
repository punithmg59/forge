"""Build founder-facing execution review responses from Approval and AgentTask."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_task import AgentTask
from app.models.approval import Approval
from app.schemas.execution import (
    ExecutionReview,
    ExecutionStepReview,
)
from app.services.execution.approval_verification import parse_plan_from_agent_task


async def execution_review_from_approval(
    db: AsyncSession,
    approval: Approval,
    *,
    execution_id: uuid.UUID,
) -> ExecutionReview:
    """Build a founder-facing review from an execution approval."""
    if approval.agent_task_id is None:
        raise ValueError("Execution approval must have an agent_task_id")

    agent_task = await db.get(AgentTask, approval.agent_task_id)
    if agent_task is None:
        raise ValueError("Agent task not found")

    plan = parse_plan_from_agent_task(agent_task)

    # Extract execution identity from agent task output if available
    execution_identity = (
        agent_task.output.get("identity")
        if isinstance(agent_task.output, dict)
        else None
    )
    trace_id = (
        execution_identity.get("trace_id")
        if isinstance(execution_identity, dict)
        else "unknown"
    )

    # Build step reviews
    step_reviews = [
        ExecutionStepReview(
            step_id=step.step_id,
            sequence=step.sequence,
            tool_name=step.tool_name,
            tool_version=step.tool_version,
            purpose=step.purpose,
            input=_sanitize_step_input(step.input),
            expected_output=step.expected_output,
            risk_level=step.risk_level,
            step_category=step.step_category,
            approval_required=step.approval_required,
            timeout_ms=step.timeout_ms,
        )
        for step in sorted(plan.steps, key=lambda s: s.sequence)
    ]

    # Build tool summary
    tool_summary = list({f"{step.tool_name}:{step.tool_version}" for step in plan.steps})

    return ExecutionReview(
        execution_id=execution_id,
        approval_id=approval.id,
        company_id=approval.company_id,
        objective_id=agent_task.objective_id,
        objective_task_id=agent_task.objective_task_id,
        agent_type=agent_task.agent_type,
        goal=plan.goal,
        rationale=plan.rationale,
        risk_level=plan.risk_level,
        status=approval.status,
        steps=step_reviews,
        tool_summary=tool_summary,
        approval_required=True,
        plan_fingerprint=approval.plan_fingerprint or "",
        expires_at=approval.expires_at,
        requested_at=approval.requested_at,
        trace_id=trace_id,
    )


def _sanitize_step_input(input_data: dict) -> dict:
    """
    Sanitize tool inputs for founder review.

    Remove or redact sensitive fields that should not be displayed.
    """
    sensitive_keys = {
        "api_key",
        "password",
        "secret",
        "token",
        "authorization",
        "bearer",
        "credential",
    }

    sanitized = {}
    for key, value in input_data.items():
        if key.lower() in sensitive_keys:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_step_input(value)
        elif isinstance(value, list):
            sanitized[key] = [_sanitize_list_item(item) for item in value]
        else:
            sanitized[key] = value

    return sanitized


def _sanitize_list_item(item):
    """Sanitize items in lists within tool inputs."""
    if isinstance(item, dict):
        return _sanitize_step_input(item)
    elif isinstance(item, list):
        return [_sanitize_list_item(sub_item) for sub_item in item]
    return item
