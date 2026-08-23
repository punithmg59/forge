from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_company_access
from app.db.dependencies import get_db
from app.models.company_member import CompanyMember
from app.schemas.brain import BrainContextRequest, BrainQueryResponse, CompanyContext
from app.services.brain_context import BrainContextError, build_company_brain_context
from app.services.brain_query import BrainQueryError, answer_brain_query

router = APIRouter(
    prefix="/companies/{company_id}/brain",
    tags=["brain"],
)


@router.post("/context", response_model=CompanyContext)
async def post_brain_context(
    company_id: uuid.UUID,
    payload: BrainContextRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> CompanyContext:
    try:
        return await build_company_brain_context(
            db,
            membership=membership,
            query=payload.query,
        )
    except BrainContextError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None


@router.post("/query", response_model=BrainQueryResponse)
async def post_brain_query(
    company_id: uuid.UUID,
    payload: BrainContextRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> BrainQueryResponse:
    try:
        return await answer_brain_query(
            db,
            membership=membership,
            query=payload.query,
        )
    except BrainContextError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    except BrainQueryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
