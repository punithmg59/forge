from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AUTH_ERROR_DETAIL, hash_password, verify_password
from app.models.user import User
from app.services import session_service


class AuthError(Exception):
    def __init__(self, detail: str = AUTH_ERROR_DETAIL) -> None:
        self.detail = detail
        super().__init__(detail)


class DuplicateEmailError(Exception):
    pass


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def register_user(
    db: AsyncSession, *, name: str, email: str, password: str
) -> tuple[User, str]:
    normalized_email = email.lower()
    existing = await get_user_by_email(db, normalized_email)
    if existing is not None:
        raise DuplicateEmailError

    user = User(
        email=normalized_email,
        name=name,
        password_hash=hash_password(password),
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateEmailError from exc

    _, raw_token = await session_service.create_session(db, user.id)
    await db.commit()
    await db.refresh(user)
    return user, raw_token


async def login_user(db: AsyncSession, *, email: str, password: str) -> tuple[User, str]:
    user = await get_user_by_email(db, email.lower())
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError

    _, raw_token = await session_service.create_session(db, user.id)
    await db.commit()
    await db.refresh(user)
    return user, raw_token


async def logout_user(db: AsyncSession, token: str | None) -> None:
    if not token:
        await db.commit()
        return
    session = await session_service.get_session_by_token(db, token)
    if session is not None:
        await session_service.revoke_session(db, session)
    await db.commit()
