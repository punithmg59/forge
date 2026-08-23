from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_authenticated_user
from app.core.config import settings
from app.core.security import clear_session_cookie, set_session_cookie
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.auth import AuthUserResponse, LoginRequest, RegisterRequest, UserPublic
from app.services import auth_service
from app.services.auth_service import AuthError, DuplicateEmailError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthUserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthUserResponse:
    try:
        user, token = await auth_service.register_user(
            db,
            name=payload.name,
            email=str(payload.email),
            password=payload.password,
        )
    except DuplicateEmailError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from None
    set_session_cookie(response, token)
    return AuthUserResponse(user=UserPublic.model_validate(user))


@router.post("/login", response_model=AuthUserResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthUserResponse:
    try:
        user, token = await auth_service.login_user(
            db,
            email=str(payload.email),
            password=payload.password,
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.detail,
        ) from None
    set_session_cookie(response, token)
    return AuthUserResponse(user=UserPublic.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    session_token: Annotated[str | None, Cookie(alias=settings.session_cookie_name)] = None,
) -> None:
    await auth_service.logout_user(db, session_token)
    clear_session_cookie(response)


@router.get("/me", response_model=UserPublic)
async def me(user: Annotated[User, Depends(require_authenticated_user)]) -> UserPublic:
    return UserPublic.model_validate(user)
