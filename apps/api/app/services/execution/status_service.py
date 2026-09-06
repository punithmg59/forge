"""Execution status retrieval from AgentRun/AgentTask persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.models.agent_task import AgentTask
from app.models.approval import Approval
from app.schemas.execution import (
    ExecutionPlan,
    ExecutionRunMetrics,
    ExecutionStatus,
    ExecutionStatusResponse,
    ExecutionStepResult,
)
from app.services.execution.audit import (
    EXECUTION_PLAN_TASK_TYPE,
    EXECUTION_STATUS_TASK_TYPE,
)


async def get_execution_status(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    execution_id: uuid.UUID,
) -> ExecutionStatusResponse:
    """
    Retrieve server-authoritative execution status from AgentRun/AgentTask.

    Raises:
        ValueError: If execution not found or does not belong to company.
    """
    # Find AgentRun by trace_id (which contains execution_id)
    # The execution_id is stored in AgentTask.input["execution_id"]
    agent_run_result = await db.execute(
        select(AgentRun).where(
            AgentRun.company_id == company_id,
            AgentRun.agent_type == "execution_runner",
        )
    )
    agent_runs = agent_run_result.scalars().all()

    # Find the run that contains our execution_id
    matching_run: AgentRun | None = None
    for run in agent_runs:
        # Check if any task in this run has our execution_id
        task_result = await db.execute(
            select(AgentTask).where(
                AgentTask.agent_run_id == run.id,
                AgentTask.task_type == EXECUTION_PLAN_TASK_TYPE,
            )
        )
        plan_task = task_result.scalar_one_or_none()
        if plan_task and plan_task.input:
            task_execution_id = plan_task.input.get("execution_id")
            if task_execution_id == str(execution_id):
                matching_run = run
                break

    if matching_run is None:
        raise ValueError("Execution not found.")

    # Get plan task
    plan_task_result = await db.execute(
        select(AgentTask).where(
            AgentTask.agent_run_id == matching_run.id,
            AgentTask.task_type == EXECUTION_PLAN_TASK_TYPE,
        )
    )
    plan_task = plan_task_result.scalar_one_or_none()

    # Get status task
    status_task_result = await db.execute(
        select(AgentTask).where(
            AgentTask.agent_run_id == matching_run.id,
            AgentTask.task_type == EXECUTION_STATUS_TASK_TYPE,
        )
    )
    status_task = status_task_result.scalar_one_or_none()

    # Get approval if available
    approval: Approval | None = None
    if plan_task and plan_task.objective_task_id:
        approval_result = await db.execute(
            select(Approval).where(
                Approval.company_id == company_id,
                Approval.agent_task_id == plan_task.objective_task_id,
                Approval.action_type == "execution",
            )
        )
        approval = approval_result.scalar_one_or_none()

    # Build response
    status = ExecutionStatus.requested
    started_at: str | None = None
    completed_at: str | None = None
    failure_reason: str | None = None
    cancel_reason: str | None = None
    metrics: ExecutionRunMetrics | None = None

    if status_task and status_task.output:
        status_output = status_task.output
        status_str = status_output.get("status", "requested")
        if status_str in ExecutionStatus.__args__:
            status = status_str  # type: ignore
        failure_reason = status_output.get("failure_reason")
        cancel_reason = status_output.get("cancel_reason")

    started_at = matching_run.started_at
    completed_at = matching_run.completed_at

    # Parse plan from plan_task
    plan: ExecutionPlan | None = None
    plan_fingerprint: str | None = None
    if plan_task and plan_task.output:
        try:
            plan_data = plan_task.output
            if isinstance(plan_data, dict):
                plan = ExecutionPlan(**plan_data)
        except Exception:
            pass

    # Get approval info
    approval_status: str | None = None
    approval_expires_at: str | None = None
    if approval:
        approval_status = approval.status
        approval_expires_at = approval.expires_at
        plan_fingerprint = approval.plan_fingerprint

    # Step results (not persisted in current architecture, return empty)
    step_results: list[ExecutionStepResult] = []

    return ExecutionStatusResponse(
        execution_id=execution_id,
        company_id=company_id,
        objective_id=matching_run.objective_id,
        objective_task_id=plan_task.objective_task_id if plan_task else None,
        agent_type=matching_run.agent_type,
        requested_by=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # Not stored in AgentRun
        trace_id=matching_run.trace_id or "",
        status=status,
        created_at=matching_run.created_at.isoformat(),
        started_at=started_at,
        completed_at=completed_at,
        failure_reason=failure_reason,
        cancel_reason=cancel_reason,
        plan=plan,
        plan_fingerprint=plan_fingerprint,
        approval_status=approval_status,
        approval_expires_at=approval_expires_at,
        step_results=step_results,
        metrics=metrics,
    )
