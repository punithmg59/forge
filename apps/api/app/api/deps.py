from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.dependencies import get_db
from app.models.company_member import CompanyMember
from app.models.user import User
from app.services import company_service, session_service

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    session_token: Annotated[str | None, Cookie(alias=settings.session_cookie_name)] = None,
) -> User | None:
    if not session_token:
        return None
    session = await session_service.get_valid_session(db, session_token)
    if session is None:
        return None
    user = await db.get(User, session.user_id)
    if user is None:
        return None
    await db.commit()
    return user


async def require_authenticated_user(
    user: Annotated[User | None, Depends(get_current_user)],
) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


async def get_company_membership(
    db: DbSession,
    user: Annotated[User, Depends(require_authenticated_user)],
    company_id: Annotated[uuid.UUID, Path()],
) -> CompanyMember:
    membership = await company_service.get_membership(
        db, user_id=user.id, company_id=company_id
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this company",
        )
    return membership


async def require_company_access(
    membership: Annotated[CompanyMember, Depends(get_company_membership)],
) -> CompanyMember:
    return membership


def require_company_role(*roles: str):
    allowed = frozenset(roles)

    async def _require_role(
        membership: Annotated[CompanyMember, Depends(require_company_access)],
    ) -> CompanyMember:
        if membership.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient company role",
            )
        return membership

    return _require_role
