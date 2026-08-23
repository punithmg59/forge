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
    payload: dict[str, Any] | None = None
    current_step: int | None = Field(
        default=None, ge=MIN_ONBOARDING_STEP, le=MAX_ONBOARDING_STEP
    )
    status: str | None = None

    @field_validator("payload")
    @classmethod
    def payload_is_object(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
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
