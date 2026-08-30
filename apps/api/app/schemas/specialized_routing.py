"""Specialized agent routing contracts."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.head_agent import RecommendationConfidence
from app.schemas.specialized_agent import SpecializedAgentContext
from app.schemas.specialized_agent_types import AgentDomain, SpecializedAgentType
from app.schemas.specialized_routing_types import RoutingIntent

RoutingConfidence = RecommendationConfidence
RoutingMethod = Literal["deterministic", "llm", "fallback"]


class SpecializedRoutingDecision(BaseModel):
    """Typed routing result — which specialist should handle the question."""

    model_config = ConfigDict(extra="forbid")

    selected_agent: SpecializedAgentType | None = None
    domain: AgentDomain | None = None
    intent: RoutingIntent
    confidence: RoutingConfidence
    reason: str
    fallback_to_head_agent: bool
    routing_method: RoutingMethod
    matched_terms: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("reason must not be empty")
        return stripped


class SpecializedRoutingHandoff(BaseModel):
    """Routing decision plus optional domain context for the selected specialist."""

    model_config = ConfigDict(extra="forbid")

    decision: SpecializedRoutingDecision
    context: SpecializedAgentContext | None = None


class LlmRoutingClassification(BaseModel):
    """Validated LLM classifier output. Never used for code execution."""

    model_config = ConfigDict(extra="forbid")

    intent: RoutingIntent
    agent_type: SpecializedAgentType | None = None
    confidence: RoutingConfidence
    reason: str

    @field_validator("agent_type", mode="before")
    @classmethod
    def normalize_agent_type(cls, value: object) -> object:
        if value is None or value == "none" or value == "":
            return None
        return value

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("reason must not be empty")
        return stripped


class DeterministicRoutingStatus(str, Enum):
    STRONG_MATCH = "strong_match"
    WEAK_MATCH = "weak_match"
    AMBIGUOUS = "ambiguous"
    NO_MATCH = "no_match"


class DeterministicRoutingResult(BaseModel):
    """Internal deterministic routing outcome."""

    model_config = ConfigDict(extra="forbid")

    status: DeterministicRoutingStatus
    decision: SpecializedRoutingDecision | None = None
