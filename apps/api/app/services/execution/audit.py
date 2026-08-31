"""Execution audit contract using existing AgentRun / AgentTask tables."""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.agent_run import AgentRun
from app.models.agent_task import AgentTask
from app.schemas.execution import ExecutionIdentity, ExecutionPlan, ExecutionRequest

EXECUTION_RUNNER_AGENT_TYPE = "execution_runner"
EXECUTION_PLAN_TASK_TYPE = "execution_plan"
EXECUTION_STATUS_TASK_TYPE = "execution_status"


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def new_execution_run(
    *,
    identity: ExecutionIdentity,
    status: str = "planned",
) -> AgentRun:
    """Create an AgentRun for an execution (not yet persisted)."""
    return AgentRun(
        company_id=identity.company_id,
        agent_type=identity.agent_type or EXECUTION_RUNNER_AGENT_TYPE,
        objective_id=identity.objective_id,
        task_id=identity.objective_task_id,
        status=status,
        started_at=_utcnow_iso(),
        trace_id=identity.trace_id,
    )


def new_execution_plan_task(
    *,
    identity: ExecutionIdentity,
    agent_run: AgentRun,
    plan: ExecutionPlan,
) -> AgentTask:
    """Persist execution plan metadata without secrets or full tool payloads."""
    return AgentTask(
        company_id=identity.company_id,
        agent_run_id=agent_run.id,
        objective_task_id=identity.objective_task_id,
        agent_type=identity.agent_type or EXECUTION_RUNNER_AGENT_TYPE,
        task_type=EXECUTION_PLAN_TASK_TYPE,
        status="completed",
        input={
            "execution_id": str(identity.execution_id),
            "trace_id": identity.trace_id,
            "goal": plan.goal,
            "step_count": len(plan.steps),
            "risk_level": plan.risk_level,
        },
        output=plan.model_dump(mode="json"),
        completed_at=_utcnow_iso(),
    )


def new_execution_status_task(
    *,
    identity: ExecutionIdentity,
    agent_run: AgentRun,
    request: ExecutionRequest,
) -> AgentTask:
    return AgentTask(
        company_id=identity.company_id,
        agent_run_id=agent_run.id,
        objective_task_id=identity.objective_task_id,
        agent_type=identity.agent_type or EXECUTION_RUNNER_AGENT_TYPE,
        task_type=EXECUTION_STATUS_TASK_TYPE,
        status="completed",
        input={
            "execution_id": str(identity.execution_id),
            "trace_id": identity.trace_id,
            "status": request.status,
        },
        output={
            "status": request.status,
            "failure_reason": request.failure_reason,
            "cancel_reason": request.cancel_reason,
        },
        completed_at=_utcnow_iso(),
    )
