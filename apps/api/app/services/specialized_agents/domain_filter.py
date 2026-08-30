"""Domain-scoped filtering for specialized agent context."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from app.schemas.brain import (
    CompanyContext,
    ContextBelief,
    ContextCompany,
    ContextConstraint,
    ContextDecision,
    ContextEvidence,
    ContextFact,
    ContextLearning,
    ContextObjective,
    ContextSource,
)
from app.schemas.specialized_agent_types import AgentDomain

_CUSTOMER_GROWTH_MATCH_TERMS: tuple[str, ...] = (
    "customer",
    "customers",
    "acquisition",
    "acquire",
    "retention",
    "churn",
    "interview",
    "pricing",
    "price",
    "sales",
    "pipeline",
    "conversion",
    "funnel",
    "lead",
    "leads",
    "marketing",
    "growth",
    "gtm",
    "icp",
    "segment",
    "demand",
    "cac",
    "revenue",
    "paying",
    "subscriber",
    "signup",
    "onboarding",
)

_PRODUCT_MATCH_TERMS: tuple[str, ...] = (
    "product",
    "feature",
    "features",
    "roadmap",
    "ux",
    "ui",
    "user experience",
    "usability",
    "workflow",
    "quality",
    "bug",
    "performance",
    "release",
    "version",
    "activation",
    "usage",
    "adoption",
    "experiment",
    "prototype",
    "mvp",
    "validation",
    "prioritization",
    "prioritise",
    "prioritize",
    "engineering",
    "capacity",
    "onboarding",
    "technical debt",
    "confusing",
    "friction",
    "usability",
    "interface",
    "design",
    "ship",
    "shipped",
    "backlog",
    "sprint",
)

_PRODUCT_ONLY_TERMS: tuple[str, ...] = (
    "product roadmap",
    "product feature",
    "feature priorit",
    "technical debt",
    "bug fix",
    "usability",
    "user interface",
    "ui design",
)


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _matches_product(text: str) -> bool:
    normalized = _normalize(text)
    if not normalized:
        return False
    return any(term in normalized for term in _PRODUCT_MATCH_TERMS)


def _matches_customer_growth(text: str) -> bool:
    normalized = _normalize(text)
    if not normalized:
        return False
    if any(term in normalized for term in _CUSTOMER_GROWTH_MATCH_TERMS):
        return True
    if any(term in normalized for term in _PRODUCT_ONLY_TERMS):
        return False
    return False


def _fact_text(fact: ContextFact) -> str:
    parts = [fact.key or "", fact.value or ""]
    return " ".join(parts)


def _belief_text(belief: ContextBelief) -> str:
    return " ".join(filter(None, [belief.statement, belief.reasoning]))


def _decision_text(decision: ContextDecision) -> str:
    return " ".join(filter(None, [decision.title, decision.decision, decision.rationale]))


def _evidence_text(evidence: ContextEvidence) -> str:
    return " ".join(filter(None, [evidence.type, evidence.title, evidence.content]))


def _learning_text(learning: ContextLearning) -> str:
    return " ".join(filter(None, [learning.statement, learning.evidence_summary]))


def _source(
    entity_type: str,
    entity_id: uuid.UUID | None,
    source_type: str | None = None,
) -> ContextSource:
    return ContextSource(
        entity_type=entity_type,
        entity_id=None if entity_id is None else str(entity_id),
        source_type=source_type,
    )


def _provenance_source_type(item: object) -> str | None:
    provenance = getattr(item, "provenance", None)
    if provenance is None:
        return None
    return getattr(provenance, "source_type", None)


def _sources_from_sections(
    *,
    company: ContextCompany | None,
    objective: ContextObjective | None,
    constraints: list[ContextConstraint],
    facts: list[ContextFact],
    beliefs: list[ContextBelief],
    evidence: list[ContextEvidence],
    decisions: list[ContextDecision],
    learnings: list[ContextLearning],
) -> list[ContextSource]:
    sources: list[ContextSource] = []
    if company is not None:
        sources.append(_source("company", company.id))
    if objective is not None:
        sources.append(_source("objective", objective.id))
    for row in constraints:
        sources.append(_source("constraint", row.id, _provenance_source_type(row)))
    for row in facts:
        sources.append(_source("fact", row.id, _provenance_source_type(row)))
    for row in beliefs:
        sources.append(_source("belief", row.id, _provenance_source_type(row)))
    for row in evidence:
        sources.append(_source("evidence", row.id, _provenance_source_type(row)))
    for row in decisions:
        sources.append(_source("decision", row.id, _provenance_source_type(row)))
    for row in learnings:
        sources.append(_source("learning", row.id, _provenance_source_type(row)))
    return sources


def _filter_sections(
    context: CompanyContext,
    matcher: Callable[[str], bool],
) -> CompanyContext:
    facts = [row for row in context.facts if matcher(_fact_text(row))]
    beliefs = [row for row in context.beliefs if matcher(_belief_text(row))]
    decisions = [row for row in context.decisions if matcher(_decision_text(row))]
    evidence = [row for row in context.evidence if matcher(_evidence_text(row))]
    learnings = [row for row in context.learnings if matcher(_learning_text(row))]
    constraints = list(context.constraints)

    sources = _sources_from_sections(
        company=context.company,
        objective=context.objective,
        constraints=constraints,
        facts=facts,
        beliefs=beliefs,
        evidence=evidence,
        decisions=decisions,
        learnings=learnings,
    )

    return CompanyContext(
        company=context.company,
        objective=context.objective,
        bottleneck=context.bottleneck,
        constraints=constraints,
        facts=facts,
        beliefs=beliefs,
        evidence=evidence,
        decisions=decisions,
        experiments=[],
        learnings=learnings,
        memories=[],
        sources=sources,
        meta=context.meta,
    )


def filter_company_context_for_domain(
    context: CompanyContext,
    domain: AgentDomain,
) -> CompanyContext:
    """Apply domain scoping to Company Brain sections."""
    if domain is AgentDomain.CUSTOMER_GROWTH:
        return _filter_sections(context, _matches_customer_growth)
    if domain is AgentDomain.PRODUCT:
        return _filter_sections(context, _matches_product)
    return context
