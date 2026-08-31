from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_company_access
from app.db.dependencies import get_db
from app.models.company_member import CompanyMember
from app.schemas.learning import LearningProposalResponse
from app.services.evidence_service import get_evidence_for_company
from app.services.learning_proposal_service import (
    LearningProposalError,
    propose_learning_from_evidence,
)

router = APIRouter(
    prefix="/companies/{company_id}/evidence",
    tags=["evidence"],
)


@router.post(
    "/{evidence_id}/learning-proposal",
    response_model=LearningProposalResponse,
)
async def post_learning_proposal(
    company_id: uuid.UUID,
    evidence_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _membership: Annotated[CompanyMember, Depends(require_company_access)],
) -> LearningProposalResponse:
    evidence = await get_evidence_for_company(
        db,
        company_id=company_id,
        evidence_id=evidence_id,
    )
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    try:
        return await propose_learning_from_evidence(db, evidence=evidence)
    except LearningProposalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
