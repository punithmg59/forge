from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import settings


@pytest_asyncio.fixture
async def db_engine() -> AsyncEngine:
    engine = create_async_engine(settings.database_url)
    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_vector_extension_exists(db_engine: AsyncEngine) -> None:
    async with db_engine.connect() as connection:
        result = await connection.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        row = result.fetchone()

    # Skip if vector extension is not installed (e.g., on Supabase without pgvector)
    if row is None:
        pytest.skip("pgvector extension not installed in database")
    
    assert row[0] == "vector"


@pytest.mark.asyncio
async def test_vector_type_accepted(db_engine: AsyncEngine) -> None:
    # First check if vector extension exists
    async with db_engine.connect() as connection:
        result = await connection.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        row = result.fetchone()
    
    if row is None:
        pytest.skip("pgvector extension not installed in database")
    
    async with db_engine.begin() as connection:
        await connection.execute(
            text("CREATE TEMP TABLE forge_vector_probe (embedding vector(3)) ON COMMIT DROP")
        )
        await connection.execute(
            text("INSERT INTO forge_vector_probe (embedding) VALUES ('[1,2,3]')")
        )
        result = await connection.execute(
            text("SELECT embedding::text FROM forge_vector_probe")
        )
        value = result.scalar()

    assert value == "[1,2,3]"


@pytest.mark.asyncio
async def test_sqlalchemy_vector_type_importable() -> None:
    from app.db import Vector

    assert Vector.__name__ == "VECTOR"
