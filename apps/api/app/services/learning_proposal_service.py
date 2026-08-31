"""Learning proposal extraction from Evidence. LLM proposes; founder approves later."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from typing import TypeVar

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import Evidence
from app.models.learning import Learning
from app.models.objective import Objective
from app.models.objective_task import ObjectiveTask
from app.schemas.learning import (
    LearningExtractionPayload,
    LearningProposalPublic,
    LearningProposalResponse,
)
from app.services.evidence_service import SOURCE_TYPE_OBJECTIVE_TASK_RESULT
from app.services.learning_proposal_prompt import build_learning_extraction_request
from app.services.llm import (
    LLMProvider,
    ProviderAuthError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnexpectedError,
    get_llm_provider,
)

T = TypeVar("T", bound=LLMProvider)

STATUS_PROPOSED = "proposed"
STATUS_ACTIVE = "active"
STATUS_REJECTED = "rejected"
STATUS_SUPERSEDED = "superseded"

CONFIDENCE_TO_FLOAT: dict[str, float] = {
    "low": 0.33,
    "medium": 0.66,
    "high": 0.9,
}


class LearningProposalError(Exception):
    def __init__(self, detail: str, status_code: int = 500) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _map_provider_error(exc: ProviderError) -> LearningProposalError:
    if isinstance(exc, ProviderAuthError):
        return LearningProposalError("LLM provider is not configured", 502)
    if isinstance(exc, ProviderTimeoutError):
        return LearningProposalError("LLM request timed out", 504)
    if isinstance(exc, ProviderRateLimitError):
        return LearningProposalError("LLM rate limit exceeded", 429)
    if isinstance(exc, ProviderUnavailableError):
        return LearningProposalError("LLM provider unavailable", 502)
    if isinstance(exc, ProviderInvalidResponseError):
        return LearningProposalError("LLM returned an invalid response", 502)
    if isinstance(exc, ProviderUnexpectedError):
        return LearningProposalError("LLM provider error", 502)
    return LearningProposalError("LLM provider error", 502)


def parse_extraction_payload(text: str) -> LearningExtractionPayload:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```").strip()
        fence = stripped.rfind("```")
        if fence != -1:
            stripped = stripped[:fence].strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LearningProposalError("LLM returned an invalid response", 502) from exc
    if not isinstance(payload, dict):
        raise LearningProposalError("LLM returned an invalid response", 502)
    try:
        return LearningExtractionPayload.model_validate(payload)
    except ValidationError as exc:
        raise LearningProposalError("LLM returned an invalid response", 502) from exc


def ground_source_evidence_ids(
    proposed_ids: list[str],
    allowed_evidence_id: uuid.UUID,
) -> list[uuid.UUID]:
    allowed = {str(allowed_evidence_id)}
    grounded: list[uuid.UUID] = []
    for raw_id in proposed_ids:
        if raw_id in allowed:
            grounded.append(allowed_evidence_id)
            break
    return grounded


def _learning_to_public(
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


async def get_proposed_learning_for_evidence(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    evidence_id: uuid.UUID,
) -> Learning | None:
    result = await db.execute(
        select(Learning).where(
            Learning.company_id == company_id,
            Learning.evidence_id == evidence_id,
            Learning.status == STATUS_PROPOSED,
        )
    )
    return result.scalar_one_or_none()


async def _load_evidence_context(
    db: AsyncSession,
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


async def propose_learning_from_evidence(
    db: AsyncSession,
    *,
    evidence: Evidence,
    provider_factory: Callable[[], T] | None = None,
) -> LearningProposalResponse:
    existing = await get_proposed_learning_for_evidence(
        db,
        company_id=evidence.company_id,
        evidence_id=evidence.id,
    )
    if existing is not None:
        source_ids = [evidence.id] if existing.evidence_id is not None else []
        return LearningProposalResponse(
            decision="learning",
            proposal=_learning_to_public(existing, source_evidence_ids=source_ids),
            reason=existing.evidence_summary,
        )

    objective_task, objective = await _load_evidence_context(db, evidence)
    provider = (provider_factory or get_llm_provider)()
    request = build_learning_extraction_request(
        evidence=evidence,
        objective_task=objective_task,
        objective=objective,
    )
    try:
        result = await provider.complete(request)
    except ProviderError as exc:
        raise _map_provider_error(exc) from exc

    parsed = parse_extraction_payload(result.text)
    if parsed.decision == "no_learning":
        reason = parsed.reason or (
            parsed.learning.reason if parsed.learning is not None else None
        )
        return LearningProposalResponse(decision="no_learning", reason=reason)

    if parsed.learning is None:
        return LearningProposalResponse(decision="no_learning")

    grounded_ids = ground_source_evidence_ids(
        parsed.source_evidence_ids,
        evidence.id,
    )
    if not grounded_ids:
        return LearningProposalResponse(
            decision="no_learning",
            reason="No valid Evidence source remained after grounding.",
        )

    confidence_label = parsed.learning.confidence
    if not grounded_ids:
        confidence_label = "low"

    learning = Learning(
        company_id=evidence.company_id,
        objective_id=objective.id if objective is not None else None,
        evidence_id=evidence.id,
        statement=parsed.learning.content.strip(),
        evidence_summary=parsed.learning.reason.strip(),
        confidence=CONFIDENCE_TO_FLOAT.get(confidence_label, 0.33),
        status=STATUS_PROPOSED,
    )
    db.add(learning)
    await db.commit()
    await db.refresh(learning)
    return LearningProposalResponse(
        decision="learning",
        proposal=_learning_to_public(learning, source_evidence_ids=grounded_ids),
        reason=learning.evidence_summary,
    )
