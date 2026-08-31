"""Specialized agent routing orchestration."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_member import CompanyMember
from app.schemas.specialized_agent import SpecializedAgentRecommendResponse
from app.schemas.specialized_routing import (
    DeterministicRoutingStatus,
    SpecializedRoutingDecision,
    SpecializedRoutingHandoff,
)
from app.services.brain_context import build_company_brain_context
from app.services.llm import LLMProvider
from app.services.specialized_agents.base import TContextBuilder
from app.services.specialized_agents.context import assert_scope_matches_membership
from app.services.specialized_agents.registry import get_specialized_agent
from app.services.specialized_agents.routing.deterministic import classify_deterministic
from app.services.specialized_agents.routing.errors import RoutingError
from app.services.specialized_agents.routing.llm_classifier import classify_with_llm

logger = logging.getLogger(__name__)


def _log_routing_perf(
    *,
    routing_method: str,
    deterministic_ms: float,
    llm_ms: float,
    total_ms: float,
) -> None:
    logger.info(
        "specialized_routing_perf method=%s deterministic_ms=%.1f llm_ms=%.1f total_ms=%.1f",
        routing_method,
        deterministic_ms,
        llm_ms,
        total_ms,
    )


async def route_specialized_agent(
    db: AsyncSession,
    *,
    membership: CompanyMember,
    question: str,
    context_builder: TContextBuilder = build_company_brain_context,
    provider_factory: Callable[[], LLMProvider] | None = None,
    include_context: bool = True,
    llm_classifier: Callable[..., Awaitable[SpecializedRoutingDecision]] = classify_with_llm,
) -> SpecializedRoutingHandoff:
    """Route a founder question to a specialist or Head Agent fallback.

    Does NOT invoke specialist reasoning (recommend). May retrieve context for handoff.
    Does NOT create AgentRun rows — routing is observability-only in Task 9.2.
    """
    stripped = question.strip()
    if not stripped:
        raise RoutingError("Question must not be empty", status_code=400)

    t0 = time.perf_counter()
    deterministic = classify_deterministic(stripped)
    t1 = time.perf_counter()
    llm_ms = 0.0

    if deterministic.status is DeterministicRoutingStatus.STRONG_MATCH:
        decision = deterministic.decision
        assert decision is not None
        routing_method = "deterministic"
    elif deterministic.status is DeterministicRoutingStatus.AMBIGUOUS:
        decision = deterministic.decision
        assert decision is not None
        routing_method = "fallback"
    else:
        t_llm_start = time.perf_counter()
        decision = await llm_classifier(
            stripped,
            provider_factory=provider_factory,
        )
        llm_ms = (time.perf_counter() - t_llm_start) * 1000
        routing_method = decision.routing_method

        if (
            deterministic.status is DeterministicRoutingStatus.NO_MATCH
            and decision.fallback_to_head_agent
            and decision.routing_method == "llm"
        ):
            routing_method = "llm"

    context = None
    if (
        include_context
        and decision.selected_agent is not None
        and not decision.fallback_to_head_agent
    ):
        agent = get_specialized_agent(decision.selected_agent)
        context = await agent.retrieve_context(
            db,
            membership=membership,
            query=stripped,
            context_builder=context_builder,
        )
        assert_scope_matches_membership(
            context.scope,
            company_id=membership.company_id,
            user_id=membership.user_id,
        )

    total_ms = (time.perf_counter() - t0) * 1000
    deterministic_ms = (t1 - t0) * 1000
    _log_routing_perf(
        routing_method=routing_method,
        deterministic_ms=deterministic_ms,
        llm_ms=llm_ms,
        total_ms=total_ms,
    )

    return SpecializedRoutingHandoff(decision=decision, context=context)


async def recommend_routed_specialist(
    db: AsyncSession,
    *,
    membership: CompanyMember,
    question: str,
    context_builder: TContextBuilder = build_company_brain_context,
    provider_factory: Callable[[], LLMProvider] | None = None,
) -> tuple[SpecializedRoutingHandoff, SpecializedAgentRecommendResponse | None]:
    """Route then invoke specialist recommend() when a specialist is selected.

    Returns (handoff, None) when routing falls back to Head Agent.
    Does NOT invoke Head Agent — caller handles general fallback.
    """
    handoff = await route_specialized_agent(
        db,
        membership=membership,
        question=question,
        context_builder=context_builder,
        provider_factory=provider_factory,
        include_context=False,
    )
    if handoff.decision.fallback_to_head_agent or handoff.decision.selected_agent is None:
        return handoff, None

    agent = get_specialized_agent(handoff.decision.selected_agent)
    response = await agent.recommend(
        db,
        membership=membership,
        question=question,
        context_builder=context_builder,
        provider_factory=provider_factory,
    )
    return handoff, response
