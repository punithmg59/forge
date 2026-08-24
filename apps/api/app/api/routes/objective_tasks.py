from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_company_access
from app.db.dependencies import get_db
from app.models.company_member import CompanyMember
from app.schemas.objective_task import ObjectiveTaskListResponse, ObjectiveTaskPublic
from app.services import objective_task_service

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
