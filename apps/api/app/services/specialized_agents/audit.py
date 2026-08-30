"""Audit contract for specialized agents using existing AgentRun / AgentTask tables."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.models.agent_run import AgentRun
from app.models.agent_task import AgentTask
from app.schemas.specialized_agent import SpecializedAgentRecommendation
from app.schemas.specialized_agent_types import AgentDomain, SpecializedAgentType

SPECIALIZED_AGENT_TASK_TYPE = "recommendation"


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def new_specialized_agent_run(
    *,
    company_id: uuid.UUID,
    agent_type: SpecializedAgentType,
    objective_id: uuid.UUID | None = None,
    trace_id: str | None = None,
) -> AgentRun:
    """Create an AgentRun row for specialist execution (not yet persisted)."""
    return AgentRun(
        company_id=company_id,
        agent_type=agent_type.value,
        objective_id=objective_id,
        status="running",
        started_at=_utcnow_iso(),
        trace_id=trace_id or str(uuid.uuid4()),
    )


def new_specialized_agent_task(
    *,
    company_id: uuid.UUID,
    agent_run: AgentRun,
    agent_type: SpecializedAgentType,
    domain: AgentDomain,
    question: str,
    recommendation: SpecializedAgentRecommendation,
) -> AgentTask:
    """Create an AgentTask row for a specialist proposal (not yet persisted)."""
    return AgentTask(
        company_id=company_id,
        agent_run_id=agent_run.id,
        agent_type=agent_type.value,
        task_type=SPECIALIZED_AGENT_TASK_TYPE,
        status="completed",
        input={
            "question": question,
            "domain": domain.value,
            "objective_id": str(agent_run.objective_id) if agent_run.objective_id else None,
        },
        output=recommendation.model_dump(mode="json"),
        completed_at=_utcnow_iso(),
    )
