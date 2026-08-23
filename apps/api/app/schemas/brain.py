"""Company Brain context contract. Assembly is implemented in later Task 5 stages."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: str | None = None
    source_reference: str | None = None
    observed_at: str | None = None


class RetrievalMeta(BaseModel):
    """How context was produced. Classifier/ranking details come later."""

    model_config = ConfigDict(extra="forbid")

    query: str | None = None
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
    provenance: Provenance | None = None


class ContextSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
