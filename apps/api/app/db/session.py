from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

_engine_kwargs: dict = {"pool_pre_ping": True}
if settings.app_env == "production":
    _engine_kwargs.update({"pool_size": 5, "max_overflow": 10})
else:
    # TestClient closes its event loop after each request; a queue pool
    # would reuse connections bound to a dead loop.
    _engine_kwargs["poolclass"] = NullPool

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    **_engine_kwargs,
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
