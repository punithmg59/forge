"""Company Brain context contract. Assembly is implemented in later Task 5 stages."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_BRAIN_QUERY_LENGTH = 4000


class BrainContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=MAX_BRAIN_QUERY_LENGTH)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Query must not be empty")
        return stripped


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: str | None = None
    source_reference: str | None = None
    observed_at: str | None = None


class RetrievalMeta(BaseModel):
    """How context was produced. Classifier/ranking details come later."""

    model_config = ConfigDict(extra="forbid")

    query: str | None = None
    classification: str | None = None
    assembled_at: datetime | None = None
    sections_empty: list[str] = Field(default_factory=list)
    structured_used: bool = False
    vector_used: bool = False
    retrieved_at: datetime | None = None


class ContextCompany(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID | None = None
    name: str | None = None
    slug: str | None = None
    stage: str | None = None
    mission: str | None = None
    product_description: str | None = None


class ContextObjective(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID | None = None
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


class ContextConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID | None = None
    type: str | None = None
    name: str | None = None
    description: str | None = None
    value: str | None = None
    severity: str | None = None
    status: str | None = None
    provenance: Provenance | None = None


class ContextFact(BaseModel):
    """Confirmed or measured company knowledge. Never merge with beliefs."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID | None = None
    key: str | None = None
    value: str | None = None
    value_type: str | None = None
    confidence: float | None = None
    status: str | None = None
    provenance: Provenance | None = None


class ContextBelief(BaseModel):
    """Founder or working hypothesis. Never treated as a confirmed fact."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID | None = None
    statement: str | None = None
    reasoning: str | None = None
    confidence: float | None = None
    status: str | None = None
    provenance: Provenance | None = None


class ContextDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID | None = None
    title: str | None = None
    decision: str | None = None
    rationale: str | None = None
    status: str | None = None
    provenance: Provenance | None = None


class ContextExperiment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID | None = None
    name: str | None = None
    description: str | None = None
    status: str | None = None
    provenance: Provenance | None = None


class ContextLearning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID | None = None
    statement: str | None = None
    evidence_summary: str | None = None
    confidence: float | None = None
    status: str | None = None
    provenance: Provenance | None = None


class ContextMemory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID | None = None
    memory_type: str | None = None
    content: str | None = None
    importance: float | None = None
    confidence: float | None = None
    created_at: datetime | None = None
    provenance: Provenance | None = None


class ContextEvidence(BaseModel):
    """Observed evidence. Never merged into facts, beliefs, or memories."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID | None = None
    type: str | None = None
    title: str | None = None
    content: str | None = None
    confidence: float | None = None
    created_at: datetime | None = None
    provenance: Provenance | None = None


class ContextSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: str | None = None
    entity_id: str | None = None
    source_type: str | None = None
    source_reference: str | None = None
    title: str | None = None


class CompanyContext(BaseModel):
    """Assembled Company Brain snapshot. Sparse/empty brains are valid.

    Facts and beliefs stay in separate sections. There is no merged knowledge list.
    """

    model_config = ConfigDict(extra="forbid")

    company: ContextCompany | None = None
    objective: ContextObjective | None = None
    bottleneck: str | None = None
    constraints: list[ContextConstraint] = Field(default_factory=list)
    facts: list[ContextFact] = Field(default_factory=list)
    beliefs: list[ContextBelief] = Field(default_factory=list)
    evidence: list[ContextEvidence] = Field(default_factory=list)
    decisions: list[ContextDecision] = Field(default_factory=list)
    experiments: list[ContextExperiment] = Field(default_factory=list)
    learnings: list[ContextLearning] = Field(default_factory=list)
    memories: list[ContextMemory] = Field(default_factory=list)
    sources: list[ContextSource] = Field(default_factory=list)
    meta: RetrievalMeta | None = None

    @field_validator(
        "constraints",
        "facts",
        "beliefs",
        "evidence",
        "decisions",
        "experiments",
        "learnings",
        "memories",
        "sources",
        mode="before",
    )
    @classmethod
    def null_sections_become_empty(cls, value: object) -> object:
        return [] if value is None else value


class BrainQueryMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    model: str | None = None
    classification: str | None = None
    context_sections_empty: list[str] = Field(default_factory=list)
    source_count: int = 0


class BrainQueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    sources: list[ContextSource] = Field(default_factory=list)
    meta: BrainQueryMeta

    @classmethod
    def from_context(
        cls,
        *,
        answer: str,
        context: CompanyContext,
        model: str | None,
        question: str,
    ) -> BrainQueryResponse:
        retrieval_meta = context.meta
        return cls(
            answer=answer,
            sources=list(context.sources),
            meta=BrainQueryMeta(
                query=question,
                model=model,
                classification=(
                    None if retrieval_meta is None else retrieval_meta.classification
                ),
                context_sections_empty=(
                    [] if retrieval_meta is None else list(retrieval_meta.sections_empty)
                ),
                source_count=len(context.sources),
            ),
        )
