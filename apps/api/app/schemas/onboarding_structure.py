"""Strict schemas for optional AI onboarding structuring."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.onboarding import OnboardingDraftPublic
from app.schemas.onboarding_confirm import ALLOWED_CONSTRAINT_TYPES, ALLOWED_STAGES


class SuggestedFact(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=2000)
    value_type: str = Field(default="string", max_length=50)


class SuggestedConstraint(BaseModel):
    type: str = Field(default="other", max_length=50)
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    value: str | None = Field(default=None, max_length=500)
    severity: str = Field(default="medium", max_length=50)

    @field_validator("type")
    @classmethod
    def normalize_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_CONSTRAINT_TYPES:
            return "other"
        return normalized


class SuggestedCompany(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    product_description: str | None = Field(default=None, max_length=4000)
    stage: str | None = Field(default=None, max_length=100)
    mission: str | None = Field(default=None, max_length=2000)

    @field_validator("stage")
    @classmethod
    def normalize_stage(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized not in ALLOWED_STAGES:
            raise ValueError("stage must be one of: idea, mvp, growth, scale")
        return normalized


class SuggestedCustomer(BaseModel):
    target_customer: str | None = Field(default=None, max_length=2000)
    problem: str | None = Field(default=None, max_length=4000)
    beliefs: list[str] = Field(default_factory=list)
    facts: list[SuggestedFact] = Field(default_factory=list)


class SuggestedCurrentSituation(BaseModel):
    objective: str | None = Field(default=None, max_length=500)
    bottleneck: str | None = Field(default=None, max_length=2000)
    deadline: str | None = Field(default=None, max_length=100)
    constraints: list[SuggestedConstraint] = Field(default_factory=list)


class SuggestedContext(BaseModel):
    mission: str | None = Field(default=None, max_length=2000)
    non_goals: str | None = Field(default=None, max_length=4000)
    strategy: str | None = Field(default=None, max_length=4000)
    working_style: str | None = Field(default=None, max_length=2000)


class OnboardingAISuggestion(BaseModel):
    """Structured suggestion produced from founder-provided draft text only."""

    company: SuggestedCompany = Field(default_factory=SuggestedCompany)
    customer: SuggestedCustomer = Field(default_factory=SuggestedCustomer)
    current_situation: SuggestedCurrentSituation = Field(
        default_factory=SuggestedCurrentSituation
    )
    context: SuggestedContext = Field(default_factory=SuggestedContext)


class OnboardingStructureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    draft: OnboardingDraftPublic
    structured: bool
    error: str | None = None
    suggestion: dict[str, Any] | None = None
