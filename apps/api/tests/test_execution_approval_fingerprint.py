"""Tests for execution approval plan fingerprinting (Task 9.8.4)."""

from datetime import UTC, datetime, timedelta

import pytest
from app.schemas.execution import (
    ExecutionPlan,
    ExecutionRisk,
    ExecutionStep,
    ExecutionStepCategory,
    RetryPolicy,
)
from app.services.execution.approval_verification import compute_plan_fingerprint


def test_fingerprint_deterministic_same_plan():
    """Same canonical plan → same fingerprint."""
    plan = ExecutionPlan(
        goal="Test goal",
        rationale="Test rationale",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step1",
                sequence=1,
                tool_name="test_tool",
                tool_version="v1",
                purpose="Test purpose",
                input={"key": "value"},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            )
        ],
    )

    fp1 = compute_plan_fingerprint(plan)
    fp2 = compute_plan_fingerprint(plan)

    assert fp1 == fp2
    assert len(fp1) == 64  # SHA256 hex string


def test_fingerprint_different_tool():
    """Different tool → different fingerprint."""
    plan1 = ExecutionPlan(
        goal="Test goal",
        rationale="Test rationale",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step1",
                sequence=1,
                tool_name="tool_a",
                tool_version="v1",
                purpose="Test purpose",
                input={},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            )
        ],
    )

    plan2 = ExecutionPlan(
        goal="Test goal",
        rationale="Test rationale",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step1",
                sequence=1,
                tool_name="tool_b",
                tool_version="v1",
                purpose="Test purpose",
                input={},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            )
        ],
    )

    assert compute_plan_fingerprint(plan1) != compute_plan_fingerprint(plan2)


def test_fingerprint_different_tool_version():
    """Different tool version → different fingerprint."""
    plan1 = ExecutionPlan(
        goal="Test goal",
        rationale="Test rationale",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step1",
                sequence=1,
                tool_name="test_tool",
                tool_version="v1",
                purpose="Test purpose",
                input={},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            )
        ],
    )

    plan2 = ExecutionPlan(
        goal="Test goal",
        rationale="Test rationale",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step1",
                sequence=1,
                tool_name="test_tool",
                tool_version="v2",
                purpose="Test purpose",
                input={},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            )
        ],
    )

    assert compute_plan_fingerprint(plan1) != compute_plan_fingerprint(plan2)


def test_fingerprint_different_input():
    """Different input → different fingerprint."""
    plan1 = ExecutionPlan(
        goal="Test goal",
        rationale="Test rationale",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step1",
                sequence=1,
                tool_name="test_tool",
                tool_version="v1",
                purpose="Test purpose",
                input={"key": "value1"},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            )
        ],
    )

    plan2 = ExecutionPlan(
        goal="Test goal",
        rationale="Test rationale",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step1",
                sequence=1,
                tool_name="test_tool",
                tool_version="v1",
                purpose="Test purpose",
                input={"key": "value2"},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            )
        ],
    )

    assert compute_plan_fingerprint(plan1) != compute_plan_fingerprint(plan2)


def test_fingerprint_different_sequence():
    """Different sequence → different fingerprint."""
    plan1 = ExecutionPlan(
        goal="Test goal",
        rationale="Test rationale",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step1",
                sequence=1,
                tool_name="test_tool",
                tool_version="v1",
                purpose="Test purpose",
                input={},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            )
        ],
    )

    plan2 = ExecutionPlan(
        goal="Test goal",
        rationale="Test rationale",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step1",
                sequence=2,
                tool_name="test_tool",
                tool_version="v1",
                purpose="Test purpose",
                input={},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            )
        ],
    )

    assert compute_plan_fingerprint(plan1) != compute_plan_fingerprint(plan2)


def test_fingerprint_different_risk_level():
    """Different risk level → different fingerprint."""
    plan1 = ExecutionPlan(
        goal="Test goal",
        rationale="Test rationale",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step1",
                sequence=1,
                tool_name="test_tool",
                tool_version="v1",
                purpose="Test purpose",
                input={},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            )
        ],
    )

    plan2 = ExecutionPlan(
        goal="Test goal",
        rationale="Test rationale",
        risk_level="high",
        steps=[
            ExecutionStep(
                step_id="step1",
                sequence=1,
                tool_name="test_tool",
                tool_version="v1",
                purpose="Test purpose",
                input={},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            )
        ],
    )

    assert compute_plan_fingerprint(plan1) != compute_plan_fingerprint(plan2)


def test_fingerprint_reordered_dict_keys():
    """Reordered dictionary keys → same fingerprint."""
    plan1 = ExecutionPlan(
        goal="Test goal",
        rationale="Test rationale",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step1",
                sequence=1,
                tool_name="test_tool",
                tool_version="v1",
                purpose="Test purpose",
                input={"a": 1, "b": 2, "c": 3},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            )
        ],
    )

    plan2 = ExecutionPlan(
        goal="Test goal",
        rationale="Test rationale",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step1",
                sequence=1,
                tool_name="test_tool",
                tool_version="v1",
                purpose="Test purpose",
                input={"c": 3, "a": 1, "b": 2},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            )
        ],
    )

    assert compute_plan_fingerprint(plan1) == compute_plan_fingerprint(plan2)


def test_fingerprint_includes_all_material_fields():
    """Fingerprint includes all material fields that affect execution."""
    plan1 = ExecutionPlan(
        goal="Goal A",
        rationale="Rationale A",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step1",
                sequence=1,
                tool_name="tool",
                tool_version="v1",
                purpose="Purpose A",
                input={},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
                timeout_ms=5000,
            )
        ],
    )

    plan2 = ExecutionPlan(
        goal="Goal B",  # Different
        rationale="Rationale A",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step1",
                sequence=1,
                tool_name="tool",
                tool_version="v1",
                purpose="Purpose A",
                input={},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
                timeout_ms=5000,
            )
        ],
    )

    assert compute_plan_fingerprint(plan1) != compute_plan_fingerprint(plan2)


def test_fingerprint_steps_sorted_by_sequence():
    """Steps are sorted by sequence for fingerprint, not by order in list."""
    plan = ExecutionPlan(
        goal="Test goal",
        rationale="Test rationale",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step2",
                sequence=2,
                tool_name="tool_b",
                tool_version="v1",
                purpose="Purpose B",
                input={},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            ),
            ExecutionStep(
                step_id="step1",
                sequence=1,
                tool_name="tool_a",
                tool_version="v1",
                purpose="Purpose A",
                input={},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            ),
        ],
    )

    # Should produce same fingerprint as correctly ordered steps
    plan_ordered = ExecutionPlan(
        goal="Test goal",
        rationale="Test rationale",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step1",
                sequence=1,
                tool_name="tool_a",
                tool_version="v1",
                purpose="Purpose A",
                input={},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            ),
            ExecutionStep(
                step_id="step2",
                sequence=2,
                tool_name="tool_b",
                tool_version="v1",
                purpose="Purpose B",
                input={},
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            ),
        ],
    )

    assert compute_plan_fingerprint(plan) == compute_plan_fingerprint(plan_ordered)
