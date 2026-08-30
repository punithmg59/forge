from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_authenticated_user, require_company_access, require_company_role
from app.db.dependencies import get_db
from app.models.company_member import CompanyMember
from app.models.user import User
from app.schemas.approval import ApprovalCreateRequest, ApprovalListResponse, ApprovalPublic
from app.services.approval_presenter import approval_to_public, approvals_to_public
from app.services.approval_service import (
    ApprovalError,
    approve_approval,
    create_approval,
    create_learning_approval,
    get_approval,
    list_approvals,
    reject_approval,
)
from app.services.company_service import COMPANY_MANAGE_ROLES

router = APIRouter(
    prefix="/companies/{company_id}/approvals",
    tags=["approvals"],
)


@router.post("", response_model=ApprovalPublic, status_code=status.HTTP_201_CREATED)
async def post_approval(
    company_id: uuid.UUID,
    payload: ApprovalCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership: Annotated[CompanyMember, Depends(require_company_role(*COMPANY_MANAGE_ROLES))],
) -> ApprovalPublic:
    try:
        if payload.learning_id is not None:
            approval = await create_learning_approval(
                db,
                company_id=company_id,
                learning_id=payload.learning_id,
            )
        else:
            approval = await create_approval(
                db,
                company_id=company_id,
                agent_task_id=payload.agent_task_id,
            )
    except ApprovalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return await approval_to_public(db, approval)


@router.get("", response_model=ApprovalListResponse)
async def get_approvals(
    company_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> ApprovalListResponse:
    approvals = await list_approvals(db, company_id=company_id)
    return ApprovalListResponse(
        approvals=await approvals_to_public(db, approvals)
    )


@router.get("/{approval_id}", response_model=ApprovalPublic)
async def get_approval_by_id(
    company_id: uuid.UUID,
    approval_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> ApprovalPublic:
    approval = await get_approval(db, company_id=company_id, approval_id=approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found",
        )
    return await approval_to_public(db, approval)


@router.post("/{approval_id}/approve", response_model=ApprovalPublic)
async def post_approve_approval(
    company_id: uuid.UUID,
    approval_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_authenticated_user)],
    _membership: Annotated[CompanyMember, Depends(require_company_role(*COMPANY_MANAGE_ROLES))],
) -> ApprovalPublic:
    approval = await get_approval(db, company_id=company_id, approval_id=approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found",
        )
    try:
        updated, _objective_task = await approve_approval(db, approval=approval, user=user)
    except ApprovalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return await approval_to_public(db, updated)


@router.post("/{approval_id}/reject", response_model=ApprovalPublic)
async def post_reject_approval(
    company_id: uuid.UUID,
    approval_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_authenticated_user)],
    _membership: Annotated[CompanyMember, Depends(require_company_role(*COMPANY_MANAGE_ROLES))],
) -> ApprovalPublic:
    approval = await get_approval(db, company_id=company_id, approval_id=approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found",
        )
    try:
        updated = await reject_approval(db, approval=approval, user=user)
    except ApprovalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return await approval_to_public(db, updated)
