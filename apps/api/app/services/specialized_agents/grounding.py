"""Grounding helpers for specialist recommendations."""

from __future__ import annotations

from app.schemas.brain import CompanyContext
from app.schemas.specialized_agent import SpecializedAgentContext, SpecializedAgentRecommendation
from app.services.head_agent import clamp_confidence_for_grounding, ground_recommendation_sources


def _grounding_context(context: SpecializedAgentContext | CompanyContext) -> CompanyContext:
    if isinstance(context, CompanyContext):
        return context
    return CompanyContext(sources=list(context.sources))


def ground_specialized_recommendation(
    recommendation: SpecializedAgentRecommendation,
    context: SpecializedAgentContext | CompanyContext,
) -> SpecializedAgentRecommendation:
    """Keep only sources that exist on the supplied Brain context."""
    brain_context = _grounding_context(context)
    grounded_sources = ground_recommendation_sources(recommendation.sources, brain_context)
    return recommendation.model_copy(
        update={
            "sources": grounded_sources,
            "confidence": clamp_confidence_for_grounding(
                recommendation.confidence,
                grounded_sources,
            ),
        }
    )


def parse_specialized_recommendation_payload(payload: dict) -> SpecializedAgentRecommendation:
    """Validate structured specialist output without LLM invocation."""
    return SpecializedAgentRecommendation.model_validate(payload)
