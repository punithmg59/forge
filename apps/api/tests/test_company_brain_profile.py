"""Test Company Brain Profile model."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.company import Company
from app.models.company_brain_profile import CompanyBrainProfile


@pytest.mark.asyncio
async def test_profile_can_be_created(async_session_factory) -> None:
    """Test that a company brain profile can be created."""
    async with async_session_factory() as session:
        company = Company()
        session.add(company)
        await session.flush()

        profile = CompanyBrainProfile(
            company_id=company.id,
            strategy="Growth through product innovation",
            non_goals="Enterprise sales, B2B partnerships",
            current_priorities="User acquisition, product stability",
            current_bottlenecks="Limited engineering bandwidth",
            working_style="Agile with weekly sprints",
            version=1,
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

        assert profile.id is not None
        assert profile.company_id == company.id
        assert profile.strategy == "Growth through product innovation"
        assert profile.version == 1


@pytest.mark.asyncio
async def test_profile_defaults_version_to_1(async_session_factory) -> None:
    """Test that profile version defaults to 1."""
    async with async_session_factory() as session:
        company = Company()
        session.add(company)
        await session.flush()

        profile = CompanyBrainProfile(
            company_id=company.id,
            strategy="Test strategy",
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

        assert profile.version == 1


@pytest.mark.asyncio
async def test_profile_nullable_fields(async_session_factory) -> None:
    """Test that profile fields can be nullable."""
    async with async_session_factory() as session:
        company = Company()
        session.add(company)
        await session.flush()

        profile = CompanyBrainProfile(
            company_id=company.id,
            version=1,
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

        assert profile.strategy is None
        assert profile.non_goals is None
        assert profile.current_priorities is None
        assert profile.current_bottlenecks is None
        assert profile.working_style is None


@pytest.mark.asyncio
async def test_company_can_only_have_one_profile(async_session_factory) -> None:
    """Test that a company can only have one active brain profile."""
    # Create company and first profile
    async with async_session_factory() as session:
        company = Company()
        session.add(company)
        await session.flush()

        profile1 = CompanyBrainProfile(
            company_id=company.id,
            strategy="First strategy",
            version=1,
        )
        session.add(profile1)
        await session.commit()
        company_id = company.id

    # Try to create a second profile for the same company in a new session
    async with async_session_factory() as session:
        profile2 = CompanyBrainProfile(
            company_id=company_id,
            strategy="Second strategy",
            version=1,
        )
        session.add(profile2)

        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_company_deletion_cascades_to_profile(async_session_factory) -> None:
    """Test that deleting a company also deletes its brain profile."""
    async with async_session_factory() as session:
        company = Company()
        session.add(company)
        await session.flush()

        profile = CompanyBrainProfile(
            company_id=company.id,
            strategy="Test strategy",
            version=1,
        )
        session.add(profile)
        await session.commit()

        profile_id = profile.id
        company_id = company.id

        # Delete the company using raw SQL to trigger database-level cascade
        await session.execute(
            text("DELETE FROM companies WHERE id = :company_id"),
            {"company_id": company_id},
        )
        await session.commit()

        # Verify profile is also deleted (cascade worked)
        result = await session.execute(
            text("SELECT id FROM company_brain_profiles WHERE id = :profile_id"),
            {"profile_id": profile_id},
        )
        assert result.fetchone() is None

        # Verify company is deleted
        result = await session.execute(
            text("SELECT id FROM companies WHERE id = :company_id"),
            {"company_id": company_id},
        )
        assert result.fetchone() is None
