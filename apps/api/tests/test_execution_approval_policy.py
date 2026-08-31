"""Execution approval policy tests."""

from __future__ import annotations

from app.schemas.execution import ExecutionStep, ExecutionStepCategory
from app.services.execution.approval_policy import (
    classify_step_category,
    evaluate_approval_requirement,
)
from app.services.tools.registry import get_tool


def test_read_only_low_risk_category() -> None:
    tool = get_tool("company_context:v1")
    step = ExecutionStep(
        step_id="s1",
        sequence=1,
        tool_name="company_context",
        tool_version="v1",
        purpose="Read company",
        risk_level="low",
        step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
    )
    category = classify_step_category(tool, step)
    assert category is ExecutionStepCategory.READ_ONLY_LOW_RISK


def test_all_categories_require_approval_in_9_8_1() -> None:
    for category in ExecutionStepCategory:
        requirement = evaluate_approval_requirement(category, "low")
        assert requirement.approval_required is True
        assert requirement.auto_execution_eligible is False


def test_read_only_low_risk_may_be_auto_eligible_in_future_flag() -> None:
    requirement = evaluate_approval_requirement(
        ExecutionStepCategory.READ_ONLY_LOW_RISK,
        "low",
    )
    assert requirement.step_category is ExecutionStepCategory.READ_ONLY_LOW_RISK
    assert "Read-only" in requirement.rationale
