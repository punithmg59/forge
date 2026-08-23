"""Optional AI structuring for onboarding drafts (draft-only writes)."""

from __future__ import annotations

import copy
import json
import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.onboarding_draft import STATUS_STRUCTURED, OnboardingDraft
from app.schemas.onboarding_structure import OnboardingAISuggestion
from app.services import onboarding_service
from app.services.llm_client import STRUCTURE_SYSTEM_PROMPT, LLMError, complete_json

FOUNDER_INPUT_SECTIONS = (
    "company",
    "customer",
    "current_situation",
    "context",
)


class StructureError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def _founder_input_for_llm(payload: dict[str, Any]) -> dict[str, Any]:
    """Send only founder-authored sections; never send prior AI suggestions."""
    return {
        key: copy.deepcopy(payload.get(key) or {})
        for key in FOUNDER_INPUT_SECTIONS
    }


async def structure_onboarding_draft(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
) -> tuple[OnboardingDraft, OnboardingAISuggestion | None, str | None]:
    """Structure founder draft text into a suggestion stored only on the draft.

    Returns (draft, suggestion_or_none, error_or_none).
    On AI failure the original draft is preserved and returned unchanged.
    """
    draft = await onboarding_service.get_draft(db, company_id)
    if draft is None:
        raise StructureError("Onboarding draft not found")

    if draft.status == "confirmed":
        raise StructureError("Confirmed onboarding cannot be restructured")

    founder_input = _founder_input_for_llm(draft.payload or {})
    user_prompt = json.dumps(founder_input, ensure_ascii=True)

    try:
        raw = await complete_json(
            system_prompt=STRUCTURE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        suggestion = OnboardingAISuggestion.model_validate(raw)
    except LLMError as exc:
        return draft, None, str(exc)
    except ValidationError:
        return draft, None, "AI output did not match the required schema"

    payload = copy.deepcopy(draft.payload or {})
    payload["ai_suggestion"] = suggestion.model_dump(mode="json")
    draft.payload = payload
    draft.status = STATUS_STRUCTURED
    flag_modified(draft, "payload")
    await db.commit()
    await db.refresh(draft)
    return draft, suggestion, None
