"""Learning visibility and correction. No LLM calls."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval
from app.models.evidence import Evidence
from app.models.learning import Learning
from app.models.objective import Objective
from app.models.objective_task import ObjectiveTask
from app.models.user import User
from app.schemas.learning import LearningProvenancePublic, LearningPublic
from app.services.evidence_service import SOURCE_TYPE_OBJECTIVE_TASK_RESULT
from app.services.learning_proposal_service import (
    STATUS_ACTIVE,
    STATUS_PROPOSED,
    STATUS_SUPERSEDED,
)

MAX_CORRECTION_REASON_LENGTH = 500


class LearningError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


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


async def list_learnings(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
) -> list[Learning]:
    result = await db.execute(
        select(Learning)
        .where(Learning.company_id == company_id)
        .order_by(Learning.created_at.desc(), Learning.id.desc())
    )
    return list(result.scalars().all())


async def _load_evidence_chain(
    db: AsyncSession,
    *,
    evidence: Evidence,
) -> tuple[ObjectiveTask | None, Objective | None]:
    if evidence.source_type != SOURCE_TYPE_OBJECTIVE_TASK_RESULT:
        return None, None
    if not evidence.source_reference:
        return None, None
    try:
        task_id = uuid.UUID(evidence.source_reference)
    except ValueError:
        return None, None
    task = await db.get(ObjectiveTask, task_id)
    if task is None or task.company_id != evidence.company_id:
        return None, None
    objective = await db.get(Objective, task.objective_id)
    if objective is None or objective.company_id != evidence.company_id:
        return task, None
    return task, objective


async def build_learning_provenance(
    db: AsyncSession,
    *,
    learning: Learning,
) -> LearningProvenancePublic | None:
    if learning.evidence_id is None:
        objective = None
        if learning.objective_id is not None:
            objective = await db.get(Objective, learning.objective_id)
        return LearningProvenancePublic(
            objective_id=learning.objective_id,
            objective_title=objective.title if objective is not None else None,
        )

    evidence = await db.get(Evidence, learning.evidence_id)
    if evidence is None or evidence.company_id != learning.company_id:
        return None

    task, objective_from_task = await _load_evidence_chain(db, evidence=evidence)
    objective = objective_from_task
    if objective is None and learning.objective_id is not None:
        objective = await db.get(Objective, learning.objective_id)

    return LearningProvenancePublic(
        evidence_id=evidence.id,
        evidence_title=evidence.title,
        evidence_content=evidence.content,
        evidence_observed_at=evidence.observed_at,
        objective_task_id=task.id if task is not None else None,
        objective_task_title=task.title if task is not None else None,
        objective_id=objective.id if objective is not None else learning.objective_id,
        objective_title=objective.title if objective is not None else None,
    )


async def _approval_status_for_learning(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    learning_id: uuid.UUID,
) -> str | None:
    result = await db.execute(
        select(Approval)
        .where(
            Approval.company_id == company_id,
            Approval.learning_id == learning_id,
        )
        .order_by(Approval.requested_at.desc())
        .limit(1)
    )
    approval = result.scalar_one_or_none()
    return approval.status if approval is not None else None


async def _approval_status_for_learning_ids(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    learning_ids: list[uuid.UUID],
) -> dict[uuid.UUID, str]:
    if not learning_ids:
        return {}
    result = await db.execute(
        select(Approval)
        .where(
            Approval.company_id == company_id,
            Approval.learning_id.in_(learning_ids),
        )
        .order_by(Approval.requested_at.desc(), Approval.id.desc())
    )
    statuses: dict[uuid.UUID, str] = {}
    for approval in result.scalars().all():
        if approval.learning_id is not None and approval.learning_id not in statuses:
            statuses[approval.learning_id] = approval.status
    return statuses


def _provenance_from_maps(
    learning: Learning,
    *,
    evidences: dict[uuid.UUID, Evidence],
    tasks: dict[uuid.UUID, ObjectiveTask],
    objectives: dict[uuid.UUID, Objective],
) -> LearningProvenancePublic | None:
    if learning.evidence_id is None:
        objective = objectives.get(learning.objective_id) if learning.objective_id else None
        return LearningProvenancePublic(
            objective_id=learning.objective_id,
            objective_title=objective.title if objective is not None else None,
        )

    evidence = evidences.get(learning.evidence_id)
    if evidence is None or evidence.company_id != learning.company_id:
        return None

    task: ObjectiveTask | None = None
    objective: Objective | None = None
    if evidence.source_type == SOURCE_TYPE_OBJECTIVE_TASK_RESULT and evidence.source_reference:
        try:
            task_id = uuid.UUID(evidence.source_reference)
            task = tasks.get(task_id)
            if task is not None:
                objective = objectives.get(task.objective_id)
        except ValueError:
            pass

    if objective is None and learning.objective_id is not None:
        objective = objectives.get(learning.objective_id)

    return LearningProvenancePublic(
        evidence_id=evidence.id,
        evidence_title=evidence.title,
        evidence_content=evidence.content,
        evidence_observed_at=evidence.observed_at,
        objective_task_id=task.id if task is not None else None,
        objective_task_title=task.title if task is not None else None,
        objective_id=objective.id if objective is not None else learning.objective_id,
        objective_title=objective.title if objective is not None else None,
    )


async def learnings_to_public(
    db: AsyncSession,
    learnings: list[Learning],
) -> list[LearningPublic]:
    if not learnings:
        return []

    company_id = learnings[0].company_id
    evidence_ids = {learning.evidence_id for learning in learnings if learning.evidence_id}
    objective_ids = {learning.objective_id for learning in learnings if learning.objective_id}
    proposed_ids = [learning.id for learning in learnings if learning.status == STATUS_PROPOSED]

    evidences: dict[uuid.UUID, Evidence] = {}
    if evidence_ids:
        result = await db.execute(select(Evidence).where(Evidence.id.in_(evidence_ids)))
        evidences = {evidence.id: evidence for evidence in result.scalars().all()}

    task_ids: set[uuid.UUID] = set()
    for evidence in evidences.values():
        if evidence.source_type != SOURCE_TYPE_OBJECTIVE_TASK_RESULT:
            continue
        if not evidence.source_reference:
            continue
        try:
            task_ids.add(uuid.UUID(evidence.source_reference))
        except ValueError:
            continue

    tasks: dict[uuid.UUID, ObjectiveTask] = {}
    if task_ids:
        result = await db.execute(
            select(ObjectiveTask).where(ObjectiveTask.id.in_(task_ids))
        )
        tasks = {task.id: task for task in result.scalars().all()}
        objective_ids |= {task.objective_id for task in tasks.values()}

    objectives: dict[uuid.UUID, Objective] = {}
    if objective_ids:
        result = await db.execute(select(Objective).where(Objective.id.in_(objective_ids)))
        objectives = {objective.id: objective for objective in result.scalars().all()}

    approval_statuses = await _approval_status_for_learning_ids(
        db,
        company_id=company_id,
        learning_ids=proposed_ids,
    )

    return [
        LearningPublic(
            id=learning.id,
            company_id=learning.company_id,
            evidence_id=learning.evidence_id,
            objective_id=learning.objective_id,
            statement=learning.statement,
            evidence_summary=learning.evidence_summary,
            confidence=learning.confidence,
            status=learning.status,
            created_at=learning.created_at,
            updated_at=learning.updated_at,
            corrected_by=learning.corrected_by,
            corrected_at=learning.corrected_at,
            correction_reason=learning.correction_reason,
            provenance=_provenance_from_maps(
                learning,
                evidences=evidences,
                tasks=tasks,
                objectives=objectives,
            ),
            approval_status=approval_statuses.get(learning.id),
        )
        for learning in learnings
    ]


async def learning_to_public(
    db: AsyncSession,
    learning: Learning,
) -> LearningPublic:
    provenance = await build_learning_provenance(db, learning=learning)
    approval_status = None
    if learning.status == STATUS_PROPOSED:
        approval_status = await _approval_status_for_learning(
            db,
            company_id=learning.company_id,
            learning_id=learning.id,
        )
    return LearningPublic(
        id=learning.id,
        company_id=learning.company_id,
        evidence_id=learning.evidence_id,
        objective_id=learning.objective_id,
        statement=learning.statement,
        evidence_summary=learning.evidence_summary,
        confidence=learning.confidence,
        status=learning.status,
        created_at=learning.created_at,
        updated_at=learning.updated_at,
        corrected_by=learning.corrected_by,
        corrected_at=learning.corrected_at,
        correction_reason=learning.correction_reason,
        provenance=provenance,
        approval_status=approval_status,
    )


async def correct_learning(
    db: AsyncSession,
    *,
    learning: Learning,
    user: User,
    reason: str,
) -> Learning:
    stripped_reason = reason.strip()
    if not stripped_reason:
        raise LearningError("Correction reason is required", 400)
    if len(stripped_reason) > MAX_CORRECTION_REASON_LENGTH:
        raise LearningError("Correction reason is too long", 400)

    if learning.status == STATUS_SUPERSEDED:
        return learning

    if learning.status != STATUS_ACTIVE:
        raise LearningError("Only active learnings can be corrected", 400)

    learning.status = STATUS_SUPERSEDED
    learning.corrected_by = user.id
    learning.corrected_at = datetime.now(UTC)
    learning.correction_reason = stripped_reason
    await db.commit()
    await db.refresh(learning)
    return learning
