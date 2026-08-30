from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_authenticated_user, require_company_access, require_company_role
from app.db.dependencies import get_db
from app.models.company_member import CompanyMember
from app.models.user import User
from app.schemas.learning import LearningCorrectRequest, LearningListResponse, LearningPublic
from app.services.company_service import COMPANY_MANAGE_ROLES
from app.services.learning_service import (
    LearningError,
    correct_learning,
    get_learning_for_company,
    learning_to_public,
    learnings_to_public,
    list_learnings,
)

router = APIRouter(
    prefix="/companies/{company_id}/learnings",
    tags=["learnings"],
)


@router.get("", response_model=LearningListResponse)
async def get_learnings(
    company_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> LearningListResponse:
    learnings = await list_learnings(db, company_id=company_id)
    return LearningListResponse(
        learnings=await learnings_to_public(db, learnings)
    )


@router.get("/{learning_id}", response_model=LearningPublic)
async def get_learning_by_id(
    company_id: uuid.UUID,
    learning_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> LearningPublic:
    learning = await get_learning_for_company(
        db,
        company_id=company_id,
        learning_id=learning_id,
    )
    if learning is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning not found")
    return await learning_to_public(db, learning)


@router.patch("/{learning_id}/correct", response_model=LearningPublic)
async def patch_correct_learning(
    company_id: uuid.UUID,
    learning_id: uuid.UUID,
    payload: LearningCorrectRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_authenticated_user)],
    _membership: Annotated[CompanyMember, Depends(require_company_role(*COMPANY_MANAGE_ROLES))],
) -> LearningPublic:
    learning = await get_learning_for_company(
        db,
        company_id=company_id,
        learning_id=learning_id,
    )
    if learning is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning not found")
    try:
        updated = await correct_learning(
            db,
            learning=learning,
            user=user,
            reason=payload.reason,
        )
    except LearningError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return await learning_to_public(db, updated)
