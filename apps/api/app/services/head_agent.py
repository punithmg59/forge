"""Head Agent recommend-only orchestration. Never mutates company state."""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TypeVar

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.models.agent_task import AgentTask
from app.models.company_member import CompanyMember
from app.schemas.brain import CompanyContext, ContextSource
from app.schemas.head_agent import (
    HeadAgentRecommendation,
    HeadAgentRecommendResponse,
    ProposedAction,
    RecommendationConfidence,
)
from app.services.brain_context import BrainContextError, build_company_brain_context
from app.services.head_agent_prompt import (
    DEFAULT_OPERATING_QUESTION,
    build_head_agent_completion_request,
    estimate_head_agent_prompt_chars,
    resolve_founder_question,
)
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

logger = logging.getLogger(__name__)

HEAD_AGENT_TYPE = "head_agent"
HEAD_AGENT_TASK_TYPE = "recommendation"
NO_OBJECTIVE_TITLE = "Active objective required"
NO_OBJECTIVE_RECOMMENDATION = (
    "Forge needs an active objective before it can make an "
    "objective-driven recommendation."
)
NO_OBJECTIVE_RATIONALE = (
    "The Company Brain does not currently contain an active objective. "
    "Create and prioritize an active objective first. "
    "No objective was invented."
)


class HeadAgentError(Exception):
    def __init__(self, detail: str, status_code: int = 500) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _source_key(source: ContextSource) -> tuple[str | None, str | None]:
    return (source.entity_type, source.entity_id)


def ground_recommendation_sources(
    proposed: list[ContextSource],
    context: CompanyContext,
) -> list[ContextSource]:
    """Keep only sources that already exist on the supplied CompanyContext."""
    allowed = {_source_key(source) for source in context.sources if source.entity_id}
    grounded: list[ContextSource] = []
    seen: set[tuple[str | None, str | None]] = set()
    for source in proposed:
        key = _source_key(source)
        if source.entity_id is None or key not in allowed or key in seen:
            continue
        seen.add(key)
        grounded.append(source)
    return grounded


def clamp_confidence_for_grounding(
    confidence: RecommendationConfidence,
    sources: list[ContextSource],
) -> RecommendationConfidence:
    if sources:
        return confidence
    return "low"


def parse_recommendation_payload(text: str) -> HeadAgentRecommendation:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```").strip()
        fence = stripped.rfind("```")
        if fence != -1:
            stripped = stripped[:fence].strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise HeadAgentError("LLM returned an invalid response", 502) from exc
    if not isinstance(payload, dict):
        raise HeadAgentError("LLM returned an invalid response", 502)
    try:
        return HeadAgentRecommendation.model_validate(payload)
    except ValidationError as exc:
        raise HeadAgentError("LLM returned an invalid response", 502) from exc


def no_active_objective_recommendation() -> HeadAgentRecommendation:
    return HeadAgentRecommendation(
        title=NO_OBJECTIVE_TITLE,
        recommendation=NO_OBJECTIVE_RECOMMENDATION,
        rationale=NO_OBJECTIVE_RATIONALE,
        proposed_action=ProposedAction(type="none"),
        sources=[],
        confidence="low",
    )


async def _persist_recommendation_task(
    db: AsyncSession,
    *,
    run: AgentRun,
    company_id: uuid.UUID,
    question: str,
    recommendation: HeadAgentRecommendation,
) -> AgentTask:
    agent_task = AgentTask(
        company_id=company_id,
        agent_run_id=run.id,
        agent_type=HEAD_AGENT_TYPE,
        task_type=HEAD_AGENT_TASK_TYPE,
        status="completed",
        input={
            "question": question,
            "objective_id": str(run.objective_id) if run.objective_id else None,
        },
        output=recommendation.model_dump(mode="json"),
        completed_at=_utcnow_iso(),
    )
    db.add(agent_task)
    await db.flush()
    return agent_task


def _map_provider_error(exc: ProviderError) -> HeadAgentError:
    if isinstance(exc, ProviderAuthError):
        return HeadAgentError("LLM provider is not configured", 502)
    if isinstance(exc, ProviderTimeoutError):
        return HeadAgentError("LLM request timed out", 504)
    if isinstance(exc, ProviderRateLimitError):
        return HeadAgentError("LLM rate limit exceeded", 429)
    if isinstance(exc, ProviderUnavailableError):
        return HeadAgentError("LLM provider unavailable", 502)
    if isinstance(exc, ProviderInvalidResponseError):
        return HeadAgentError("LLM returned an invalid response", 502)
    if isinstance(exc, ProviderUnexpectedError):
        return HeadAgentError("LLM provider error", 502)
    return HeadAgentError("LLM provider error", 502)


