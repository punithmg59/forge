from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_authenticated_user, require_company_access, require_company_role
from app.db.dependencies import get_db
from app.models.company_member import CompanyMember
from app.models.user import User
from app.schemas.company import (
    CompanyCreateRequest,
    CompanyMemberPublic,
    CompanyPublic,
    CompanyUpdateRequest,
)
from app.services import company_service
from app.services.company_service import COMPANY_MANAGE_ROLES

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyPublic])
async def list_companies(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_authenticated_user)],
) -> list[CompanyPublic]:
    companies = await company_service.list_companies_for_user(db, user.id)
    return [CompanyPublic.from_company(company) for company in companies]


@router.post("", response_model=CompanyPublic, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_authenticated_user)],
) -> CompanyPublic:
    company = await company_service.create_company(
        db,
        user=user,
        name=payload.name,
        description=payload.description,
        target_customer=payload.target_customer,
        stage=payload.stage,
    )
    return CompanyPublic.from_company(company)


@router.get("/{company_id}", response_model=CompanyPublic)
async def get_company(
    company_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> CompanyPublic:
    company = await company_service.get_company(db, company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this company",
        )
    return CompanyPublic.from_company(company)


@router.patch("/{company_id}", response_model=CompanyPublic)
async def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    membership: Annotated[CompanyMember, Depends(require_company_role(*COMPANY_MANAGE_ROLES))],
) -> CompanyPublic:
    company = await company_service.get_company(db, company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this company",
        )
    updated = await company_service.update_company(
        db,
        company,
        name=payload.name,
        description=payload.description,
        target_customer=payload.target_customer,
        stage=payload.stage,
    )
    return CompanyPublic.from_company(updated)


@router.get("/{company_id}/members", response_model=list[CompanyMemberPublic])
async def list_company_members(
    company_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> list[CompanyMemberPublic]:
    rows = await company_service.list_members(db, company_id)
    return [
        CompanyMemberPublic(
            id=member.id,
            user_id=member.user_id,
            role=member.role,
            email=user.email,
            name=user.name,
        )
        for member, user in rows
    ]
