from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_PAYLOAD_KEYS = frozenset(
    {"company", "customer", "current_situation", "context", "ai_suggestion"}
)
MIN_ONBOARDING_STEP = 1
MAX_ONBOARDING_STEP = 5
ALLOWED_PATCH_STATUSES = frozenset({"draft", "structured"})

FLAT_PAYLOAD_ALIASES: dict[str, tuple[str, str]] = {
    "company_name": ("company", "name"),
    "name": ("company", "name"),
    "product_description": ("company", "product_description"),
    "stage": ("company", "stage"),
    "target_customer": ("customer", "target_customer"),
    "problem": ("customer", "problem"),
    "objective": ("current_situation", "objective"),
    "bottleneck": ("current_situation", "bottleneck"),
    "deadline": ("current_situation", "deadline"),
    "constraint": ("current_situation", "constraint"),
    "mission": ("context", "mission"),
    "vision": ("context", "non_goals"),
    "non_goals": ("context", "non_goals"),
}


def normalize_onboarding_payload_patch(payload: dict[str, Any]) -> dict[str, Any]:
    """Accept nested sections or common flat Swagger/manual keys."""
    if any(key in ALLOWED_PAYLOAD_KEYS for key in payload):
        return payload

    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        target = FLAT_PAYLOAD_ALIASES.get(key)
        if target is None:
            raise ValueError(f"Unsupported payload key: {key}")
        section, field = target
        normalized.setdefault(section, {})[field] = value
    return normalized


class OnboardingCompanyPatch(BaseModel):
    name: str | None = None
    product_description: str | None = None
    stage: str | None = None


class OnboardingCustomerPatch(BaseModel):
    target_customer: str | None = None
    problem: str | None = None
    beliefs: list[str] | None = None


class OnboardingCurrentSituationPatch(BaseModel):
    objective: str | None = None
    bottleneck: str | None = None
    deadline: str | None = None
    constraint: str | dict[str, Any] | None = None


class OnboardingContextPatch(BaseModel):
    mission: str | None = None
    non_goals: str | None = None


class OnboardingPayloadPatch(BaseModel):
    company: OnboardingCompanyPatch | None = None
    customer: OnboardingCustomerPatch | None = None
    current_situation: OnboardingCurrentSituationPatch | None = None
    context: OnboardingContextPatch | None = None
    ai_suggestion: dict[str, Any] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "company": {
                    "name": "Forge AI",
                    "product_description": "AI operating system for solo founders.",
                    "stage": "mvp",
                },
                "customer": {
                    "target_customer": "Technical solo founders",
                    "problem": "Operating a startup alone is overwhelming",
                },
                "current_situation": {
                    "objective": "Ship MVP",
                    "bottleneck": "Limited time",
                },
                "context": {
                    "mission": "Help solo founders build with AI leverage.",
                    "non_goals": "Not a generic chatbot",
                },
            }
        }
    )


class OnboardingDraftPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    payload: dict[str, Any]
    current_step: int
    status: str
    created_at: datetime
    updated_at: datetime


class OnboardingDraftPatchRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "payload": {
                    "company": {
                        "name": "Forge AI",
                        "product_description": "AI operating system for solo founders.",
                        "stage": "mvp",
                    },
                    "customer": {
                        "target_customer": "Technical solo founders",
                    },
                    "context": {
                        "mission": "Help solo founders build with AI leverage.",
                    },
                },
                "current_step": 1,
                "status": "draft",
            }
        }
    )

    payload: dict[str, Any] | OnboardingPayloadPatch | None = None
    current_step: int | None = Field(
        default=None, ge=MIN_ONBOARDING_STEP, le=MAX_ONBOARDING_STEP
    )
    status: str | None = None

    @field_validator("payload", mode="before")
    @classmethod
    def payload_is_object(cls, value: dict[str, Any] | OnboardingPayloadPatch | None) -> dict[str, Any] | None:
        if value is None:
            return value
        if isinstance(value, OnboardingPayloadPatch):
            value = value.model_dump(exclude_none=True)
        if not isinstance(value, dict):
            raise ValueError("payload must be an object")
        value = normalize_onboarding_payload_patch(value)
        for key, item in value.items():
            if key not in ALLOWED_PAYLOAD_KEYS:
                raise ValueError(f"Unsupported payload key: {key}")
            if key == "ai_suggestion":
                if item is not None and not isinstance(item, dict):
                    raise ValueError("ai_suggestion must be an object or null")
                continue
            if not isinstance(item, dict):
                raise ValueError(f"{key} must be an object")
        return value

    @field_validator("status")
    @classmethod
    def status_is_allowed(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in ALLOWED_PATCH_STATUSES:
            raise ValueError("Status must be draft or structured")
        return value
