"""Approval workflow for Head Agent recommendations and Learning proposals. No LLM calls."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.models.agent_task import AgentTask
from app.models.approval import Approval
from app.models.evidence import Evidence
from app.models.learning import Learning
from app.models.objective import Objective
from app.models.objective_task import ObjectiveTask
from app.models.user import User
from app.schemas.head_agent import HeadAgentRecommendation, ProposedActionType
from app.services.head_agent import HEAD_AGENT_TASK_TYPE, HEAD_AGENT_TYPE
from app.services.learning_proposal_service import (
    STATUS_ACTIVE,
    STATUS_PROPOSED,
)
from app.services.learning_proposal_service import (
    STATUS_REJECTED as LEARNING_STATUS_REJECTED,
)

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"

TERMINAL_STATUSES = frozenset({STATUS_APPROVED, STATUS_REJECTED})

ALLOWED_ACTION_TYPES: frozenset[ProposedActionType] = frozenset(
    {"task", "objective_change", "none"}
)

ACTION_TYPE_LEARNING = "learning"
ACTION_TYPE_EXECUTION = "execution"

CONFIDENCE_RISK: dict[str, str] = {
    "low": "low",
    "medium": "medium",
    "high": "medium",
}

DEFAULT_TASK_CAPABILITY = "founder"
DEFAULT_TASK_STATUS = "pending"
DEFAULT_TASK_PRIORITY = "medium"


class ApprovalError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def parse_stored_recommendation(output: object) -> HeadAgentRecommendation:
    if not isinstance(output, dict):
        raise ApprovalError("Recommendation is invalid", 400)
    try:
        return HeadAgentRecommendation.model_validate(output)
    except ValidationError as exc:
        raise ApprovalError("Recommendation is invalid", 400) from exc


def validate_action_type(action_type: str) -> ProposedActionType:
    if action_type not in ALLOWED_ACTION_TYPES:
        raise ApprovalError(f"Unsupported action type: {action_type}", 400)
    return action_type  # type: ignore[return-value]


async def get_learning_for_company(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    learning_id: uuid.UUID,
) -> Learning | None:
    learning = await db.get(Learning, learning_id)
    if learning is None or learning.company_id != company_id:
        return None
    return learning


async def _validate_learning_evidence_company(
    db: AsyncSession,
    *,
    learning: Learning,
    company_id: uuid.UUID,
) -> None:
    if learning.evidence_id is None:
        return
    evidence = await db.get(Evidence, learning.evidence_id)
    if evidence is None or evidence.company_id != company_id:
        raise ApprovalError("Evidence not found", 404)


def _learning_confidence_to_risk(confidence: float | None) -> str:
    if confidence is None:
        return "low"
    if confidence >= 0.66:
        return "medium"
    return "low"


async def create_learning_approval(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    learning_id: uuid.UUID,
) -> Approval:
    learning = await get_learning_for_company(
        db,
        company_id=company_id,
        learning_id=learning_id,
    )
    if learning is None:
        raise ApprovalError("Learning not found", 404)
    if learning.status != STATUS_PROPOSED:
        raise ApprovalError("Only proposed learnings can enter approval", 400)
    await _validate_learning_evidence_company(db, learning=learning, company_id=company_id)

    existing = await db.execute(
        select(Approval).where(
            Approval.company_id == company_id,
            Approval.learning_id == learning_id,
            Approval.status == STATUS_PENDING,
        )
    )
    pending = existing.scalar_one_or_none()
    if pending is not None:
        return pending

    approval = Approval(
        company_id=company_id,
        learning_id=learning_id,
        action_type=ACTION_TYPE_LEARNING,
        description=learning.statement,
        risk_level=_learning_confidence_to_risk(learning.confidence),
        status=STATUS_PENDING,
        requested_at=_utcnow_iso(),
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    return approval


async def _activate_learning_on_approve(
    db: AsyncSession,
    *,
    approval: Approval,
) -> Learning:
    if approval.learning_id is None:
        raise ApprovalError("Approval has no linked learning", 400)

    learning = await get_learning_for_company(
        db,
        company_id=approval.company_id,
        learning_id=approval.learning_id,
    )
    if learning is None:
        raise ApprovalError("Learning not found", 404)
    if learning.status == STATUS_ACTIVE:
        return learning
    if learning.status != STATUS_PROPOSED:
        raise ApprovalError("Learning is not in a proposed state", 400)
    await _validate_learning_evidence_company(
        db,
        learning=learning,
        company_id=approval.company_id,
    )
    learning.status = STATUS_ACTIVE
    await db.flush()
    return learning


async def _reject_learning_on_reject(
    db: AsyncSession,
    *,
    approval: Approval,
) -> Learning | None:
    if approval.learning_id is None:
        return None

    learning = await get_learning_for_company(
        db,
        company_id=approval.company_id,
        learning_id=approval.learning_id,
    )
    if learning is None:
        raise ApprovalError("Learning not found", 404)
    if learning.status == LEARNING_STATUS_REJECTED:
        return learning
    if learning.status == STATUS_ACTIVE:
        raise ApprovalError("Active learning cannot be rejected through this approval", 400)
    if learning.status != STATUS_PROPOSED:
        raise ApprovalError("Learning is not in a proposed state", 400)
    learning.status = LEARNING_STATUS_REJECTED
    await db.flush()
    return learning


async def get_agent_task_for_company(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    agent_task_id: uuid.UUID,
) -> AgentTask | None:
    task = await db.get(AgentTask, agent_task_id)
    if task is None or task.company_id != company_id:
        return None
    return task


async def get_approval(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    approval_id: uuid.UUID,
) -> Approval | None:
    approval = await db.get(Approval, approval_id)
    if approval is None or approval.company_id != company_id:
        return None
    return approval


async def list_approvals(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
) -> list[Approval]:
    result = await db.execute(
        select(Approval)
        .where(Approval.company_id == company_id)
        .order_by(Approval.requested_at.desc())
    )
    return list(result.scalars().all())


async def _load_agent_task_context(
    db: AsyncSession,
    agent_task: AgentTask,
) -> tuple[HeadAgentRecommendation, AgentRun | None]:
    if agent_task.agent_type != HEAD_AGENT_TYPE:
        raise ApprovalError("Recommendation did not come from the Head Agent", 400)
    if agent_task.task_type != HEAD_AGENT_TASK_TYPE:
        raise ApprovalError("Agent task is not a Head Agent recommendation", 400)
    recommendation = parse_stored_recommendation(agent_task.output)
    validate_action_type(recommendation.proposed_action.type)
    agent_run = None
    if agent_task.agent_run_id is not None:
        agent_run = await db.get(AgentRun, agent_task.agent_run_id)
    return recommendation, agent_run


async def create_approval(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    agent_task_id: uuid.UUID,
) -> Approval:
    agent_task = await get_agent_task_for_company(
        db,
        company_id=company_id,
        agent_task_id=agent_task_id,
    )
    if agent_task is None:
        raise ApprovalError("Recommendation not found", 404)

    recommendation, _agent_run = await _load_agent_task_context(db, agent_task)
    action_type = recommendation.proposed_action.type

    existing = await db.execute(
        select(Approval).where(
            Approval.company_id == company_id,
            Approval.agent_task_id == agent_task_id,
            Approval.status == STATUS_PENDING,
        )
    )
    pending = existing.scalar_one_or_none()
    if pending is not None:
        return pending

    approval = Approval(
        company_id=company_id,
        agent_task_id=agent_task_id,
        action_type=action_type,
        description=recommendation.title,
        risk_level=CONFIDENCE_RISK.get(recommendation.confidence, "low"),
        status=STATUS_PENDING,
        requested_at=_utcnow_iso(),
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    return approval


def validate_transition(current_status: str, next_status: str) -> None:
    if current_status == next_status:
        return
    if current_status in TERMINAL_STATUSES:
        raise ApprovalError(
            f"Cannot transition approval from '{current_status}' to '{next_status}'",
            400,
        )
    if current_status == STATUS_PENDING and next_status in TERMINAL_STATUSES:
        return
    raise ApprovalError(
        f"Cannot transition approval from '{current_status}' to '{next_status}'",
        400,
    )


async def _get_or_create_objective_task(
    db: AsyncSession,
    *,
    agent_task: AgentTask,
    agent_run: AgentRun | None,
    recommendation: HeadAgentRecommendation,
    company_id: uuid.UUID,
) -> ObjectiveTask | None:
    if agent_task.objective_task_id is not None:
        existing = await db.get(ObjectiveTask, agent_task.objective_task_id)
        if existing is not None and existing.company_id == company_id:
            return existing

    if recommendation.proposed_action.type != "task":
        return None

    if agent_run is None or agent_run.objective_id is None:
        raise ApprovalError("Recommendation objective is missing", 400)

    objective = await db.get(Objective, agent_run.objective_id)
    if objective is None or objective.company_id != company_id:
        raise ApprovalError("Objective not found", 404)

    title = recommendation.proposed_action.title.strip() or recommendation.title.strip()
    if not title:
        raise ApprovalError("Task title is required", 400)

    description = (
        recommendation.proposed_action.description.strip()
        or recommendation.recommendation.strip()
        or None
    )

    objective_task = ObjectiveTask(
        company_id=company_id,
        objective_id=objective.id,
        title=title,
        description=description,
        capability=DEFAULT_TASK_CAPABILITY,
        status=DEFAULT_TASK_STATUS,
        priority=DEFAULT_TASK_PRIORITY,
        requires_approval=False,
    )
    db.add(objective_task)
    await db.flush()
    agent_task.objective_task_id = objective_task.id
    return objective_task


async def approve_approval(
    db: AsyncSession,
    *,
    approval: Approval,
    user: User,
) -> tuple[Approval, ObjectiveTask | None]:
    validate_transition(approval.status, STATUS_APPROVED)

    if approval.status == STATUS_APPROVED:
        objective_task = None
        if approval.action_type == ACTION_TYPE_LEARNING:
            return approval, None
        if approval.agent_task_id is not None:
            agent_task = await db.get(AgentTask, approval.agent_task_id)
            if agent_task is not None and agent_task.objective_task_id is not None:
                objective_task = await db.get(ObjectiveTask, agent_task.objective_task_id)
        return approval, objective_task

    if approval.action_type == ACTION_TYPE_LEARNING:
        await _activate_learning_on_approve(db, approval=approval)
        approval.status = STATUS_APPROVED
        approval.resolved_at = _utcnow_iso()
        approval.resolved_by = user.id
        await db.commit()
        await db.refresh(approval)
        return approval, None

    if approval.action_type == ACTION_TYPE_EXECUTION:
        if approval.agent_task_id is None:
            raise ApprovalError("Execution plan not found", 404)
        agent_task = await get_agent_task_for_company(
            db,
            company_id=approval.company_id,
            agent_task_id=approval.agent_task_id,
        )
        if agent_task is None:
            raise ApprovalError("Execution plan not found", 404)
        approval.status = STATUS_APPROVED
        approval.resolved_at = _utcnow_iso()
        approval.resolved_by = user.id
        await db.commit()
        await db.refresh(approval)
        return approval, None

    if approval.agent_task_id is None:
        raise ApprovalError("Approval has no linked recommendation", 400)

    agent_task = await get_agent_task_for_company(
        db,
        company_id=approval.company_id,
        agent_task_id=approval.agent_task_id,
    )
    if agent_task is None:
        raise ApprovalError("Recommendation not found", 404)

    recommendation, agent_run = await _load_agent_task_context(db, agent_task)
    objective_task = await _get_or_create_objective_task(
        db,
        agent_task=agent_task,
        agent_run=agent_run,
        recommendation=recommendation,
        company_id=approval.company_id,
    )

    approval.status = STATUS_APPROVED
    approval.resolved_at = _utcnow_iso()
    approval.resolved_by = user.id
    await db.commit()
    await db.refresh(approval)
    return approval, objective_task


async def reject_approval(
    db: AsyncSession,
    *,
    approval: Approval,
    user: User,
) -> Approval:
    validate_transition(approval.status, STATUS_REJECTED)

    if approval.status == STATUS_REJECTED:
        return approval

    if approval.action_type == ACTION_TYPE_LEARNING:
        await _reject_learning_on_reject(db, approval=approval)

    approval.status = STATUS_REJECTED
    approval.resolved_at = _utcnow_iso()
    approval.resolved_by = user.id
    await db.commit()
    await db.refresh(approval)
    return approval
