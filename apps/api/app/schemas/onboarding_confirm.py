from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.onboarding import OnboardingDraftPublic

ALLOWED_STAGES = frozenset({"idea", "mvp", "growth", "scale"})
ALLOWED_CONSTRAINT_TYPES = frozenset(
    {"budget", "team_size", "time", "technical", "other"}
)


class OnboardingConfirmResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    draft: OnboardingDraftPublic
    brain_initialized: bool = True


def as_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
