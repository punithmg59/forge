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
from app.schemas.brain import CompanyContext
from app.schemas.head_agent import (
    HeadAgentRecommendation,
    HeadAgentRecommendResponse,
    OrchestrationMode,
    ProposedAction,
    SpecialistAnalysisSummary,
)
from app.schemas.specialized_agent import SpecializedAgentRecommendResponse
from app.services.brain_context import BrainContextError, build_company_brain_context
from app.services.head_agent_orchestration import (
    OrchestrationPlanMode,
    invoke_planned_specialists,
    resolve_orchestration_plan,
)
from app.services.head_agent_prompt import (
    DEFAULT_OPERATING_QUESTION,
    build_head_agent_completion_request,
    estimate_head_agent_prompt_chars,
    resolve_founder_question,
)
from app.services.head_agent_synthesis_prompt import build_head_agent_synthesis_completion_request
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
from app.services.recommendation_grounding import (
    clamp_confidence_for_grounding,
    ground_recommendation_sources,
)
from app.services.specialized_agents.errors import SpecializedAgentError
from app.services.specialized_agents.registry import get_specialized_agent

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
    specialist_agents: list[str] | None = None,
    orchestration_mode: str | None = None,
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
            "specialist_agents": specialist_agents or [],
            "orchestration_mode": orchestration_mode,
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


def _specialist_analyses_from_responses(
    responses: list[SpecializedAgentRecommendResponse],
) -> list[SpecialistAnalysisSummary]:
    analyses: list[SpecialistAnalysisSummary] = []
    for response in responses:
        agent = get_specialized_agent(response.agent_type)
        rec = response.recommendation
        analyses.append(
            SpecialistAnalysisSummary(
                agent_type=response.agent_type.value,
                domain=response.domain.value,
                display_name=agent.display_name,
                agent_task_id=response.agent_task_id,
                title=rec.title,
                recommendation=rec.recommendation,
                rationale=rec.rationale,
                confidence=rec.confidence,
                sources=list(rec.sources),
            )
        )
    return analyses


def _build_recommend_response(
    *,
    agent_task_id: uuid.UUID,
    recommendation: HeadAgentRecommendation,
    founder_question: str,
    orchestration_mode: OrchestrationMode,
    specialist_responses: list[SpecializedAgentRecommendResponse] | None = None,
) -> HeadAgentRecommendResponse:
    specialist_agents = (
        [r.agent_type.value for r in specialist_responses] if specialist_responses else []
    )
    specialist_analyses = (
        _specialist_analyses_from_responses(specialist_responses)
        if specialist_responses
        else []
    )
    return HeadAgentRecommendResponse(
        agent_task_id=agent_task_id,
        recommendation=recommendation,
        orchestration_mode=orchestration_mode,
        specialist_agents=specialist_agents,
        specialist_analyses=specialist_analyses,
        founder_question=founder_question,
    )


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


def _log_head_agent_orchestration_perf(
    trace_id: str,
    *,
    routing_ms: float,
    specialist_ms: float,
    synthesis_ms: float,
    retrieval_ms: float,
    persistence_ms: float,
    total_ms: float,
    orchestration_mode: str,
    specialist_count: int,
) -> None:
    logger.info(
        "head_agent_orchestration_perf trace_id=%s mode=%s specialist_count=%d "
        "routing_ms=%.1f specialist_ms=%.1f synthesis_ms=%.1f retrieval_ms=%.1f "
        "persistence_ms=%.1f total_ms=%.1f",
        trace_id,
        orchestration_mode,
        specialist_count,
        routing_ms,
        specialist_ms,
        synthesis_ms,
        retrieval_ms,
        persistence_ms,
        total_ms,
    )


