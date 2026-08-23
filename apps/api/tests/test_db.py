from __future__ import annotations

import pytest
from sqlalchemy import text

from app.db import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    Vector,
    get_db,
)
from app.db.base import Base as BaseFromModule
from app.models import register_models


def test_db_public_imports() -> None:
    assert Base is BaseFromModule
    assert Vector.__name__ == "VECTOR"
    assert callable(get_db)


def test_db_mixins_are_typed() -> None:
    assert "id" in UUIDPrimaryKeyMixin.__annotations__
    assert "created_at" in TimestampMixin.__annotations__
    assert "updated_at" in TimestampMixin.__annotations__


def test_model_registration_is_idempotent() -> None:
    register_models()
    assert Base.metadata is not None


@pytest.mark.asyncio
async def test_database_connection(engine) -> None:
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        assert result.scalar() == 1
