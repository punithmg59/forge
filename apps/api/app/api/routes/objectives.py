from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_authenticated_user, require_company_access, require_company_role
from app.db.dependencies import get_db
from app.models.company_member import CompanyMember
from app.models.user import User
from app.schemas.objective import (
    ObjectiveCreateRequest,
    ObjectiveListResponse,
    ObjectivePublic,
    ObjectiveUpdateRequest,
)
from app.services import objective_service
from app.services.company_service import COMPANY_MANAGE_ROLES
from app.services.objective_service import ObjectiveError

router = APIRouter(
    prefix="/companies/{company_id}/objectives",
    tags=["objectives"],
)


@router.post("", response_model=ObjectivePublic, status_code=status.HTTP_201_CREATED)
async def create_objective(
    company_id: uuid.UUID,
    payload: ObjectiveCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_authenticated_user)],
    _membership: Annotated[CompanyMember, Depends(require_company_role(*COMPANY_MANAGE_ROLES))],
) -> ObjectivePublic:
    try:
        objective = await objective_service.create_objective(
            db,
            company_id=company_id,
            user=user,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            target_value=payload.target_value,
            target_unit=payload.target_unit,
            deadline=payload.deadline,
        )
    except ObjectiveError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return ObjectivePublic.from_objective(objective)


@router.get("", response_model=ObjectiveListResponse)
async def list_objectives(
    company_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> ObjectiveListResponse:
    objectives = await objective_service.list_objectives(db, company_id=company_id)
    current = objective_service.select_current_objective(objectives)
    return ObjectiveListResponse(
        objectives=[ObjectivePublic.from_objective(item) for item in objectives],
        current_objective=ObjectivePublic.from_objective(current) if current else None,
    )


@router.get("/{objective_id}", response_model=ObjectivePublic)
async def get_objective(
    company_id: uuid.UUID,
    objective_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> ObjectivePublic:
    objective = await objective_service.get_objective(
        db,
        company_id=company_id,
        objective_id=objective_id,
    )
    if objective is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Objective not found",
        )
    return ObjectivePublic.from_objective(objective)


@router.patch("/{objective_id}", response_model=ObjectivePublic)
async def update_objective(
    company_id: uuid.UUID,
    objective_id: uuid.UUID,
    payload: ObjectiveUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership: Annotated[CompanyMember, Depends(require_company_role(*COMPANY_MANAGE_ROLES))],
) -> ObjectivePublic:
    objective = await objective_service.get_objective(
        db,
        company_id=company_id,
        objective_id=objective_id,
    )
    if objective is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Objective not found",
        )
    try:
        updated = await objective_service.update_objective(
            db,
            objective,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            priority=payload.priority,
            target_value=payload.target_value,
            target_unit=payload.target_unit,
            deadline=payload.deadline,
        )
    except ObjectiveError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return ObjectivePublic.from_objective(updated)
