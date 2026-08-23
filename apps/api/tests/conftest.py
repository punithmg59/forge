"""Pytest configuration and fixtures for async tests."""

from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


@pytest.fixture(scope="function")
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create async engine for each test function."""
    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def async_session_factory(
    engine: AsyncEngine,
) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    """Create async session factory for each test."""
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    yield factory
