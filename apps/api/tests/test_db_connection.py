"""Test database connection and session management."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_session_creation(async_session_factory) -> None:
    """Test that async sessions can be created."""
    async with async_session_factory() as session:
        assert isinstance(session, AsyncSession)
        await session.close()
