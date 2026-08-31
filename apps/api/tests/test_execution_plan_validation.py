"""Execution plan validation tests."""

from __future__ import annotations

import pytest

from app.schemas.execution import ExecutionPlan, ExecutionStep, ExecutionStepCategory
from app.services.execution.errors import ExecutionPlanError
from app.services.execution.plan_validation import validate_execution_plan
from app.services.execution.policy import ExecutionRuntimePolicy
from app.services.tools.registry import disable_tool, enable_tool


def _sample_plan(**input_overrides: object) -> ExecutionPlan:
    return ExecutionPlan(
        goal="Understand customer evidence",
        rationale="Ground execution in company evidence before synthesis.",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step-1",
                sequence=1,
                tool_name="company_context",
                tool_version="v1",
                purpose="Load company metadata",
                input={},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
            ),
            ExecutionStep(
                step_id="step-2",
                sequence=2,
                tool_name="customer_evidence",
                tool_version="v1",
                purpose="Review recent customer evidence",
                input=input_overrides or {"limit": 5},
                risk_level="medium",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
            ),
        ],
    )


def test_valid_plan_resolves_registered_tools() -> None:
    tools = validate_execution_plan(_sample_plan())
    assert "company_context:v1" in tools
    assert "customer_evidence:v1" in tools


def test_unknown_tool_rejected() -> None:
    plan = ExecutionPlan(
        goal="Bad plan",
        rationale="Uses unknown tool",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="bad",
                sequence=1,
                tool_name="stripe_revenue",
                tool_version="v1",
                purpose="Invalid",
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
            ),
        ],
    )
    with pytest.raises(ExecutionPlanError):
        validate_execution_plan(plan)


def test_disabled_tool_rejected() -> None:
    disable_tool("company_context:v1")
    try:
        with pytest.raises(ExecutionPlanError):
            validate_execution_plan(_sample_plan())
    finally:
        enable_tool("company_context:v1")


def test_invalid_tool_input_rejected() -> None:
    with pytest.raises(ExecutionPlanError):
        validate_execution_plan(_sample_plan(limit=0))


def test_extra_input_fields_rejected() -> None:
    with pytest.raises(ExecutionPlanError):
        validate_execution_plan(_sample_plan(company_id="malicious"))


def test_plan_step_limit_enforced() -> None:
    policy = ExecutionRuntimePolicy(
        max_steps_per_plan=1,
        max_tool_calls_per_step=5,
        max_retries_per_step=3,
        max_total_duration_ms=120000,
    )
    with pytest.raises(ExecutionPlanError):
        validate_execution_plan(_sample_plan(), runtime_policy=policy)