async def _run_head_agent_direct(
    db: AsyncSession,
    *,
    run: AgentRun,
    membership: CompanyMember,
    founder_question: str,
    context: CompanyContext,
    provider: LLMProvider,
    t0: float,
    t1: float,
    vector_used: bool,
) -> HeadAgentRecommendResponse:
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
        orchestration_mode="head_only",
    )
    await db.commit()
    t7 = time.perf_counter()
    output_chars = len(result.text)
    _log_head_agent_perf(
        run.trace_id or "",
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
    return _build_recommend_response(
        agent_task_id=agent_task.id,
        recommendation=recommendation,
        founder_question=founder_question,
        orchestration_mode="head_only",
    )


async def _run_head_agent_synthesis(
    db: AsyncSession,
    *,
    run: AgentRun,
    membership: CompanyMember,
    founder_question: str,
    context: CompanyContext,
    provider: LLMProvider,
    specialist_responses: list[SpecializedAgentRecommendResponse],
    orchestration_mode: str,
    t0: float,
    t1: float,
    routing_ms: float = 0.0,
    specialist_ms: float = 0.0,
) -> HeadAgentRecommendResponse:
    specialist_agents = [r.agent_type.value for r in specialist_responses]
    request = build_head_agent_synthesis_completion_request(
        question=founder_question,
        context=context,
        specialist_responses=specialist_responses,
    )
    t_synth_start = time.perf_counter()
    try:
        result = await provider.complete(request)
    except ProviderError as exc:
        raise _map_provider_error(exc) from exc
    t_synth_end = time.perf_counter()

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
    t_parse_end = time.perf_counter()
    run.model_name = result.model
    run.status = "completed"
    run.completed_at = _utcnow_iso()
    agent_task = await _persist_recommendation_task(
        db,
        run=run,
        company_id=membership.company_id,
        question=founder_question,
        recommendation=recommendation,
        specialist_agents=specialist_agents,
        orchestration_mode=orchestration_mode,
    )
    await db.commit()
    t_end = time.perf_counter()
    _log_head_agent_orchestration_perf(
        run.trace_id or "",
        routing_ms=routing_ms,
        specialist_ms=specialist_ms,
        synthesis_ms=(t_synth_end - t_synth_start) * 1000,
        retrieval_ms=(t1 - t0) * 1000,
        persistence_ms=(t_end - t_parse_end) * 1000,
        total_ms=(t_end - t0) * 1000,
        orchestration_mode=orchestration_mode,
        specialist_count=len(specialist_responses),
    )
    return _build_recommend_response(
        agent_task_id=agent_task.id,
        recommendation=recommendation,
        founder_question=founder_question,
        orchestration_mode=orchestration_mode,
        specialist_responses=specialist_responses,
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

        founder_question = resolve_founder_question(question, context.objective)

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
                orchestration_mode="head_only",
                founder_question=retrieval_query,
            )
        provider = (provider_factory or get_llm_provider)()
        run.model_provider = provider.name

        t_route_start = time.perf_counter()
        plan = await resolve_orchestration_plan(
            founder_question,
            provider_factory=provider_factory,
        )
        routing_ms = (time.perf_counter() - t_route_start) * 1000

        if plan.mode is OrchestrationPlanMode.HEAD_ONLY:
            return await _run_head_agent_direct(
                db,
                run=run,
                membership=membership,
                founder_question=founder_question,
                context=context,
                provider=provider,
                t0=t0,
                t1=t1,
                vector_used=vector_used,
            )

        specialist_ms = 0.0
        specialist_responses: list[SpecializedAgentRecommendResponse] = []
        try:
            specialist_responses, specialist_ms = await invoke_planned_specialists(
                db,
                membership=membership,
                question=founder_question,
                plan=plan,
                context_builder=context_builder,
                provider_factory=provider_factory,
                orchestration_trace_id=run.trace_id,
            )
        except SpecializedAgentError:
            logger.warning(
                "head_agent_specialist_fallback trace_id=%s reason=specialist_failed",
                run.trace_id,
            )
            return await _run_head_agent_direct(
                db,
                run=run,
                membership=membership,
                founder_question=founder_question,
                context=context,
                provider=provider,
                t0=t0,
                t1=t1,
                vector_used=vector_used,
            )

        if not specialist_responses:
            return await _run_head_agent_direct(
                db,
                run=run,
                membership=membership,
                founder_question=founder_question,
                context=context,
                provider=provider,
                t0=t0,
                t1=t1,
                vector_used=vector_used,
            )

        orchestration_mode = (
            "multi_specialist"
            if plan.mode is OrchestrationPlanMode.MULTI_SPECIALIST
            else "single_specialist"
        )
        response = await _run_head_agent_synthesis(
            db,
            run=run,
            membership=membership,
            founder_question=founder_question,
            context=context,
            provider=provider,
            specialist_responses=specialist_responses,
            orchestration_mode=orchestration_mode,
            t0=t0,
            t1=t1,
            routing_ms=routing_ms,
            specialist_ms=specialist_ms,
        )
        return response
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
