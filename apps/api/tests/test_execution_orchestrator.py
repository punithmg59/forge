"""Execution foundation orchestrator boundary tests.

Task 9.8.2: Updated from 9.8.1 stale test.
ExecutionFoundationOrchestrator.run_execution now delegates to ExecutionRunner
instead of raising ExecutionNotImplementedError.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.company_member import CompanyMember
from app.schemas.execution import ExecutionPlan, ExecutionStep, ExecutionStepCategory
from app.services.execution.errors import ExecutionRunnerError, ExecutionScopeError
from app.services.execution.orchestrator import ExecutionFoundationOrchestrator


def _membership(role: str = "founder") -> CompanyMember:
    return CompanyMember(
        company_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=role,
    )


def _plan() -> ExecutionPlan:
    return ExecutionPlan(
        goal="Review evidence",
        rationale="Prepare for future autonomous step.",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="step-1",
                sequence=1,
                tool_name="objective_status",
                tool_version="v1",
                purpose="Check objective",
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
            ),
        ],
    )


@pytest.mark.asyncio
async def test_orchestrator_delegates_to_runner() -> None:
    """Task 9.8.2: run_execution delegates to ExecutionRunner (no longer a stub).

    The orchestrator constructs ExecutionRunner and delegates run() to it.
    The runner itself enforces approval, tenant isolation, and tool execution.
    """
    membership = _membership()
    orchestrator = ExecutionFoundationOrchestrator()
    request = orchestrator.build_request(membership, agent_type="head_agent")
    with patch("app.services.execution.runner.ExecutionRunner.run", new_callable=AsyncMock) as runner_mock:
        await orchestrator.run_execution(
            request,
            membership,
            db=None,  # type: ignore[arg-type]
            plan_agent_task_id=uuid.uuid4(),
        )
        runner_mock.assert_called_once()


@pytest.mark.asyncio
async def test_execute_step_is_not_exposed() -> None:
    """The orchestrator hard-blocks individual step execution (architectural boundary)."""
    orchestrator = ExecutionFoundationOrchestrator()
    membership = _membership()
    request = orchestrator.build_request(membership, agent_type="head_agent")
    with pytest.raises(ExecutionRunnerError):
        await orchestrator.execute_step(request, "step-1")


def test_attach_plan_annotates_approval_flags() -> None:
    membership = _membership()
    orchestrator = ExecutionFoundationOrchestrator()
    request = orchestrator.build_request(membership, agent_type="head_agent")
    updated = orchestrator.attach_plan(request, _plan(), membership)
    assert updated.status == "planned"
    assert updated.plan is not None
    assert updated.plan.steps[0].approval_required is True


def test_cross_company_request_rejected() -> None:
    membership_a = _membership()
    membership_b = _membership()
    orchestrator = ExecutionFoundationOrchestrator()
    request = orchestrator.build_request(membership_a, agent_type="head_agent")
    with pytest.raises(ExecutionScopeError):
        orchestrator.attach_plan(request, _plan(), membership_b)


@pytest.mark.asyncio
async def test_cancel_execution_updates_status() -> None:
    membership = _membership()
    orchestrator = ExecutionFoundationOrchestrator()
    request = orchestrator.build_request(membership, agent_type="head_agent")
    planned = orchestrator.attach_plan(request, _plan(), membership)
    running_request = planned.model_copy(update={"status": "running"})
    cancelled = await orchestrator.cancel_execution(
        running_request,
        membership,
        reason="Founder stopped execution",
    )
    assert cancelled.status == "cancelled"
    assert cancelled.cancel_reason == "Founder stopped execution"
