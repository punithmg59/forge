"""Internal read-only objective status tool."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tool import (
    ObjectiveStatusInput,
    ObjectiveStatusOutput,
    ToolCategory,
    ToolEffect,
    ToolExecutionContext,
    ToolPermission,
)
from app.services.objective_service import get_current_objective
from app.services.tools.base import Tool


class ObjectiveStatusTool(Tool[ObjectiveStatusInput, ObjectiveStatusOutput]):
    @property
    def name(self) -> str:
        return "objective_status"

    @property
    def version(self) -> str:
        return "v1"

    @property
    def description(self) -> str:
        return "Read the current objective and status for the authenticated tenant."

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
    def input_model(self) -> type[ObjectiveStatusInput]:
        return ObjectiveStatusInput

    @property
    def output_model(self) -> type[ObjectiveStatusOutput]:
        return ObjectiveStatusOutput

    async def execute(
        self,
        db: AsyncSession,
        context: ToolExecutionContext,
        validated_input: ObjectiveStatusInput,
    ) -> ObjectiveStatusOutput:
        objective = await get_current_objective(db, company_id=context.company_id)
        if objective is None:
            return ObjectiveStatusOutput(has_active_objective=False)
        return ObjectiveStatusOutput(
            has_active_objective=True,
            objective_id=objective.id,
            title=objective.title,
            description=objective.description,
            status=objective.status,
            priority=objective.priority,
            target_value=objective.target_value,
            target_unit=objective.target_unit,
            deadline=objective.deadline,
        )
