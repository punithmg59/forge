"""Execution status API."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_company_access
from app.db.dependencies import get_db
from app.models.company_member import CompanyMember
from app.schemas.execution import ExecutionStatusResponse
from app.services.execution.status_service import get_execution_status

router = APIRouter(
    prefix="/companies/{company_id}/executions",
    tags=["executions"],
)


@router.get("/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_status_endpoint(
    company_id: uuid.UUID,
    execution_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> ExecutionStatusResponse:
    """
    Get server-authoritative execution status and details.

    Enforces:
    - Authentication (via require_company_access)
    - Company membership (via require_company_access)
    - Tenant isolation (company_id match)
    - Execution ownership (execution_id must belong to company)
    - Safe error serialization (no secrets exposed)
    """
    try:
        return await get_execution_status(
            db,
            company_id=company_id,
            execution_id=execution_id,
        )
    except ValueError:
        # Return 404 without revealing whether execution exists in another company
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found.",
        )
