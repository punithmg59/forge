from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_session_token, hash_session_token, session_expiry, utcnow
from app.models.session import Session


async def create_session(db: AsyncSession, user_id) -> tuple[Session, str]:
    raw_token = generate_session_token()
    now = utcnow()
    session = Session(
        user_id=user_id,
        token_hash=hash_session_token(raw_token),
        expires_at=session_expiry(now),
        created_at=now,
        last_used_at=now,
        revoked_at=None,
    )
    db.add(session)
    await db.flush()
    return session, raw_token


async def get_session_by_token(db: AsyncSession, token: str) -> Session | None:
    token_hash = hash_session_token(token)
    result = await db.execute(select(Session).where(Session.token_hash == token_hash))
    return result.scalar_one_or_none()


def is_session_active(session: Session, now: datetime | None = None) -> bool:
    current = now or utcnow()
    if session.revoked_at is not None:
        return False
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=current.tzinfo)
    return expires_at > current


async def get_valid_session(db: AsyncSession, token: str) -> Session | None:
    session = await get_session_by_token(db, token)
    if session is None or not is_session_active(session):
        return None
    session.last_used_at = utcnow()
    await db.flush()
    return session


async def revoke_session(db: AsyncSession, session: Session) -> None:
    if session.revoked_at is None:
        session.revoked_at = utcnow()
        await db.flush()
