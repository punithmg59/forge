"""Database tests for onboarding_drafts."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.company import Company
from app.models.onboarding_draft import (
    STATUS_CONFIRMED,
    STATUS_DRAFT,
    OnboardingDraft,
)
from app.models.user import User


async def _create_user(session) -> User:
    user = User(email=f"draft-{uuid.uuid4()}@example.com", name="Draft Founder")
    session.add(user)
    await session.flush()
    return user


async def _create_company(session) -> Company:
    company = Company(
        name=f"Draft Co {uuid.uuid4()}",
        slug=f"draft-co-{uuid.uuid4()}",
    )
    session.add(company)
    await session.flush()
    return company


@pytest.mark.asyncio
async def test_draft_can_be_created(async_session_factory) -> None:
    async with async_session_factory() as session:
        user = await _create_user(session)
        company = await _create_company(session)

        draft = OnboardingDraft(
            company_id=company.id,
            created_by_user_id=user.id,
            payload={"company": {}, "customer": {}},
            current_step=1,
            status=STATUS_DRAFT,
        )
        session.add(draft)
        await session.commit()
        await session.refresh(draft)

        assert draft.id is not None
        assert draft.company_id == company.id
        assert draft.created_by_user_id == user.id
        assert draft.status == STATUS_DRAFT


@pytest.mark.asyncio
async def test_draft_belongs_to_company(async_session_factory) -> None:
    async with async_session_factory() as session:
        user = await _create_user(session)
        company = await _create_company(session)
        draft = OnboardingDraft(
            company_id=company.id,
            created_by_user_id=user.id,
            payload={},
            current_step=1,
            status=STATUS_DRAFT,
        )
        session.add(draft)
        await session.commit()

        result = await session.execute(
            text("SELECT company_id FROM onboarding_drafts WHERE id = :id"),
            {"id": draft.id},
        )
        row = result.fetchone()
        assert row is not None
        assert row.company_id == company.id


@pytest.mark.asyncio
async def test_company_id_is_unique(async_session_factory) -> None:
    async with async_session_factory() as session:
        user = await _create_user(session)
        company = await _create_company(session)
        session.add(
            OnboardingDraft(
                company_id=company.id,
                created_by_user_id=user.id,
                payload={},
                current_step=1,
                status=STATUS_DRAFT,
            )
        )
        await session.commit()
        company_id = company.id
        user_id = user.id

    async with async_session_factory() as session:
        duplicate = OnboardingDraft(
            company_id=company_id,
            created_by_user_id=user_id,
            payload={"company": {"name": "other"}},
            current_step=2,
            status=STATUS_DRAFT,
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_multiple_drafts_for_same_company_are_rejected(
    async_session_factory,
) -> None:
    async with async_session_factory() as session:
        user = await _create_user(session)
        company = await _create_company(session)
        session.add(
            OnboardingDraft(
                company_id=company.id,
                created_by_user_id=user.id,
                payload={},
                current_step=1,
                status=STATUS_DRAFT,
            )
        )
        session.add(
            OnboardingDraft(
                company_id=company.id,
                created_by_user_id=user.id,
                payload={},
                current_step=3,
                status=STATUS_DRAFT,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_draft_can_contain_jsonb_payload(async_session_factory) -> None:
    payload = {
        "company": {"name": "Forge", "stage": "mvp"},
        "customer": {"target_customer": "solo founders"},
        "current_situation": {"objective": "ship"},
        "context": {"mission": "help founders"},
        "ai_suggestion": None,
    }
    async with async_session_factory() as session:
        user = await _create_user(session)
        company = await _create_company(session)
        draft = OnboardingDraft(
            company_id=company.id,
            created_by_user_id=user.id,
            payload=payload,
            current_step=4,
            status=STATUS_DRAFT,
        )
        session.add(draft)
        await session.commit()
        await session.refresh(draft)

        assert draft.payload == payload
        assert draft.payload["company"]["name"] == "Forge"
        assert draft.payload["ai_suggestion"] is None


@pytest.mark.asyncio
async def test_current_step_persists(async_session_factory) -> None:
    async with async_session_factory() as session:
        user = await _create_user(session)
        company = await _create_company(session)
        draft = OnboardingDraft(
            company_id=company.id,
            created_by_user_id=user.id,
            payload={},
            current_step=3,
            status=STATUS_DRAFT,
        )
        session.add(draft)
        await session.commit()
        draft_id = draft.id

    async with async_session_factory() as session:
        stored = await session.get(OnboardingDraft, draft_id)
        assert stored is not None
        assert stored.current_step == 3


@pytest.mark.asyncio
async def test_status_persists(async_session_factory) -> None:
    async with async_session_factory() as session:
        user = await _create_user(session)
        company = await _create_company(session)
        draft = OnboardingDraft(
            company_id=company.id,
            created_by_user_id=user.id,
            payload={},
            current_step=5,
            status=STATUS_CONFIRMED,
        )
        session.add(draft)
        await session.commit()
        await session.refresh(draft)

        assert draft.status == STATUS_CONFIRMED


@pytest.mark.asyncio
async def test_confirmed_fields_are_nullable(async_session_factory) -> None:
    async with async_session_factory() as session:
        user = await _create_user(session)
        company = await _create_company(session)
        draft = OnboardingDraft(
            company_id=company.id,
            created_by_user_id=user.id,
            payload={},
            current_step=1,
            status=STATUS_DRAFT,
        )
        session.add(draft)
        await session.commit()
        await session.refresh(draft)

        assert draft.confirmed_at is None
        assert draft.confirmed_by_user_id is None


@pytest.mark.asyncio
async def test_company_deletion_cascades_to_draft(async_session_factory) -> None:
    async with async_session_factory() as session:
        user = await _create_user(session)
        company = await _create_company(session)
        draft = OnboardingDraft(
            company_id=company.id,
            created_by_user_id=user.id,
            payload={"company": {"name": "Gone"}},
            current_step=2,
            status=STATUS_DRAFT,
        )
        session.add(draft)
        await session.commit()
        draft_id = draft.id
        company_id = company.id

        await session.execute(
            text("DELETE FROM companies WHERE id = :company_id"),
            {"company_id": company_id},
        )
        await session.commit()

        result = await session.execute(
            text("SELECT id FROM onboarding_drafts WHERE id = :draft_id"),
            {"draft_id": draft_id},
        )
        assert result.fetchone() is None
