"""Pure Company Brain context assembly. No I/O, retrieval, or LLM."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TypeVar

from app.schemas.brain import (
    CompanyContext,
    ContextBelief,
    ContextCompany,
    ContextConstraint,
    ContextDecision,
    ContextEvidence,
    ContextExperiment,
    ContextFact,
    ContextLearning,
    ContextMemory,
    ContextObjective,
    ContextSource,
    Provenance,
    RetrievalMeta,
)
from app.services.retrieval.classifier import QueryClassification
from app.services.retrieval.vector import VectorHit

MAX_CONSTRAINTS = 20
MAX_FACTS = 20
MAX_BELIEFS = 20
MAX_EVIDENCE = 15
MAX_DECISIONS = 15
MAX_EXPERIMENTS = 15
MAX_LEARNINGS = 15
MAX_MEMORIES = 8

_SECTION_ORDER = (
    "company",
    "objective",
    "bottleneck",
    "constraints",
    "facts",
    "beliefs",
    "evidence",
    "decisions",
    "experiments",
    "learnings",
    "memories",
)

T = TypeVar("T")


def assemble_context(
    structured_results: CompanyContext | None,
    vector_results: Sequence[VectorHit] | None,
    classification_meta: QueryClassification | None,
) -> CompanyContext:
    """Merge already-retrieved structured and vector data into CompanyContext."""
    structured = structured_results or CompanyContext()
    constraints = _dedupe_and_cap(structured.constraints, MAX_CONSTRAINTS)
    facts = _dedupe_and_cap(structured.facts, MAX_FACTS)
    beliefs = _dedupe_and_cap(structured.beliefs, MAX_BELIEFS)
    evidence = _dedupe_and_cap(structured.evidence, MAX_EVIDENCE)
    decisions = _dedupe_and_cap(structured.decisions, MAX_DECISIONS)
    experiments = _dedupe_and_cap(structured.experiments, MAX_EXPERIMENTS)
    learnings = _dedupe_and_cap(structured.learnings, MAX_LEARNINGS)
    memories = _dedupe_and_cap(_memories_from_hits(vector_results or ()), MAX_MEMORIES)

    context = CompanyContext(
        company=structured.company,
        objective=structured.objective,
        bottleneck=structured.bottleneck,
        constraints=constraints,
        facts=facts,
        beliefs=beliefs,
        evidence=evidence,
        decisions=decisions,
        experiments=experiments,
        learnings=learnings,
        memories=memories,
        sources=_sources_from(
            company=structured.company,
            objective=structured.objective,
            constraints=constraints,
            facts=facts,
            beliefs=beliefs,
            evidence=evidence,
            decisions=decisions,
            experiments=experiments,
            learnings=learnings,
            memories=memories,
        ),
        meta=_meta(
            structured,
            classification_meta,
            company=structured.company,
            objective=structured.objective,
            bottleneck=structured.bottleneck,
            constraints=constraints,
            facts=facts,
            beliefs=beliefs,
            evidence=evidence,
            decisions=decisions,
            experiments=experiments,
            learnings=learnings,
            memories=memories,
        ),
    )
    return context


def _memories_from_hits(hits: Sequence[VectorHit]) -> list[ContextMemory]:
    memories: list[ContextMemory] = []
    for hit in hits:
        memories.append(
            ContextMemory(
                id=_as_uuid(hit.memory_id),
                memory_type=hit.memory_type,
                content=hit.content,
                created_at=hit.created_at,
                provenance=Provenance(
                    source_type=hit.source_type,
                    source_reference=hit.source_reference,
                ),
            )
        )
    return memories


def _dedupe_and_cap(items: Sequence[T], cap: int) -> list[T]:
    seen: set[str] = set()
    kept: list[T] = []
    for item in items:
        entity_id = _item_id(item)
        if entity_id is not None:
            if entity_id in seen:
                continue
            seen.add(entity_id)
        kept.append(item)
        if len(kept) >= cap:
            break
    return kept


def _item_id(item: object) -> str | None:
    value = getattr(item, "id", None)
    if value is None:
        return None
    return str(value)


def _as_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _sources_from(
    *,
    company: ContextCompany | None,
    objective: ContextObjective | None,
    constraints: Sequence[ContextConstraint],
    facts: Sequence[ContextFact],
    beliefs: Sequence[ContextBelief],
    evidence: Sequence[ContextEvidence],
    decisions: Sequence[ContextDecision],
    experiments: Sequence[ContextExperiment],
    learnings: Sequence[ContextLearning],
    memories: Sequence[ContextMemory],
) -> list[ContextSource]:
    sources: list[ContextSource] = []
    if company is not None:
        sources.append(_source("company", company.id, None))
    if objective is not None:
        sources.append(_source("objective", objective.id, None))
    for row in constraints:
        sources.append(_source("constraint", row.id, _source_type(row)))
    for row in facts:
        sources.append(_source("fact", row.id, _source_type(row)))
    for row in beliefs:
        sources.append(_source("belief", row.id, _source_type(row)))
    for row in evidence:
        sources.append(_source("evidence", row.id, _source_type(row)))
    for row in decisions:
        sources.append(_source("decision", row.id, _source_type(row)))
    for row in experiments:
        sources.append(_source("experiment", row.id, _source_type(row)))
    for row in learnings:
        sources.append(_source("learning", row.id, _source_type(row)))
    for row in memories:
        sources.append(_source("memory", row.id, _source_type(row)))
    return sources


def _source(
    entity_type: str,
    entity_id: uuid.UUID | None,
    source_type: str | None,
) -> ContextSource:
    return ContextSource(
        entity_type=entity_type,
        entity_id=None if entity_id is None else str(entity_id),
        source_type=source_type,
    )


def _source_type(item: object) -> str | None:
    provenance = getattr(item, "provenance", None)
    if provenance is None:
        return None
    return getattr(provenance, "source_type", None)


def _meta(
    structured: CompanyContext,
    classification_meta: QueryClassification | None,
    **sections: object,
) -> RetrievalMeta:
    query = structured.meta.query if structured.meta is not None else None
    classification = None if classification_meta is None else classification_meta.intent.value
    empty = [name for name in _SECTION_ORDER if _is_empty(sections.get(name))]
    return RetrievalMeta(
        query=query,
        classification=classification,
        assembled_at=datetime.now(UTC),
        sections_empty=empty,
        structured_used=structured.meta.structured_used if structured.meta is not None else False,
        vector_used=bool(sections.get("memories")),
        retrieved_at=structured.meta.retrieved_at if structured.meta is not None else None,
    )


def _is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, list):
        return len(value) == 0
    return False
