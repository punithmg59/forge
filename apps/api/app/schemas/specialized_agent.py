"""Specialized agent contracts. Proposals only — never Company Brain truth."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.brain import (
    ContextBelief,
    ContextCompany,
    ContextConstraint,
    ContextDecision,
    ContextEvidence,
    ContextFact,
    ContextLearning,
    ContextObjective,
    ContextSource,
    RetrievalMeta,
)
from app.schemas.head_agent import (
    ProposedAction,
    RecommendationConfidence,
)
from app.schemas.specialized_agent_types import AgentDomain, SpecializedAgentType
from app.services.retrieval.scope import RetrievalScope

MAX_SPECIALIZED_AGENT_QUESTION_LENGTH = 4000


class SpecializedAgentContext(BaseModel):
    """Domain-scoped Company Brain snapshot for specialist reasoning.

    Built from CompanyContext — not a second Brain. Domain filtering is added in Task 9.3+.
    """

    model_config = ConfigDict(extra="forbid")

    scope: RetrievalScope
    domain: AgentDomain
    company: ContextCompany | None = None
    objective: ContextObjective | None = None
    constraints: list[ContextConstraint] = Field(default_factory=list)
    facts: list[ContextFact] = Field(default_factory=list)
    beliefs: list[ContextBelief] = Field(default_factory=list)
    decisions: list[ContextDecision] = Field(default_factory=list)
    evidence: list[ContextEvidence] = Field(default_factory=list)
    learnings: list[ContextLearning] = Field(default_factory=list)
    sources: list[ContextSource] = Field(default_factory=list)
    meta: RetrievalMeta | None = None

    @field_validator(
        "constraints",
        "facts",
        "beliefs",
        "decisions",
        "evidence",
        "learnings",
        "sources",
        mode="before",
    )
    @classmethod
    def null_sections_become_empty(cls, value: object) -> object:
        return [] if value is None else value


class SpecializedAgentRecommendation(BaseModel):
    """Structured specialist proposal. Not a fact, belief, decision, or learning."""

    model_config = ConfigDict(extra="forbid")

    title: str
    recommendation: str
    rationale: str
    proposed_action: ProposedAction
    sources: list[ContextSource] = Field(default_factory=list)
    confidence: RecommendationConfidence


class SpecializedAgentRecommendResponse(BaseModel):
    """Specialist recommendation plus audit references when persisted."""

    model_config = ConfigDict(extra="forbid")

    agent_type: SpecializedAgentType
    domain: AgentDomain
    agent_task_id: uuid.UUID | None = None
    recommendation: SpecializedAgentRecommendation


class SpecializedAgentRecommendRequest(BaseModel):
    """Future specialist execution input."""

    model_config = ConfigDict(extra="forbid")

    question: str | None = Field(default=None, max_length=MAX_SPECIALIZED_AGENT_QUESTION_LENGTH)

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None