def _log_head_agent_perf(
    trace_id: str,
    *,
    retrieval_ms: float,
    prompt_build_ms: float,
    llm_ms: float,
    parsing_ms: float,
    persistence_ms: float,
    total_ms: float,
    prompt_chars: int = 0,
    output_chars: int = 0,
    vector_used: bool = False,
) -> None:
    logger.info(
        "head_agent_perf trace_id=%s retrieval_ms=%.1f prompt_build_ms=%.1f "
        "llm_ms=%.1f parsing_ms=%.1f persistence_ms=%.1f total_ms=%.1f "
        "prompt_chars=%d output_chars=%d vector_used=%s",
        trace_id,
        retrieval_ms,
        prompt_build_ms,
        llm_ms,
        parsing_ms,
        persistence_ms,
        total_ms,
        prompt_chars,
        output_chars,
        vector_used,
    )


async def recommend_next_action(
    db: AsyncSession,
    *,
    membership: CompanyMember,
    question: str | None = None,
    context_builder: Callable[..., Awaitable[CompanyContext]] = (
        build_company_brain_context
    ),
    provider_factory: Callable[[], T] | None = None,
) -> HeadAgentRecommendResponse:
    """Build CompanyContext, complete via LLMProvider, return a grounded proposal."""
    retrieval_query = (question or "").strip() or DEFAULT_OPERATING_QUESTION
    t0 = time.perf_counter()
    run = AgentRun(
        company_id=membership.company_id,
        agent_type=HEAD_AGENT_TYPE,
        status="running",
        started_at=_utcnow_iso(),
        trace_id=str(uuid.uuid4()),
    )
    db.add(run)
    await db.flush()

    try:
        context = await context_builder(
            db,
            membership=membership,
            query=retrieval_query,
        )
        t1 = time.perf_counter()
        vector_used = bool(context.meta and context.meta.vector_used)
        if context.objective is not None and context.objective.id is not None:
            run.objective_id = context.objective.id

        if context.objective is None:
            recommendation = no_active_objective_recommendation()
            run.status = "completed"
            run.completed_at = _utcnow_iso()
            agent_task = await _persist_recommendation_task(
                db,
                run=run,
                company_id=membership.company_id,
                question=retrieval_query,
                recommendation=recommendation,
            )
            await db.commit()
            t7 = time.perf_counter()
            total_ms = (t7 - t0) * 1000
            _log_head_agent_perf(
                run.trace_id,
                retrieval_ms=(t1 - t0) * 1000,
                prompt_build_ms=0.0,
                llm_ms=0.0,
                parsing_ms=0.0,
                persistence_ms=(t7 - t1) * 1000,
                total_ms=total_ms,
                vector_used=vector_used,
            )
            return HeadAgentRecommendResponse(
                agent_task_id=agent_task.id,
                recommendation=recommendation,
            )

        founder_question = resolve_founder_question(question, context.objective)
        provider = (provider_factory or get_llm_provider)()
        run.model_provider = provider.name
        request = build_head_agent_completion_request(
            question=founder_question,
            context=context,
        )
        t2 = time.perf_counter()
        prompt_chars = estimate_head_agent_prompt_chars(
            question=founder_question,
            context=context,
        )
        t3 = time.perf_counter()
        try:
            result = await provider.complete(request)
        except ProviderError as exc:
            raise _map_provider_error(exc) from exc
        t4 = time.perf_counter()

        parsed = parse_recommendation_payload(result.text)
        grounded_sources = ground_recommendation_sources(parsed.sources, context)
        recommendation = parsed.model_copy(
            update={
                "sources": grounded_sources,
                "confidence": clamp_confidence_for_grounding(
                    parsed.confidence,
                    grounded_sources,
                ),
            }
        )
        t5 = time.perf_counter()
        run.model_name = result.model
        run.status = "completed"
        run.completed_at = _utcnow_iso()
        agent_task = await _persist_recommendation_task(
            db,
            run=run,
            company_id=membership.company_id,
            question=founder_question,
            recommendation=recommendation,
        )
        await db.commit()
        t7 = time.perf_counter()
        output_chars = len(result.text)
        _log_head_agent_perf(
            run.trace_id,
            retrieval_ms=(t1 - t0) * 1000,
            prompt_build_ms=(t3 - t2) * 1000,
            llm_ms=(t4 - t3) * 1000,
            parsing_ms=(t5 - t4) * 1000,
            persistence_ms=(t7 - t5) * 1000,
            total_ms=(t7 - t0) * 1000,
            prompt_chars=prompt_chars,
            output_chars=output_chars,
            vector_used=vector_used,
        )
        return HeadAgentRecommendResponse(
            agent_task_id=agent_task.id,
            recommendation=recommendation,
        )
    except BrainContextError as exc:
        run.status = "failed"
        run.error_message = exc.detail
        run.completed_at = _utcnow_iso()
        await db.commit()
        raise
    except HeadAgentError as exc:
        run.status = "failed"
        run.error_message = exc.detail
        run.completed_at = _utcnow_iso()
        await db.commit()
        raise
