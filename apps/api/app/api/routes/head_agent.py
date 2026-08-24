from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_company_access
from app.db.dependencies import get_db
from app.models.company_member import CompanyMember
from app.schemas.head_agent import HeadAgentRecommendRequest, HeadAgentRecommendResponse
from app.services.brain_context import BrainContextError
from app.services.head_agent import HeadAgentError, recommend_next_action

router = APIRouter(
    prefix="/companies/{company_id}/head-agent",
    tags=["head-agent"],
)


@router.post("/recommend", response_model=HeadAgentRecommendResponse)
async def post_head_agent_recommend(
    company_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    membership: Annotated[CompanyMember, Depends(require_company_access)],
    payload: HeadAgentRecommendRequest = HeadAgentRecommendRequest(),
) -> HeadAgentRecommendResponse:
    request = payload
    try:
        return await recommend_next_action(
            db,
            membership=membership,
            question=request.question,
        )
    except BrainContextError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    except HeadAgentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
