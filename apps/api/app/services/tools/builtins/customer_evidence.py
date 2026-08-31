"""Internal read-only customer evidence tool."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import Evidence
from app.schemas.tool import (
    CustomerEvidenceInput,
    CustomerEvidenceOutput,
    EvidenceSummary,
    ToolCategory,
    ToolEffect,
    ToolExecutionContext,
    ToolPermission,
)
from app.services.tools.base import Tool

CONTENT_PREVIEW_MAX = 500


class CustomerEvidenceTool(Tool[CustomerEvidenceInput, CustomerEvidenceOutput]):
    @property
    def name(self) -> str:
        return "customer_evidence"

    @property
    def version(self) -> str:
        return "v1"

    @property
    def description(self) -> str:
        return "Read company-scoped evidence records for customer and growth analysis."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CUSTOMER

    @property
    def effect(self) -> ToolEffect:
        return ToolEffect.READ

    @property
    def required_permissions(self) -> frozenset[ToolPermission]:
        return frozenset({ToolPermission.CUSTOMER_READ})

    @property
    def input_model(self) -> type[CustomerEvidenceInput]:
        return CustomerEvidenceInput

    @property
    def output_model(self) -> type[CustomerEvidenceOutput]:
        return CustomerEvidenceOutput

    async def execute(
        self,
        db: AsyncSession,
        context: ToolExecutionContext,
        validated_input: CustomerEvidenceInput,
    ) -> CustomerEvidenceOutput:
        query = (
            select(Evidence)
            .where(Evidence.company_id == context.company_id)
            .order_by(Evidence.created_at.desc())
            .limit(validated_input.limit)
        )
        if validated_input.evidence_type is not None:
            query = query.where(Evidence.type == validated_input.evidence_type)
        result = await db.execute(query)
        rows = result.scalars().all()
        summaries = [
            EvidenceSummary(
                id=row.id,
                type=row.type,
                title=row.title,
                content_preview=_preview(row.content),
                source_type=row.source_type,
                observed_at=row.observed_at,
            )
            for row in rows
        ]
        return CustomerEvidenceOutput(evidence=summaries, count=len(summaries))


def _preview(content: str) -> str:
    if len(content) <= CONTENT_PREVIEW_MAX:
        return content
    return content[:CONTENT_PREVIEW_MAX]
