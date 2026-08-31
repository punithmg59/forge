"""Tool execution audit via existing AgentRun / AgentTask tables."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.models.agent_task import AgentTask
from app.schemas.tool import ToolErrorCode, ToolExecutionContext

TOOL_RUNNER_AGENT_TYPE = "tool_runner"
TOOL_EXECUTION_TASK_TYPE = "tool_execution"


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


async def persist_tool_execution_audit(
    db: AsyncSession,
    *,
    context: ToolExecutionContext,
    tool_name: str,
    tool_version: str,
    success: bool,
    duration_ms: float,
    error_code: ToolErrorCode | None = None,
    agent_run_id: uuid.UUID | None = None,
) -> AgentTask:
    """Record tool execution metadata without storing secrets or large payloads."""
    run = None
    if agent_run_id is not None:
        run = await db.get(AgentRun, agent_run_id)
    if run is None:
        run = AgentRun(
            company_id=context.company_id,
            agent_type=context.agent_type or TOOL_RUNNER_AGENT_TYPE,
            status="completed",
            started_at=_utcnow_iso(),
            completed_at=_utcnow_iso(),
            trace_id=context.trace_id,
        )
        db.add(run)
        await db.flush()

    task = AgentTask(
        company_id=context.company_id,
        agent_run_id=run.id,
        agent_type=context.agent_type or TOOL_RUNNER_AGENT_TYPE,
        task_type=TOOL_EXECUTION_TASK_TYPE,
        status="completed" if success else "failed",
        input={
            "tool_name": tool_name,
            "tool_version": tool_version,
            "trace_id": context.trace_id,
            "user_id": str(context.user_id),
        },
        output={
            "success": success,
            "error_code": error_code.value if error_code else None,
            "duration_ms": round(duration_ms, 2),
        },
        completed_at=_utcnow_iso(),
    )
    db.add(task)
    await db.flush()
    return task
