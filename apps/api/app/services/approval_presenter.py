"""Build public approval responses with linked recommendation or learning context."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_task import AgentTask
from app.models.approval import Approval
from app.models.learning import Learning
from app.schemas.approval import ApprovalPublic
from app.schemas.learning import LearningProposalPublic
from app.services.approval_service import ApprovalError, parse_stored_recommendation


def _learning_to_proposal_public(
    learning: Learning,
    *,
    source_evidence_ids: list[uuid.UUID],
) -> LearningProposalPublic:
    return LearningProposalPublic(
        id=learning.id,
        company_id=learning.company_id,
        evidence_id=learning.evidence_id,
        objective_id=learning.objective_id,
        statement=learning.statement,
        evidence_summary=learning.evidence_summary,
        confidence=learning.confidence,
        status=learning.status,
        source_evidence_ids=source_evidence_ids,
    )


async def approvals_to_public(
    db: AsyncSession,
    approvals: list[Approval],
) -> list[ApprovalPublic]:
    if not approvals:
        return []

    agent_task_ids = {approval.agent_task_id for approval in approvals if approval.agent_task_id}
    learning_ids = {approval.learning_id for approval in approvals if approval.learning_id}

    agent_tasks: dict[uuid.UUID, AgentTask] = {}
    if agent_task_ids:
        result = await db.execute(
            select(AgentTask).where(AgentTask.id.in_(agent_task_ids))
        )
        agent_tasks = {task.id: task for task in result.scalars().all()}

    learnings: dict[uuid.UUID, Learning] = {}
    if learning_ids:
        result = await db.execute(select(Learning).where(Learning.id.in_(learning_ids)))
        learnings = {learning.id: learning for learning in result.scalars().all()}

    return [
        _approval_to_public_from_maps(approval, agent_tasks=agent_tasks, learnings=learnings)
        for approval in approvals
    ]


async def approval_to_public(
    db: AsyncSession,
    approval: Approval,
) -> ApprovalPublic:
    agent_tasks: dict[uuid.UUID, AgentTask] = {}
    learnings: dict[uuid.UUID, Learning] = {}

    if approval.agent_task_id is not None:
        agent_task = await db.get(AgentTask, approval.agent_task_id)
        if agent_task is not None:
            agent_tasks[agent_task.id] = agent_task

    if approval.learning_id is not None:
        learning = await db.get(Learning, approval.learning_id)
        if learning is not None:
            learnings[learning.id] = learning

    return _approval_to_public_from_maps(
        approval,
        agent_tasks=agent_tasks,
        learnings=learnings,
    )


def _approval_to_public_from_maps(
    approval: Approval,
    *,
    agent_tasks: dict[uuid.UUID, AgentTask],
    learnings: dict[uuid.UUID, Learning],
) -> ApprovalPublic:
    objective_task_id: uuid.UUID | None = None
    recommendation = None
    learning_proposal = None

    if approval.agent_task_id is not None:
        agent_task = agent_tasks.get(approval.agent_task_id)
        if agent_task is not None:
            objective_task_id = agent_task.objective_task_id
            if isinstance(agent_task.output, dict):
                try:
                    recommendation = parse_stored_recommendation(agent_task.output)
                except ApprovalError:
                    recommendation = None

    if approval.learning_id is not None:
        learning = learnings.get(approval.learning_id)
        if learning is not None:
            source_ids = [learning.evidence_id] if learning.evidence_id is not None else []
            learning_proposal = _learning_to_proposal_public(
                learning,
                source_evidence_ids=source_ids,
            )

    return ApprovalPublic(
        id=approval.id,
        company_id=approval.company_id,
        agent_task_id=approval.agent_task_id,
        learning_id=approval.learning_id,
        action_type=approval.action_type,
        description=approval.description,
        risk_level=approval.risk_level,
        status=approval.status,
        requested_at=approval.requested_at,
        resolved_at=approval.resolved_at,
        resolved_by=approval.resolved_by,
        objective_task_id=objective_task_id,
        recommendation=recommendation,
        learning_proposal=learning_proposal,
    )
