"""Shared recommendation source grounding utilities."""

from __future__ import annotations

from app.schemas.brain import CompanyContext, ContextSource
from app.schemas.head_agent import RecommendationConfidence


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
