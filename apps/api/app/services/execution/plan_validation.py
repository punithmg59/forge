"""Execution plan validation against ToolRegistry contracts."""

from __future__ import annotations

import json

from pydantic import ValidationError

from app.schemas.execution import ExecutionPlan, ExecutionStep
from app.schemas.tool import ToolEffect
from app.services.execution.errors import ExecutionPlanError
from app.services.execution.policy import ExecutionRuntimePolicy
from app.services.tools.base import Tool
from app.services.tools.registry import get_tool, is_tool_enabled


def validate_execution_plan(
    plan: ExecutionPlan,
    *,
    runtime_policy: ExecutionRuntimePolicy | None = None,
) -> dict[str, Tool]:
    """
    Validate plan structure and tool references.

    Returns resolved tools map for downstream policy application.
    Does NOT execute tools.
    """
    policy = runtime_policy or ExecutionRuntimePolicy.default()
    if len(plan.steps) > policy.max_steps_per_plan:
        raise ExecutionPlanError(
            f"Plan exceeds maximum steps ({policy.max_steps_per_plan})."
        )

    tools: dict[str, Tool] = {}
    for step in sorted(plan.steps, key=lambda s: s.sequence):
        _validate_step_input_size(step)
        qualified = step.tool_qualified_name
        if qualified in tools:
            continue
        if not is_tool_enabled(qualified):
            raise ExecutionPlanError(f"Tool '{qualified}' is disabled or unknown.")
        tool = get_tool(qualified)
        if tool.effect is ToolEffect.WRITE:
            raise ExecutionPlanError(
                f"Write tool '{qualified}' cannot be included in execution plans yet."
            )
        try:
            tool.input_model.model_validate(step.input)
        except ValidationError as exc:
            raise ExecutionPlanError(
                f"Invalid input for tool '{qualified}' in step '{step.step_id}'."
            ) from exc
        tools[qualified] = tool

    return tools


def _validate_step_input_size(step: ExecutionStep) -> None:
    encoded = json.dumps(step.input, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > 8192:
        raise ExecutionPlanError(
            f"Step '{step.step_id}' input exceeds allowed size."
        )
