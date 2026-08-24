"""Build public approval responses with linked recommendation context."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_task import AgentTask
from app.models.approval import Approval
from app.schemas.approval import ApprovalPublic
from app.services.approval_service import parse_stored_recommendation


async def approval_to_public(
    db: AsyncSession,
    approval: Approval,
) -> ApprovalPublic:
    objective_task_id: uuid.UUID | None = None
    recommendation = None
    if approval.agent_task_id is not None:
        agent_task = await db.get(AgentTask, approval.agent_task_id)
        if agent_task is not None:
            objective_task_id = agent_task.objective_task_id
            if isinstance(agent_task.output, dict):
                recommendation = parse_stored_recommendation(agent_task.output)
    return ApprovalPublic(
        id=approval.id,
        company_id=approval.company_id,
        agent_task_id=approval.agent_task_id,
        action_type=approval.action_type,
        description=approval.description,
        risk_level=approval.risk_level,
        status=approval.status,
        requested_at=approval.requested_at,
        resolved_at=approval.resolved_at,
        resolved_by=approval.resolved_by,
        objective_task_id=objective_task_id,
        recommendation=recommendation,
    )
