from __future__ import annotations

import copy
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.company import Company
from app.models.onboarding_draft import STATUS_DRAFT, OnboardingDraft
from app.models.user import User

DEFAULT_PAYLOAD: dict[str, Any] = {
    "company": {},
    "customer": {},
    "current_situation": {},
    "context": {},
    "ai_suggestion": None,
}


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge patch into base without dropping unrelated keys."""
    merged = copy.deepcopy(base)
    for key, value in patch.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = deep_merge(existing, value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


async def get_draft(db: AsyncSession, company_id: uuid.UUID) -> OnboardingDraft | None:
    result = await db.execute(
        select(OnboardingDraft).where(OnboardingDraft.company_id == company_id)
    )
    return result.scalar_one_or_none()


def _initial_payload_from_company(company: Company | None) -> dict[str, Any]:
    payload = copy.deepcopy(DEFAULT_PAYLOAD)
    if company is None:
        return payload
    payload["company"] = {
        "name": company.name or "",
        "product_description": company.product_description or "",
        "stage": company.stage or "mvp",
    }
    payload["customer"] = {
        "target_customer": company.target_customer or "",
    }
    return payload


async def get_or_create_draft(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[OnboardingDraft, bool]:
    """Return the onboarding draft, creating one from company fields when missing."""
    draft = await get_draft(db, company_id)
    if draft is not None:
        return draft, False

    company = await db.get(Company, company_id)
    draft = OnboardingDraft(
        company_id=company_id,
        created_by_user_id=user_id,
        payload=_initial_payload_from_company(company),
        current_step=1,
        status=STATUS_DRAFT,
    )
    db.add(draft)
    await db.commit()
    await db.refresh(draft)
    return draft, True


async def patch_draft(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    user: User,
    payload: dict[str, Any] | None,
    current_step: int | None,
    status: str | None,
) -> OnboardingDraft:
    draft = await get_draft(db, company_id)
    if draft is None:
        draft = OnboardingDraft(
            company_id=company_id,
            created_by_user_id=user.id,
            payload=copy.deepcopy(DEFAULT_PAYLOAD),
            current_step=1,
            status=STATUS_DRAFT,
        )
        db.add(draft)
        await db.flush()

    if payload is not None:
        draft.payload = deep_merge(draft.payload or {}, payload)
        flag_modified(draft, "payload")
    if current_step is not None:
        draft.current_step = current_step
    if status is not None:
        draft.status = status

    await db.commit()
    await db.refresh(draft)
    return draft
