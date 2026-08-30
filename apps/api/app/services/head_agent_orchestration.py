"""Head Agent specialist orchestration planning and invocation."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_member import CompanyMember
from app.schemas.specialized_agent import SpecializedAgentRecommendResponse
from app.schemas.specialized_agent_types import SpecializedAgentType
from app.schemas.specialized_routing import DeterministicRoutingStatus
from app.services.brain_context import build_company_brain_context
from app.services.llm import LLMProvider
from app.services.specialized_agents.base import TContextBuilder
from app.services.specialized_agents.errors import SpecializedAgentError
from app.services.specialized_agents.registry import get_specialized_agent
from app.services.specialized_agents.routing.deterministic import (
    classify_deterministic,
    detect_mixed_domain_strong_match,
)
from app.services.specialized_agents.routing.errors import InvalidClassification
from app.services.specialized_agents.routing.llm_classifier import classify_with_llm

logger = logging.getLogger(__name__)

OrchestrationMode = Literal["head_only", "single_specialist", "multi_specialist"]
MAX_SPECIALISTS = 2


class OrchestrationPlanMode(str, Enum):
    HEAD_ONLY = "head_only"
    SINGLE_SPECIALIST = "single_specialist"
    MULTI_SPECIALIST = "multi_specialist"


@dataclass(frozen=True)
class OrchestrationPlan:
    mode: OrchestrationPlanMode
    agents: tuple[SpecializedAgentType, ...] = field(default_factory=tuple)
    routing_method: str = "deterministic"
    reason: str = ""


def is_mixed_domain_question(question: str) -> bool:
    """Both customer/growth and product domains have strong deterministic signals."""
    return detect_mixed_domain_strong_match(question)


async def resolve_orchestration_plan(
    question: str,
    *,
    provider_factory: Callable[[], LLMProvider] | None = None,
    llm_classifier: Callable[..., Awaitable[object]] | None = None,
) -> OrchestrationPlan:
    """Decide whether Head Agent runs alone or invokes specialist(s)."""
    stripped = question.strip()
    deterministic = classify_deterministic(stripped)

    if deterministic.status is DeterministicRoutingStatus.AMBIGUOUS:
        return OrchestrationPlan(
            mode=OrchestrationPlanMode.HEAD_ONLY,
            reason="Ambiguous operating question — Head Agent only.",
            routing_method="fallback",
        )

    if is_mixed_domain_question(stripped):
        return OrchestrationPlan(
            mode=OrchestrationPlanMode.MULTI_SPECIALIST,
            agents=(
                SpecializedAgentType.CUSTOMER_GROWTH,
                SpecializedAgentType.PRODUCT,
            ),
            routing_method="deterministic",
            reason="Strong signals for both customer/growth and product domains.",
        )

    if deterministic.status is DeterministicRoutingStatus.STRONG_MATCH:
        decision = deterministic.decision
        assert decision is not None and decision.selected_agent is not None
        return OrchestrationPlan(
            mode=OrchestrationPlanMode.SINGLE_SPECIALIST,
            agents=(decision.selected_agent,),
            routing_method="deterministic",
            reason=decision.reason,
        )

    classifier = llm_classifier or classify_with_llm
    try:
        decision = await classifier(stripped, provider_factory=provider_factory)
    except InvalidClassification:
        return OrchestrationPlan(
            mode=OrchestrationPlanMode.HEAD_ONLY,
            reason="Routing classification unavailable — Head Agent only.",
            routing_method="fallback",
        )
    if decision.fallback_to_head_agent or decision.selected_agent is None:
        return OrchestrationPlan(
            mode=OrchestrationPlanMode.HEAD_ONLY,
            reason=decision.reason,
            routing_method=decision.routing_method,
        )

    return OrchestrationPlan(
        mode=OrchestrationPlanMode.SINGLE_SPECIALIST,
        agents=(decision.selected_agent,),
        routing_method=decision.routing_method,
        reason=decision.reason,
    )


async def invoke_planned_specialists(
    db: AsyncSession,
    *,
    membership: CompanyMember,
    question: str,
    plan: OrchestrationPlan,
    context_builder: TContextBuilder = build_company_brain_context,
    provider_factory: Callable[[], LLMProvider] | None = None,
    orchestration_trace_id: str | None = None,
) -> tuple[list[SpecializedAgentRecommendResponse], float]:
    """Invoke up to two specialists per plan. Returns responses and elapsed ms."""
    if plan.mode is OrchestrationPlanMode.HEAD_ONLY:
        return [], 0.0

    agents = plan.agents[:MAX_SPECIALISTS]
    seen: set[SpecializedAgentType] = set()
    ordered: list[SpecializedAgentType] = []
    for agent_type in agents:
        if agent_type not in seen:
            seen.add(agent_type)
            ordered.append(agent_type)

    t0 = time.perf_counter()
    responses: list[SpecializedAgentRecommendResponse] = []
    for agent_type in ordered:
        agent = get_specialized_agent(agent_type)
        try:
            response = await agent.recommend(
                db,
                membership=membership,
                question=question,
                context_builder=context_builder,
                provider_factory=provider_factory,
                orchestration_trace_id=orchestration_trace_id,
            )
        except SpecializedAgentError as exc:
            logger.warning(
                "specialist_invoke_failed agent_type=%s detail=%s",
                agent_type.value,
                exc.detail,
            )
            if plan.mode is OrchestrationPlanMode.SINGLE_SPECIALIST:
                raise
            continue
        responses.append(response)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    return responses, elapsed_ms
