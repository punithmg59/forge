"""Unit tests for Task 5.5 context assembly. In-memory only."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.schemas.brain import (
    CompanyContext,
    ContextBelief,
    ContextCompany,
    ContextConstraint,
    ContextEvidence,
    ContextFact,
    ContextMemory,
    ContextObjective,
    Provenance,
    RetrievalMeta,
)
from app.services.retrieval.assemble import MAX_FACTS, assemble_context
from app.services.retrieval.classifier import QueryIntent, classify_query
from app.services.retrieval.vector import VectorHit


def _id() -> uuid.UUID:
    return uuid.uuid4()


def _classification(question: str = "Give me a complete picture of the company."):
    return classify_query(question)


def test_full_brain() -> None:
    fact_id = _id()
    belief_id = _id()
    evidence_id = _id()
    memory_id = _id()
    structured = CompanyContext(
        company=ContextCompany(id=_id(), name="Forge"),
        objective=ContextObjective(id=_id(), title="Get 20 customers", status="active"),
        bottleneck="bandwidth",
        constraints=[ContextConstraint(id=_id(), name="burn", status="active")],
        facts=[
            ContextFact(
                id=fact_id,
                key="mrr",
                value="12000",
                confidence=0.9,
                provenance=Provenance(source_type="analytics", source_reference="mixpanel"),
            )
        ],
        beliefs=[
            ContextBelief(
                id=belief_id,
                statement="Founders want CLI",
                provenance=Provenance(source_type="founder_input"),
            )
        ],
        evidence=[
            ContextEvidence(
                id=evidence_id,
                title="Interview",
                content="Onboarding was long",
                provenance=Provenance(source_type="customer_feedback"),
            )
        ],
        meta=RetrievalMeta(query="complete picture"),
    )
    created = datetime(2026, 8, 23, tzinfo=UTC)
    hits = [
        VectorHit(
            memory_id=str(memory_id),
            content="CLI preference note",
            source_type="founder_input",
            source_reference="notes",
            memory_type="semantic",
            created_at=created,
        )
    ]

    context = assemble_context(structured, hits, _classification())

    assert context.company is not None
    assert context.company.name == "Forge"
    assert context.objective is not None
    assert context.objective.title == "Get 20 customers"
    assert context.facts[0].key == "mrr"
    assert context.beliefs[0].statement == "Founders want CLI"
    assert context.evidence[0].title == "Interview"
    assert context.memories[0].content == "CLI preference note"
    assert context.meta is not None
    assert context.meta.query == "complete picture"
    assert context.meta.classification == QueryIntent.BROAD.value
    assert context.meta.assembled_at is not None
    assert "facts" not in context.meta.sections_empty
    assert "memories" not in context.meta.sections_empty
    source_types = {source.entity_type for source in context.sources}
    assert {"company", "objective", "fact", "belief", "evidence", "memory"} <= source_types


def test_empty_brain() -> None:
    context = assemble_context(CompanyContext(), [], _classification("What should we do next?"))
    assert context.company is None
    assert context.objective is None
    assert context.bottleneck is None
    assert context.constraints == []
    assert context.facts == []
    assert context.beliefs == []
    assert context.evidence == []
    assert context.decisions == []
    assert context.experiments == []
    assert context.learnings == []
    assert context.memories == []
    assert context.sources == []
    assert context.meta is not None
    assert "objective" in context.meta.sections_empty
    assert "facts" in context.meta.sections_empty
    assert "beliefs" in context.meta.sections_empty
    assert "evidence" in context.meta.sections_empty
    assert "memories" in context.meta.sections_empty


def test_partial_brain() -> None:
    structured = CompanyContext(
        facts=[ContextFact(id=_id(), key="users", value="10")],
    )
    context = assemble_context(structured, None, None)
    assert context.facts[0].value == "10"
    assert context.objective is None
    assert context.beliefs == []
    assert context.memories == []
    assert context.meta is not None
    assert "facts" not in context.meta.sections_empty
    assert "beliefs" in context.meta.sections_empty
    assert context.meta.classification is None


def test_duplicate_entity_id_within_one_section() -> None:
    shared = _id()
    structured = CompanyContext(
        facts=[
            ContextFact(id=shared, key="mrr", value="first"),
            ContextFact(id=shared, key="mrr", value="duplicate"),
            ContextFact(id=_id(), key="users", value="10"),
        ]
    )
    context = assemble_context(structured, [], _classification())
    assert [fact.value for fact in context.facts] == ["first", "10"]


def test_cross_section_overlap_remains_untouched() -> None:
    shared = _id()
    structured = CompanyContext(
        facts=[ContextFact(id=shared, key="overlap", value="fact")],
        beliefs=[ContextBelief(id=shared, statement="belief")],
        evidence=[ContextEvidence(id=shared, title="evidence")],
    )
    context = assemble_context(structured, [], _classification())
    assert context.facts[0].id == shared
    assert context.beliefs[0].id == shared
    assert context.evidence[0].id == shared


def test_facts_beliefs_evidence_memories_remain_separate() -> None:
    structured = CompanyContext(
        facts=[ContextFact(id=_id(), key="known", value="12")],
        beliefs=[ContextBelief(id=_id(), statement="we believe")],
        evidence=[ContextEvidence(id=_id(), content="quote")],
    )
    hits = [
        VectorHit(memory_id=str(_id()), content="semantic note", source_type="founder_input")
    ]
    context = assemble_context(structured, hits, _classification())
    assert "knowledge" not in CompanyContext.model_fields
    assert context.facts[0].key == "known"
    assert context.beliefs[0].statement == "we believe"
    assert context.evidence[0].content == "quote"
    assert context.memories[0].content == "semantic note"
    assert not hasattr(context.facts[0], "statement") or "statement" not in ContextFact.model_fields
    assert "key" not in ContextBelief.model_fields
    assert "key" not in ContextMemory.model_fields


def test_no_vector_results_still_produces_valid_context() -> None:
    structured = CompanyContext(
        company=ContextCompany(name="Sparse Co"),
        facts=[ContextFact(key="stage", value="mvp")],
    )
    context = assemble_context(structured, None, _classification())
    assert context.company is not None
    assert context.facts[0].value == "mvp"
    assert context.memories == []
    assert context.meta is not None
    assert "memories" in context.meta.sections_empty


def test_provenance_is_preserved() -> None:
    provenance = Provenance(
        source_type="analytics",
        source_reference="mixpanel",
        observed_at="2026-08-22T00:00:00Z",
    )
    structured = CompanyContext(
        facts=[
            ContextFact(id=_id(), key="mrr", value="12000", confidence=0.95, provenance=provenance)
        ]
    )
    created = datetime(2026, 8, 1, tzinfo=UTC)
    memory_id = _id()
    context = assemble_context(
        structured,
        [
            VectorHit(
                memory_id=str(memory_id),
                content="note",
                source_type="founder_input",
                source_reference="doc-1",
                created_at=created,
            )
        ],
        _classification(),
    )
    assert context.facts[0].provenance == provenance
    assert context.facts[0].confidence == 0.95
    assert context.memories[0].id == memory_id
    assert context.memories[0].created_at == created
    assert context.memories[0].provenance is not None
    assert context.memories[0].provenance.source_type == "founder_input"
    assert context.memories[0].provenance.source_reference == "doc-1"
    fact_source = next(source for source in context.sources if source.entity_type == "fact")
    assert fact_source.source_type == "analytics"
    assert fact_source.entity_id == str(context.facts[0].id)


def test_caps_are_applied_after_ordering() -> None:
    extras = MAX_FACTS + 3
    structured = CompanyContext(
        facts=[
            ContextFact(id=_id(), key=f"k{index}", value=str(index))
            for index in range(extras)
        ]
    )
    context = assemble_context(structured, [], _classification())
    assert [fact.value for fact in context.facts] == [str(index) for index in range(MAX_FACTS)]
    assert len(context.facts) == MAX_FACTS


def test_no_invented_content() -> None:
    context = assemble_context(None, [], None)
    assert context.company is None
    assert context.objective is None
    assert context.bottleneck is None
    dumped = context.model_dump()
    for section in (
        "constraints",
        "facts",
        "beliefs",
        "evidence",
        "decisions",
        "experiments",
        "learnings",
        "memories",
        "sources",
    ):
        assert dumped[section] == []
    text = str(dumped)
    assert "unknown" not in text.lower()
    assert "placeholder" not in text.lower()
    assert "no data" not in text.lower()
    assert context.meta is not None
    assert context.meta.classification is None
    assert context.meta.query is None
