from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_authenticated_user, require_company_access, require_company_role
from app.db.dependencies import get_db
from app.models.company_member import CompanyMember
from app.models.user import User
from app.schemas.objective_task import (
    ObjectiveTaskCompleteRequest,
    ObjectiveTaskDetailResponse,
    ObjectiveTaskListResponse,
    ObjectiveTaskPublic,
    ObjectiveTaskStatusRequest,
    ObjectiveTaskUpdateRequest,
)
from app.services import objective_task_service
from app.services.company_service import COMPANY_MANAGE_ROLES
from app.services.objective_task_service import ObjectiveTaskError

router = APIRouter(
    prefix="/companies/{company_id}/objective-tasks",
    tags=["objective-tasks"],
)


@router.get("", response_model=ObjectiveTaskListResponse)
async def list_objective_tasks(
    company_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> ObjectiveTaskListResponse:
    tasks = await objective_task_service.list_objective_tasks(db, company_id=company_id)
    return ObjectiveTaskListResponse(
        tasks=[ObjectiveTaskPublic.from_task(task) for task in tasks]
    )


@router.get("/{task_id}", response_model=ObjectiveTaskDetailResponse)
async def get_objective_task(
    company_id: uuid.UUID,
    task_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> ObjectiveTaskDetailResponse:
    detail = await objective_task_service.get_objective_task_detail(
        db,
        company_id=company_id,
        task_id=task_id,
    )
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return ObjectiveTaskDetailResponse.from_detail(detail)


@router.patch("/{task_id}", response_model=ObjectiveTaskPublic)
async def update_objective_task(
    company_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: ObjectiveTaskUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership: Annotated[CompanyMember, Depends(require_company_role(*COMPANY_MANAGE_ROLES))],
) -> ObjectiveTaskPublic:
    task = await objective_task_service.get_objective_task_for_company(
        db,
        company_id=company_id,
        task_id=task_id,
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    updated = await objective_task_service.update_objective_task(
        db,
        task=task,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
    )
    return ObjectiveTaskPublic.from_task(updated)


@router.post("/{task_id}/complete", response_model=ObjectiveTaskPublic)
async def complete_objective_task(
    company_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: ObjectiveTaskCompleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_authenticated_user)],
    _membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> ObjectiveTaskPublic:
    task = await objective_task_service.get_objective_task_for_company(
        db,
        company_id=company_id,
        task_id=task_id,
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    try:
        completed = await objective_task_service.complete_objective_task(
            db,
            task=task,
            user=user,
            result_summary=payload.result_summary,
            result_metrics=payload.result_metrics,
            result_notes=payload.result_notes,
        )
    except ObjectiveTaskError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None

    return ObjectiveTaskPublic.from_task(completed)


@router.patch("/{task_id}/status", response_model=ObjectiveTaskPublic)
async def patch_objective_task_status(
    company_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: ObjectiveTaskStatusRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_authenticated_user)],
    _membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> ObjectiveTaskPublic:
    try:
        updated = await objective_task_service.transition_objective_task_status(
            db,
            company_id=company_id,
            task_id=task_id,
            user=user,
            new_status=payload.status,
            blocked_reason=payload.blocked_reason,
            result_summary=payload.result_summary,
            result_metrics=payload.result_metrics,
            result_notes=payload.result_notes,
        )
    except ObjectiveTaskError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None

    return ObjectiveTaskPublic.from_task(updated)
