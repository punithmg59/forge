"""Product specialized reasoning agent."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TypeVar

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_member import CompanyMember
from app.schemas.head_agent import ProposedAction
from app.schemas.specialized_agent import (
    SpecializedAgentContext,
    SpecializedAgentRecommendation,
    SpecializedAgentRecommendResponse,
)
from app.schemas.specialized_agent_types import AgentDomain, SpecializedAgentType
from app.schemas.specialized_routing_types import INTENT_TO_DOMAIN, RoutingIntent
from app.services.brain_context import build_company_brain_context
from app.services.llm import (
    CompletionRequest,
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
from app.services.specialized_agents.audit import (
    new_specialized_agent_run,
    new_specialized_agent_task,
)
from app.services.specialized_agents.base import SpecializedAgent, TContextBuilder
from app.services.specialized_agents.errors import SpecializedAgentError
from app.services.specialized_agents.grounding import (
    ground_specialized_recommendation,
    parse_specialized_recommendation_payload,
)
from app.services.specialized_agents.product_prompt import build_product_completion_request

T = TypeVar("T", bound=LLMProvider)

logger = logging.getLogger(__name__)

NO_OBJECTIVE_TITLE = "Active objective required"
NO_OBJECTIVE_RECOMMENDATION = (
    "Forge needs an active objective before it can make a product recommendation."
)
NO_OBJECTIVE_RATIONALE = (
    "The Company Brain does not currently contain an active objective. "
    "Create and prioritize an active objective first."
)


class ProductAgentError(SpecializedAgentError):
    """Product agent orchestration errors."""


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _parse_recommendation_text(text: str) -> SpecializedAgentRecommendation:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```").strip()
        fence = stripped.rfind("```")
        if fence != -1:
            stripped = stripped[:fence].strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ProductAgentError("LLM returned an invalid response", 502) from exc
    if not isinstance(payload, dict):
        raise ProductAgentError("LLM returned an invalid response", 502)
    try:
        return parse_specialized_recommendation_payload(payload)
    except ValidationError as exc:
        raise ProductAgentError("LLM returned an invalid response", 502) from exc


def _no_objective_recommendation() -> SpecializedAgentRecommendation:
    return SpecializedAgentRecommendation(
        title=NO_OBJECTIVE_TITLE,
        recommendation=NO_OBJECTIVE_RECOMMENDATION,
        rationale=NO_OBJECTIVE_RATIONALE,
        proposed_action=ProposedAction(type="none"),
        sources=[],
        confidence="low",
    )


def _map_provider_error(exc: ProviderError) -> ProductAgentError:
    if isinstance(exc, ProviderAuthError):
        return ProductAgentError("LLM provider is not configured", 502)
    if isinstance(exc, ProviderTimeoutError):
        return ProductAgentError("LLM request timed out", 504)
    if isinstance(exc, ProviderUnavailableError):
        return ProductAgentError("LLM provider unavailable", 502)
    if isinstance(exc, ProviderRateLimitError):
        return ProductAgentError("LLM rate limit exceeded", 429)
    if isinstance(exc, ProviderInvalidResponseError):
        return ProductAgentError("LLM returned an invalid response", 502)
    if isinstance(exc, ProviderUnexpectedError):
        return ProductAgentError("LLM provider error", 502)
    return ProductAgentError("LLM provider error", 502)


def _log_product_perf(
    trace_id: str,
    *,
    retrieval_ms: float,
    llm_ms: float,
    parsing_ms: float,
    persistence_ms: float,
    total_ms: float,
) -> None:
    logger.info(
        "product_agent_perf trace_id=%s retrieval_ms=%.1f llm_ms=%.1f "
        "parsing_ms=%.1f persistence_ms=%.1f total_ms=%.1f",
        trace_id,
        retrieval_ms,
        llm_ms,
        parsing_ms,
        persistence_ms,
        total_ms,
    )


class ProductAgent(SpecializedAgent):
    @property
    def agent_type(self) -> SpecializedAgentType:
        return SpecializedAgentType.PRODUCT

    @property
    def display_name(self) -> str:
        return "Product"

    @property
    def description(self) -> str:
        return (
            "Reasons about product strategy, roadmap, feature prioritization, "
            "UX, quality, and discovery using domain-scoped Company Brain context."
        )

    @property
    def supported_intents(self) -> frozenset[str]:
        return frozenset(
            intent.value
            for intent in RoutingIntent
            if INTENT_TO_DOMAIN[intent] is AgentDomain.PRODUCT
        )

    def build_prompt(
        self,
        *,
        question: str,
        context: SpecializedAgentContext,
    ) -> CompletionRequest:
        return build_product_completion_request(question=question, context=context)

    async def recommend(
        self,
        db: AsyncSession,
        *,
        membership: CompanyMember,
        question: str | None = None,
        context_builder: TContextBuilder = build_company_brain_context,
        provider_factory: Callable[[], T] | None = None,
        orchestration_trace_id: str | None = None,
    ) -> SpecializedAgentRecommendResponse:
        founder_question = (question or "").strip()
        if not founder_question:
            raise ProductAgentError("Question must not be empty", 400)

        t0 = time.perf_counter()
        run = new_specialized_agent_run(
            company_id=membership.company_id,
            agent_type=self.agent_type,
            trace_id=orchestration_trace_id,
        )
        db.add(run)
        await db.flush()

        try:
            context = await self.retrieve_context(
                db,
                membership=membership,
                query=founder_question,
                context_builder=context_builder,
            )
            t1 = time.perf_counter()

            if context.objective is None:
                recommendation = _no_objective_recommendation()
                run.status = "completed"
                run.completed_at = _utcnow_iso()
                agent_task = new_specialized_agent_task(
                    company_id=membership.company_id,
                    agent_run=run,
                    agent_type=self.agent_type,
                    domain=self.domain,
                    question=founder_question,
                    recommendation=recommendation,
                )
                db.add(agent_task)
                await db.commit()
                t_end = time.perf_counter()
                _log_product_perf(
                    run.trace_id or "",
                    retrieval_ms=(t1 - t0) * 1000,
                    llm_ms=0.0,
                    parsing_ms=0.0,
                    persistence_ms=(t_end - t1) * 1000,
                    total_ms=(t_end - t0) * 1000,
                )
                return SpecializedAgentRecommendResponse(
                    agent_type=self.agent_type,
                    domain=self.domain,
                    agent_task_id=agent_task.id,
                    recommendation=recommendation,
                )

            if context.objective.id is not None:
                run.objective_id = context.objective.id

            provider = (provider_factory or get_llm_provider)()
            run.model_provider = provider.name
            request = build_product_completion_request(
                question=founder_question,
                context=context,
            )
            t2 = time.perf_counter()
            try:
                result = await provider.complete(request)
            except ProviderError as exc:
                raise _map_provider_error(exc) from exc
            t3 = time.perf_counter()

            parsed = _parse_recommendation_text(result.text)
            recommendation = ground_specialized_recommendation(parsed, context)
            t4 = time.perf_counter()

            run.model_name = result.model
            run.status = "completed"
            run.completed_at = _utcnow_iso()
            agent_task = new_specialized_agent_task(
                company_id=membership.company_id,
                agent_run=run,
                agent_type=self.agent_type,
                domain=self.domain,
                question=founder_question,
                recommendation=recommendation,
            )
            db.add(agent_task)
            await db.commit()
            t_end = time.perf_counter()

            _log_product_perf(
                run.trace_id or "",
                retrieval_ms=(t1 - t0) * 1000,
                llm_ms=(t3 - t2) * 1000,
                parsing_ms=(t4 - t3) * 1000,
                persistence_ms=(t_end - t4) * 1000,
                total_ms=(t_end - t0) * 1000,
            )

            return SpecializedAgentRecommendResponse(
                agent_type=self.agent_type,
                domain=self.domain,
                agent_task_id=agent_task.id,
                recommendation=recommendation,
            )
        except ProductAgentError as exc:
            run.status = "failed"
            run.error_message = exc.detail
            run.completed_at = _utcnow_iso()
            await db.commit()
            raise
        except SpecializedAgentError as exc:
            run.status = "failed"
            run.error_message = exc.detail
            run.completed_at = _utcnow_iso()
            await db.commit()
            raise ProductAgentError(exc.detail, exc.status_code) from exc
