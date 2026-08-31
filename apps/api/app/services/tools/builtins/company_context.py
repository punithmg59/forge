"""Internal read-only company context tool."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.schemas.tool import (
    CompanyContextInput,
    CompanyContextOutput,
    ToolCategory,
    ToolEffect,
    ToolExecutionContext,
    ToolPermission,
)
from app.services.tools.base import Tool


class CompanyContextTool(Tool[CompanyContextInput, CompanyContextOutput]):
    @property
    def name(self) -> str:
        return "company_context"

    @property
    def version(self) -> str:
        return "v1"

    @property
    def description(self) -> str:
        return "Read company identity and metadata for the authenticated tenant."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.COMPANY

    @property
    def effect(self) -> ToolEffect:
        return ToolEffect.READ

    @property
    def required_permissions(self) -> frozenset[ToolPermission]:
        return frozenset({ToolPermission.COMPANY_READ})

    @property
    def input_model(self) -> type[CompanyContextInput]:
        return CompanyContextInput

    @property
    def output_model(self) -> type[CompanyContextOutput]:
        return CompanyContextOutput

    async def execute(
        self,
        db: AsyncSession,
        context: ToolExecutionContext,
        validated_input: CompanyContextInput,
    ) -> CompanyContextOutput:
        company = await db.get(Company, context.company_id)
        if company is None:
            return CompanyContextOutput(company_id=context.company_id)
        return CompanyContextOutput(
            company_id=company.id,
            name=company.name,
            slug=company.slug,
            stage=company.stage,
            mission=company.mission,
            vision=company.vision,
            product_description=company.product_description,
            target_customer=company.target_customer,
        )
