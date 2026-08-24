"""Head Agent recommendation contracts. Proposals only — not Brain updates."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.brain import ContextSource

MAX_HEAD_AGENT_QUESTION_LENGTH = 4000

ProposedActionType = Literal["task", "objective_change", "none"]
RecommendationConfidence = Literal["low", "medium", "high"]


class HeadAgentRecommendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str | None = Field(default=None, max_length=MAX_HEAD_AGENT_QUESTION_LENGTH)

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ProposedAction(BaseModel):
    """A proposed next step. The Head Agent never executes this."""

    model_config = ConfigDict(extra="forbid")

    type: ProposedActionType
    title: str = ""
    description: str = ""


class HeadAgentRecommendation(BaseModel):
    """Structured Head Agent proposal. Not a fact, belief, or decision."""

    model_config = ConfigDict(extra="forbid")

    title: str
    recommendation: str
    rationale: str
    proposed_action: ProposedAction
    sources: list[ContextSource] = Field(default_factory=list)
    confidence: RecommendationConfidence


class HeadAgentRecommendResponse(BaseModel):
    """Head Agent recommendation plus the persisted proposal reference."""

    model_config = ConfigDict(extra="forbid")

    agent_task_id: uuid.UUID | None = None
    recommendation: HeadAgentRecommendation
