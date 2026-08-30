"""Deterministic Evidence capture from completed ObjectiveTask results. No LLM."""

from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import Evidence
from app.models.objective_task import ObjectiveTask

SOURCE_TYPE_OBJECTIVE_TASK_RESULT = "objective_task_result"
EVIDENCE_TYPE_FOUNDER_TASK_RESULT = "founder_task_result"


def build_objective_task_evidence_content(
    *,
    result_summary: str,
    result_metrics: dict[str, float] | None = None,
    result_notes: str | None = None,
) -> str:
    """Preserve the founder's original result without summarization or inference."""
    payload: dict[str, object] = {"result_summary": result_summary}
    if result_metrics is not None:
        payload["result_metrics"] = result_metrics
    if result_notes is not None:
        payload["result_notes"] = result_notes
    return json.dumps(payload, ensure_ascii=False)


def parse_objective_task_evidence_content(content: str) -> dict[str, object]:
    return json.loads(content)


async def get_evidence_for_company(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    evidence_id: uuid.UUID,
) -> Evidence | None:
    evidence = await db.get(Evidence, evidence_id)
    if evidence is None or evidence.company_id != company_id:
        return None
    return evidence


async def get_evidence_for_objective_task(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    task_id: uuid.UUID,
) -> Evidence | None:
    result = await db.execute(
        select(Evidence).where(
            Evidence.company_id == company_id,
            Evidence.source_type == SOURCE_TYPE_OBJECTIVE_TASK_RESULT,
            Evidence.source_reference == str(task_id),
        )
    )
    return result.scalar_one_or_none()


async def create_evidence_from_objective_task(
    db: AsyncSession,
    *,
    task: ObjectiveTask,
) -> Evidence:
    """Create one Evidence row per completed ObjectiveTask result."""
    existing = await get_evidence_for_objective_task(
        db,
        company_id=task.company_id,
        task_id=task.id,
    )
    if existing is not None:
        return existing

    evidence = Evidence(
        company_id=task.company_id,
        type=EVIDENCE_TYPE_FOUNDER_TASK_RESULT,
        title=task.title,
        content=build_objective_task_evidence_content(
            result_summary=task.result_summary or "",
            result_metrics=task.result_metrics,
            result_notes=task.result_notes,
        ),
        source_type=SOURCE_TYPE_OBJECTIVE_TASK_RESULT,
        source_reference=str(task.id),
        observed_at=task.completed_at,
    )
    db.add(evidence)
    await db.flush()
    return evidence
