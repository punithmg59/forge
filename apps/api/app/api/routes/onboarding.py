from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_authenticated_user, require_company_access, require_company_role
from app.db.dependencies import get_db
from app.models.company_member import CompanyMember
from app.models.user import User
from app.schemas.onboarding import OnboardingDraftPatchRequest, OnboardingDraftPublic
from app.schemas.onboarding_confirm import OnboardingConfirmResponse
from app.schemas.onboarding_structure import OnboardingStructureResponse
from app.services import onboarding_service
from app.services.company_service import COMPANY_MANAGE_ROLES
from app.services.onboarding_confirm import ConfirmError, confirm_onboarding
from app.services.onboarding_structure import StructureError, structure_onboarding_draft

router = APIRouter(
    prefix="/companies/{company_id}/onboarding",
    tags=["onboarding"],
)


@router.get("/draft", response_model=OnboardingDraftPublic)
async def get_onboarding_draft(
    company_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> OnboardingDraftPublic:
    draft, _created = await onboarding_service.get_or_create_draft(
        db,
        company_id=company_id,
        user_id=membership.user_id,
    )
    return OnboardingDraftPublic.model_validate(draft)


@router.patch("/draft", response_model=OnboardingDraftPublic)
async def patch_onboarding_draft(
    company_id: uuid.UUID,
    payload: OnboardingDraftPatchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_authenticated_user)],
    _membership: Annotated[CompanyMember, Depends(require_company_role(*COMPANY_MANAGE_ROLES))],
) -> OnboardingDraftPublic:
    draft = await onboarding_service.patch_draft(
        db,
        company_id=company_id,
        user=user,
        payload=payload.payload,
        current_step=payload.current_step,
        status=payload.status,
    )
    return OnboardingDraftPublic.model_validate(draft)


@router.post("/confirm", response_model=OnboardingConfirmResponse)
async def confirm_onboarding_draft(
    company_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_authenticated_user)],
    _membership: Annotated[CompanyMember, Depends(require_company_role(*COMPANY_MANAGE_ROLES))],
) -> OnboardingConfirmResponse:
    try:
        draft = await confirm_onboarding(db, company_id=company_id, user=user)
    except ConfirmError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return OnboardingConfirmResponse(
        draft=OnboardingDraftPublic.model_validate(draft),
        brain_initialized=True,
    )


@router.post("/structure", response_model=OnboardingStructureResponse)
async def structure_onboarding(
    company_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(require_authenticated_user)],
    _membership: Annotated[CompanyMember, Depends(require_company_role(*COMPANY_MANAGE_ROLES))],
) -> OnboardingStructureResponse:
    try:
        draft, suggestion, error = await structure_onboarding_draft(
            db, company_id=company_id
        )
    except StructureError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND
            if "not found" in exc.detail.lower()
            else status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from None
    return OnboardingStructureResponse(
        draft=OnboardingDraftPublic.model_validate(draft),
        structured=suggestion is not None,
        error=error,
        suggestion=suggestion.model_dump(mode="json") if suggestion else None,
    )
