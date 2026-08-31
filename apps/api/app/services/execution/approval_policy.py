"""Approval policy boundary for execution steps. Does not auto-execute."""

from __future__ import annotations

from app.schemas.execution import (
    ApprovalRequirement,
    ExecutionPlan,
    ExecutionRisk,
    ExecutionStep,
    ExecutionStepCategory,
)
from app.schemas.tool import ToolCategory, ToolEffect
from app.services.tools.base import Tool


def classify_step_category(tool: Tool, step: ExecutionStep) -> ExecutionStepCategory:
    """Map a registered tool and step metadata to a policy category."""
    if tool.effect is ToolEffect.WRITE:
        if step.risk_level in {"high", "critical"}:
            return ExecutionStepCategory.WRITE_HIGH_RISK
        return ExecutionStepCategory.WRITE_LOW_RISK

    if tool.category is ToolCategory.EXTERNAL:
        return ExecutionStepCategory.EXTERNAL_SIDE_EFFECT

    if step.risk_level in {"high", "critical"}:
        return ExecutionStepCategory.READ_ONLY_HIGH_COST

    return ExecutionStepCategory.READ_ONLY_LOW_RISK


def evaluate_approval_requirement(
    category: ExecutionStepCategory,
    risk_level: ExecutionRisk,
) -> ApprovalRequirement:
    """
    Determine approval requirements for a step category.

    Task 9.8.1 defines the boundary only — automatic execution is NOT enabled.
    """
    auto_eligible = category is ExecutionStepCategory.READ_ONLY_LOW_RISK

    rationale_map = {
        ExecutionStepCategory.READ_ONLY_LOW_RISK: (
            "Read-only low-risk step. May become auto-eligible in a future release."
        ),
        ExecutionStepCategory.READ_ONLY_HIGH_COST: (
            "Read-only step with elevated cost or risk requires founder approval."
        ),
        ExecutionStepCategory.WRITE_LOW_RISK: (
            "Write-capable step requires founder approval."
        ),
        ExecutionStepCategory.WRITE_HIGH_RISK: (
            "High-risk write step requires founder approval."
        ),
        ExecutionStepCategory.EXTERNAL_SIDE_EFFECT: (
            "External side-effect step requires founder approval."
        ),
        ExecutionStepCategory.FINANCIAL_ACTION: (
            "Financial action requires founder approval."
        ),
        ExecutionStepCategory.COMMUNICATION_TO_CUSTOMER: (
            "Customer communication requires founder approval."
        ),
    }

    # 9.8.1: all steps require approval until controlled autonomy is enabled.
    approval_required = True

    return ApprovalRequirement(
        approval_required=approval_required,
        step_category=category,
        risk_level=risk_level,
        rationale=rationale_map.get(
            category,
            "Execution step requires founder approval.",
        ),
        auto_execution_eligible=False if approval_required else auto_eligible,
    )


def apply_approval_policy_to_plan(plan: ExecutionPlan, tools: dict[str, Tool]) -> ExecutionPlan:
    """Annotate each step with policy-derived approval flags (data only)."""
    updated_steps: list[ExecutionStep] = []
    for step in plan.steps:
        tool = tools[step.tool_qualified_name]
        category = classify_step_category(tool, step)
        requirement = evaluate_approval_requirement(category, step.risk_level)
        updated_steps.append(
            step.model_copy(
                update={
                    "step_category": requirement.step_category,
                    "approval_required": requirement.approval_required,
                }
            )
        )
    return plan.model_copy(update={"steps": updated_steps})
