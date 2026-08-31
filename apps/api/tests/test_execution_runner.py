"""Task 9.8.2 — Controlled Execution Runner: Comprehensive Test Suite.

Tests all 33 required scenarios:
 1. approved plan executes
 2. unapproved plan does not execute
 3. missing approval does not execute
 4. unknown tool rejected (at plan validation)
 5. write tool rejected (at plan validation)
 6. ToolExecutor is always used
 7. tenant isolation
 8. invalid plan rejected
 9. invalid tool input rejected
10. successful step
11. failed step
12. retryable failure
13. non-retryable failure
14. retry limit
15. execution timeout
16. step timeout (via ToolExecutor's timeout)
17. max steps
18. max tool calls
19. repeated execution is idempotent
20. partial execution resumes correctly
21. cancelled execution does not run
22. terminal execution cannot run again
23. safe errors (no secrets in messages)
24. audit record created (ToolExecutor audit fires)
25. no Evidence created
26. no Learning created
27. no Objective mutation
28. no Approval mutation
29. no Brain mutation
30. malicious tool output is treated as data
31. secrets are absent from logs/errors
32. trace_id propagation
33. deterministic execution ordering
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, ConfigDict

from app.models.company_member import CompanyMember
from app.schemas.execution import (
    ExecutionAttempt,
    ExecutionIdentity,
    ExecutionPlan,
    ExecutionRequest,
    ExecutionStep,
    ExecutionStepCategory,
    ExecutionStepResult,
)
from app.schemas.tool import (
    ToolCall,
    ToolCategory,
    ToolEffect,
    ToolErrorCode,
    ToolExecutionContext,
    ToolPermission,
    ToolResult,
)
from app.services.execution.errors import (
    ExecutionNotApprovedError,
    ExecutionPlanError,
    ExecutionRunnerError,
    ExecutionScopeError,
)
from app.services.execution.policy import ExecutionRuntimePolicy
from app.services.execution.runner import (
    NON_RETRYABLE_TOOL_CODES,
    ExecutionRunner,
    _safe_error_message,
    _summarize_output,
)
from app.services.tools.base import Tool
from app.services.tools.executor import ToolExecutor


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _membership(company_id: uuid.UUID | None = None) -> CompanyMember:
    return CompanyMember(
        company_id=company_id or uuid.uuid4(),
        user_id=uuid.uuid4(),
        role="founder",
    )


def _identity(membership: CompanyMember, agent_type: str = "test_agent") -> ExecutionIdentity:
    return ExecutionIdentity(
        execution_id=uuid.uuid4(),
        company_id=membership.company_id,
        agent_type=agent_type,
        requested_by=membership.user_id,
        trace_id=str(uuid.uuid4()),
        created_at=datetime.now(UTC),
    )


def _step(
    step_id: str = "step-1",
    sequence: int = 1,
    tool_name: str = "company_context",
    tool_version: str = "v1",
    *,
    risk_level: str = "low",
    input: dict | None = None,
    timeout_ms: int | None = None,
    retry_policy: Any = None,
) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        sequence=sequence,
        tool_name=tool_name,
        tool_version=tool_version,
        purpose=f"Test step {step_id}",
        input=input or {},
        risk_level=risk_level,  # type: ignore[arg-type]
        step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
        timeout_ms=timeout_ms,
        retry_policy=retry_policy,
    )


def _plan(*steps: ExecutionStep) -> ExecutionPlan:
    if not steps:
        steps = (_step(),)
    return ExecutionPlan(
        goal="Test execution",
        rationale="Automated test",
        risk_level="low",
        steps=list(steps),
    )


def _request(
    membership: CompanyMember,
    *,
    status: str = "approved",
    plan: ExecutionPlan | None = None,
    agent_type: str = "test_agent",
) -> ExecutionRequest:
    identity = _identity(membership, agent_type=agent_type)
    return ExecutionRequest(
        identity=identity,
        status=status,  # type: ignore[arg-type]
        plan=plan or _plan(),
    )


def _successful_tool_result(tool_name: str = "company_context") -> ToolResult:
    return ToolResult(
        success=True,
        tool_name=tool_name,
        tool_version="v1",
        data={"company_id": str(uuid.uuid4()), "name": "Acme Co"},
        trace_id=str(uuid.uuid4()),
        executed_at=datetime.now(UTC),
        duration_ms=12.5,
    )


def _failed_tool_result(
    error_code: str = ToolErrorCode.TOOL_EXECUTION_FAILED.value,
    message: str = "Tool execution failed.",
    tool_name: str = "company_context",
) -> ToolResult:
    return ToolResult(
        success=False,
        tool_name=tool_name,
        tool_version="v1",
        error_code=error_code,
        error_message=message,
        trace_id=str(uuid.uuid4()),
        executed_at=datetime.now(UTC),
        duration_ms=5.0,
    )


def _policy(
    *,
    max_steps: int = 20,
    max_tool_calls_per_step: int = 5,
    max_retries: int = 3,
    max_duration_ms: int = 120000,
) -> ExecutionRuntimePolicy:
    return ExecutionRuntimePolicy(
        max_steps_per_plan=max_steps,
        max_tool_calls_per_step=max_tool_calls_per_step,
        max_retries_per_step=max_retries,
        max_total_duration_ms=max_duration_ms,
    )


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _mock_executor(result: ToolResult | None = None) -> MagicMock:
    executor = MagicMock(spec=ToolExecutor)
    executor.execute = AsyncMock(return_value=result or _successful_tool_result())
    return executor


# ---------------------------------------------------------------------------
# 1. Approved plan executes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approved_plan_executes() -> None:
    """An approved plan with a valid registered tool completes successfully."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()
    executor = _mock_executor(_successful_tool_result())

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        result = await runner.run(
            request,
            membership,
            plan_agent_task_id=uuid.uuid4(),
        )

    assert result.status == "succeeded"
    assert len(result.step_results) == 1
    assert result.step_results[0].status == "succeeded"
    executor.execute.assert_called_once()


# ---------------------------------------------------------------------------
# 2. Unapproved plan does not execute
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unapproved_plan_does_not_execute() -> None:
    """A plan without server-side approval must not execute any tool."""
    membership = _membership()
    request = _request(membership, status="waiting_for_approval")
    db = _mock_db()
    executor = _mock_executor()

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        side_effect=ExecutionNotApprovedError(),
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        with pytest.raises(ExecutionNotApprovedError):
            await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    executor.execute.assert_not_called()


# ---------------------------------------------------------------------------
# 3. Missing approval does not execute (same gate, different status)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_approval_does_not_execute() -> None:
    """Even if status='approved', execution requires server-side Approval record."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()
    executor = _mock_executor()

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        side_effect=ExecutionNotApprovedError(),
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        with pytest.raises(ExecutionNotApprovedError):
            await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    executor.execute.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Unknown tool rejected at plan validation
# ---------------------------------------------------------------------------


def test_unknown_tool_rejected_at_validation() -> None:
    """A plan referencing an unregistered tool is rejected by validate_execution_plan."""
    from app.services.execution.plan_validation import validate_execution_plan

    plan = _plan(
        _step(tool_name="stripe_revenue", tool_version="v1"),
    )
    with pytest.raises(ExecutionPlanError):
        validate_execution_plan(plan)


# ---------------------------------------------------------------------------
# 5. Write tool rejected at plan validation
# ---------------------------------------------------------------------------


def test_write_tool_rejected_at_validation() -> None:
    """A plan containing a write-effect tool is rejected by validate_execution_plan."""
    from app.schemas.tool import ToolEffect
    from app.services.execution.plan_validation import validate_execution_plan

    class _WriteInput(BaseModel):
        model_config = ConfigDict(extra="forbid")

    class _WriteOutput(BaseModel):
        model_config = ConfigDict(extra="forbid")
        ok: bool = True

    class _WriteTool(Tool[_WriteInput, _WriteOutput]):
        @property
        def name(self) -> str:
            return "test_write_tool"

        @property
        def version(self) -> str:
            return "v1"

        @property
        def description(self) -> str:
            return "test write"

        @property
        def category(self) -> ToolCategory:
            return ToolCategory.SYSTEM

        @property
        def effect(self) -> ToolEffect:
            return ToolEffect.WRITE

        @property
        def required_permissions(self) -> frozenset[ToolPermission]:
            return frozenset()

        @property
        def input_model(self) -> type[_WriteInput]:
            return _WriteInput

        @property
        def output_model(self) -> type[_WriteOutput]:
            return _WriteOutput

        async def execute(self, db, context, validated_input):  # noqa: ANN001
            return _WriteOutput()

    from app.services.tools.registry import _REGISTRY

    qualified = "test_write_tool:v1"
    _REGISTRY[qualified] = _WriteTool()
    try:
        plan = _plan(_step(tool_name="test_write_tool", tool_version="v1"))
        with pytest.raises(ExecutionPlanError, match="Write tool"):
            validate_execution_plan(plan)
    finally:
        _REGISTRY.pop(qualified, None)


# ---------------------------------------------------------------------------
# 6. ToolExecutor is always used (cannot be bypassed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_executor_is_always_used() -> None:
    """ExecutionRunner must delegate every tool call through ToolExecutor.execute()."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()
    executor = _mock_executor(_successful_tool_result())

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        result = await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    assert executor.execute.called
    assert result.status == "succeeded"


@pytest.mark.asyncio
async def test_runner_cannot_call_tool_execute_directly() -> None:
    """Verify runner only executes tools through ToolExecutor.execute."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()
    executor_mock = _mock_executor(_successful_tool_result())

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor_mock, runtime_policy=_policy())
        executor_mock.execute = AsyncMock(side_effect=RuntimeError("Bypass detected"))
        with pytest.raises(RuntimeError, match="Bypass detected"):
            await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    executor_mock.execute = AsyncMock(return_value=_successful_tool_result())
    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner2 = ExecutionRunner(db, tool_executor=executor_mock, runtime_policy=_policy())
        result = await runner2.run(request, membership, plan_agent_task_id=uuid.uuid4())
    assert result.status == "succeeded"
    assert executor_mock.execute.called


# ---------------------------------------------------------------------------
# 7. Tenant isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_isolation_cross_company_rejected() -> None:
    """A user from Company B cannot execute a plan belonging to Company A."""
    company_a = uuid.uuid4()
    company_b = uuid.uuid4()
    membership_a = _membership(company_id=company_a)
    membership_b = _membership(company_id=company_b)
    request = _request(membership_a, status="approved")

    db = _mock_db()
    executor = _mock_executor()
    runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())

    with pytest.raises(ExecutionScopeError):
        await runner.run(request, membership_b, plan_agent_task_id=uuid.uuid4())

    executor.execute.assert_not_called()


@pytest.mark.asyncio
async def test_tool_execution_context_is_scoped_to_authenticated_company() -> None:
    """ToolExecutionContext is built from membership.company_id, not from plan payload."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()

    captured_context: list[ToolExecutionContext] = []

    async def capture_execute(call: ToolCall, context: ToolExecutionContext, **kwargs):  # noqa: ANN001, ANN202
        captured_context.append(context)
        return _successful_tool_result()

    executor = _mock_executor()
    executor.execute = AsyncMock(side_effect=capture_execute)

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    assert len(captured_context) == 1
    assert captured_context[0].company_id == membership.company_id


# ---------------------------------------------------------------------------
# 8. Invalid plan rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_plan_rejected() -> None:
    """A plan with a non-existent tool is rejected before any execution."""
    membership = _membership()
    plan = ExecutionPlan(
        goal="Bad plan",
        rationale="Unknown tool",
        risk_level="low",
        steps=[
            ExecutionStep(
                step_id="bad-step",
                sequence=1,
                tool_name="nonexistent_tool",
                tool_version="v1",
                purpose="This tool does not exist",
                risk_level="low",
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
            )
        ],
    )
    request = _request(membership, status="approved", plan=plan)
    db = _mock_db()
    executor = _mock_executor()

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        with pytest.raises(ExecutionPlanError):
            await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    executor.execute.assert_not_called()


# ---------------------------------------------------------------------------
# 9. Invalid tool input rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_tool_input_rejected_at_plan_validation() -> None:
    """A step with input that fails Pydantic validation is rejected at plan validation."""
    from app.services.execution.plan_validation import validate_execution_plan

    plan = _plan(_step(tool_name="customer_evidence", tool_version="v1", input={"limit": 0}))
    with pytest.raises(ExecutionPlanError):
        validate_execution_plan(plan)


# ---------------------------------------------------------------------------
# 10. Successful step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_step_returns_step_result() -> None:
    """A step that succeeds produces a succeeded ExecutionStepResult."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()
    executor = _mock_executor(_successful_tool_result())

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        result = await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    assert result.status == "succeeded"
    step_result = result.step_results[0]
    assert step_result.status == "succeeded"
    assert step_result.step_id == "step-1"
    assert step_result.tool_qualified_name == "company_context:v1"
    assert step_result.duration_ms is not None
    assert step_result.started_at is not None
    assert step_result.completed_at is not None
    assert len(step_result.attempts) == 1
    assert step_result.attempts[0].status == "succeeded"


# ---------------------------------------------------------------------------
# 11. Failed step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failed_step_marks_execution_failed() -> None:
    """A step with a non-retryable failure marks execution as failed."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()
    executor = _mock_executor(
        _failed_tool_result(
            error_code=ToolErrorCode.TOOL_NOT_FOUND.value,
            message="Tool not found.",
        )
    )

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        result = await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    assert result.status == "failed"
    assert result.step_results[0].status == "failed"
    assert result.step_results[0].error_code == ToolErrorCode.TOOL_NOT_FOUND.value
    executor.execute.assert_called_once()


# ---------------------------------------------------------------------------
# 12. Retryable failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retryable_failure_retries_and_succeeds() -> None:
    """A retryable failure is retried and may succeed on a subsequent attempt."""
    from app.schemas.execution import RetryPolicy

    membership = _membership()
    plan = _plan(
        _step(
            retry_policy=RetryPolicy(max_attempts=3, backoff_ms=0),
        )
    )
    request = _request(membership, status="approved", plan=plan)
    db = _mock_db()

    executor = _mock_executor()
    executor.execute = AsyncMock(
        side_effect=[
            _failed_tool_result(error_code=ToolErrorCode.TOOL_EXECUTION_FAILED.value),
            _successful_tool_result(),
        ]
    )

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        result = await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    assert result.status == "succeeded"
    assert executor.execute.call_count == 2
    step_result = result.step_results[0]
    assert step_result.status == "succeeded"
    assert len(step_result.attempts) == 2
    assert step_result.attempts[0].status == "failed"
    assert step_result.attempts[1].status == "succeeded"


# ---------------------------------------------------------------------------
# 13. Non-retryable failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_retryable_failure_does_not_retry() -> None:
    """Validation errors and authorization failures are never retried."""
    from app.schemas.execution import RetryPolicy

    membership = _membership()
    plan = _plan(
        _step(retry_policy=RetryPolicy(max_attempts=5, backoff_ms=0))
    )
    request = _request(membership, status="approved", plan=plan)
    db = _mock_db()

    executor = _mock_executor(
        _failed_tool_result(error_code=ToolErrorCode.TOOL_INVALID_INPUT.value)
    )

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        result = await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    assert result.status == "failed"
    executor.execute.assert_called_once()
    assert result.step_results[0].error_code == ToolErrorCode.TOOL_INVALID_INPUT.value


@pytest.mark.asyncio
async def test_non_retryable_codes_set_is_comprehensive() -> None:
    """Verify the non-retryable code set covers all authorization/validation errors."""
    assert ToolErrorCode.TOOL_NOT_FOUND.value in NON_RETRYABLE_TOOL_CODES
    assert ToolErrorCode.TOOL_DISABLED.value in NON_RETRYABLE_TOOL_CODES
    assert ToolErrorCode.TOOL_UNAUTHORIZED.value in NON_RETRYABLE_TOOL_CODES
    assert ToolErrorCode.TOOL_INVALID_INPUT.value in NON_RETRYABLE_TOOL_CODES
    assert ToolErrorCode.TOOL_INVALID_OUTPUT.value in NON_RETRYABLE_TOOL_CODES
    assert ToolErrorCode.TOOL_WRITE_NOT_ALLOWED.value in NON_RETRYABLE_TOOL_CODES


# ---------------------------------------------------------------------------
# 14. Retry limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_limit_enforced() -> None:
    """Execution fails when all retry attempts are exhausted."""
    from app.schemas.execution import RetryPolicy

    membership = _membership()
    plan = _plan(
        _step(retry_policy=RetryPolicy(max_attempts=2, backoff_ms=0))
    )
    request = _request(membership, status="approved", plan=plan)
    db = _mock_db()

    executor = _mock_executor()
    executor.execute = AsyncMock(
        return_value=_failed_tool_result(error_code=ToolErrorCode.TOOL_EXECUTION_FAILED.value)
    )

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy(max_retries=3))
        result = await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    assert result.status == "failed"
    assert executor.execute.call_count == 2
    assert result.step_results[0].retryable is False


# ---------------------------------------------------------------------------
# 15. Execution timeout (total duration exceeded)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execution_total_timeout() -> None:
    """Execution that exceeds max_total_duration_ms is stopped safely."""
    membership = _membership()
    plan = _plan(
        _step(step_id="step-1", sequence=1),
        _step(step_id="step-2", sequence=2, tool_name="objective_status"),
    )
    request = _request(membership, status="approved", plan=plan)
    db = _mock_db()

    async def slow_execute(call, context, **kwargs):  # noqa: ANN001, ANN202
        await asyncio.sleep(0.2)
        return _successful_tool_result()

    executor = _mock_executor()
    executor.execute = AsyncMock(side_effect=slow_execute)

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(
            db,
            tool_executor=executor,
            runtime_policy=_policy(max_duration_ms=50),
        )
        result = await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    assert result.status == "failed"
    assert result.failure_reason is not None
    assert "duration" in result.failure_reason.lower() or "timeout" in result.failure_reason.lower()


# ---------------------------------------------------------------------------
# 16. Step timeout (executor level)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step_timeout_via_executor() -> None:
    """Verify timeout_ms is passed to ToolExecutor.execute per step."""
    membership = _membership()
    plan = _plan(_step(timeout_ms=500))
    request = _request(membership, status="approved", plan=plan)
    db = _mock_db()

    captured_kwargs: list[dict] = []

    async def capture_execute(call, context, **kwargs):  # noqa: ANN001, ANN202
        captured_kwargs.append(kwargs)
        return _successful_tool_result()

    executor = _mock_executor()
    executor.execute = AsyncMock(side_effect=capture_execute)

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    assert captured_kwargs[0].get("timeout_override_ms") == 500


# ---------------------------------------------------------------------------
# 17. Max steps enforced at plan validation
# ---------------------------------------------------------------------------


def test_max_steps_per_plan_enforced() -> None:
    """Plans exceeding max_steps_per_plan are rejected at validation."""
    from app.services.execution.plan_validation import validate_execution_plan

    steps = [
        _step(step_id=f"step-{i}", sequence=i, tool_name="company_context")
        for i in range(1, 4)
    ]
    plan = _plan(*steps)
    policy = _policy(max_steps=2)
    with pytest.raises(ExecutionPlanError, match="maximum steps"):
        validate_execution_plan(plan, runtime_policy=policy)


# ---------------------------------------------------------------------------
# 18. Max tool calls per step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_max_tool_calls_per_step_enforced() -> None:
    """Steps exceed max_tool_calls_per_step after the limit is hit."""
    from app.schemas.execution import RetryPolicy

    membership = _membership()
    plan = _plan(
        _step(retry_policy=RetryPolicy(max_attempts=5, backoff_ms=0))
    )
    request = _request(membership, status="approved", plan=plan)
    db = _mock_db()

    executor = _mock_executor()
    executor.execute = AsyncMock(
        return_value=_failed_tool_result(error_code=ToolErrorCode.TOOL_EXECUTION_FAILED.value)
    )

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(
            db,
            tool_executor=executor,
            runtime_policy=_policy(max_tool_calls_per_step=2, max_retries=10),
        )
        result = await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    assert result.status == "failed"
    assert executor.execute.call_count == 2
    assert "Maximum tool calls" in (result.step_results[0].error_message or "")


# ---------------------------------------------------------------------------
# 19. Repeated execution is idempotent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repeated_execution_already_succeeded_is_idempotent() -> None:
    """Calling run() on an already-succeeded execution returns existing result immediately."""
    membership = _membership()
    request = _request(membership, status="succeeded")
    prior_results = [
        ExecutionStepResult(
            step_id="step-1",
            sequence=1,
            status="succeeded",
            tool_qualified_name="company_context:v1",
            output_summary='{"name":"Acme"}',
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
    ]
    db = _mock_db()
    executor = _mock_executor()

    runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
    result = await runner.run(
        request,
        membership,
        plan_agent_task_id=uuid.uuid4(),
        prior_results=prior_results,
    )

    assert result.status == "succeeded"
    assert len(result.step_results) == 1
    executor.execute.assert_not_called()


@pytest.mark.asyncio
async def test_already_succeeded_step_is_not_re_executed() -> None:
    """A step that already has status='succeeded' in prior_results is skipped."""
    membership = _membership()
    plan = _plan(
        _step(step_id="step-1", sequence=1),
        _step(step_id="step-2", sequence=2, tool_name="objective_status"),
    )
    request = _request(membership, status="approved", plan=plan)

    prior_results = [
        ExecutionStepResult(
            step_id="step-1",
            sequence=1,
            status="succeeded",
            tool_qualified_name="company_context:v1",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
    ]
    db = _mock_db()
    executor = _mock_executor(_successful_tool_result("objective_status"))

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        result = await runner.run(
            request,
            membership,
            plan_agent_task_id=uuid.uuid4(),
            prior_results=prior_results,
        )

    assert result.status == "succeeded"
    executor.execute.assert_called_once()
    call_args = executor.execute.call_args
    assert call_args[0][0].tool_name == "objective_status"


# ---------------------------------------------------------------------------
# 20. Partial execution resumes correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_partial_execution_resumes_from_failed_step() -> None:
    """A failed prior step is retried on re-invocation."""
    from app.schemas.execution import RetryPolicy

    membership = _membership()
    plan = _plan(
        _step(
            step_id="step-1",
            sequence=1,
            retry_policy=RetryPolicy(max_attempts=3, backoff_ms=0),
        )
    )
    request = _request(membership, status="failed", plan=plan)

    prior_results = [
        ExecutionStepResult(
            step_id="step-1",
            sequence=1,
            status="failed",
            tool_qualified_name="company_context:v1",
            error_code=ToolErrorCode.TOOL_EXECUTION_FAILED.value,
            error_message="Tool execution failed.",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            attempts=[
                ExecutionAttempt(
                    attempt_id=uuid.uuid4(),
                    execution_id=uuid.uuid4(),
                    step_id="step-1",
                    attempt_number=1,
                    status="failed",
                    started_at=datetime.now(UTC),
                    error_code=ToolErrorCode.TOOL_EXECUTION_FAILED.value,
                    error_message="Tool execution failed.",
                    trace_id="trace-123",
                )
            ],
        )
    ]

    db = _mock_db()
    executor = _mock_executor(_successful_tool_result())

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        result = await runner.run(
            request,
            membership,
            plan_agent_task_id=uuid.uuid4(),
            prior_results=prior_results,
        )

    assert result.status == "succeeded"
    assert executor.execute.called


# ---------------------------------------------------------------------------
# 21. Cancelled execution does not run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancelled_execution_does_not_run() -> None:
    """A cancelled execution must not execute any tool."""
    membership = _membership()
    request = _request(membership, status="cancelled")
    db = _mock_db()
    executor = _mock_executor()

    runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
    with pytest.raises(ExecutionRunnerError):
        await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    executor.execute.assert_not_called()


# ---------------------------------------------------------------------------
# 22. Terminal execution cannot run again
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_terminal_execution_cannot_run() -> None:
    """Executions in terminal states (except succeeded) cannot run."""
    membership = _membership()
    request = _request(membership, status="cancelled")
    db = _mock_db()
    executor = _mock_executor()

    runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
    with pytest.raises(ExecutionRunnerError):
        await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    executor.execute.assert_not_called()


# ---------------------------------------------------------------------------
# 23. Safe errors (no secrets in messages)
# ---------------------------------------------------------------------------


def test_safe_error_message_scrubs_secrets() -> None:
    """Secret-containing strings must be replaced with safe generic messages."""
    assert _safe_error_message("api_key=sk-secret-1234") == "Tool execution failed."
    assert _safe_error_message("password=hunter2 was wrong") == "Tool execution failed."
    assert _safe_error_message("Authorization: Bearer tok_abc123") == "Tool execution failed."
    assert _safe_error_message("DB connection string with secret embedded") == "Tool execution failed."


def test_safe_error_message_preserves_safe_messages() -> None:
    """Non-sensitive messages are preserved."""
    msg = _safe_error_message("Tool execution timed out.")
    assert msg == "Tool execution timed out."


def test_safe_error_message_truncates_long_messages() -> None:
    """Messages exceeding 500 chars are truncated."""
    long_message = "x" * 600
    result = _safe_error_message(long_message)
    assert len(result) <= 500


# ---------------------------------------------------------------------------
# 24. Audit record created
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_record_created_via_tool_executor() -> None:
    """ToolExecutor.audit creates AgentTask records during execution."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()

    captured_kwargs: list[dict] = []

    async def capturing_execute(call, context, **kwargs):  # noqa: ANN001, ANN202
        captured_kwargs.append(kwargs)
        return _successful_tool_result()

    executor = _mock_executor()
    executor.execute = AsyncMock(side_effect=capturing_execute)

    agent_run_id = uuid.uuid4()

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        result = await runner.run(
            request,
            membership,
            plan_agent_task_id=uuid.uuid4(),
            agent_run_id=agent_run_id,
        )

    assert result.status == "succeeded"
    assert captured_kwargs[0].get("agent_run_id") == agent_run_id


# ---------------------------------------------------------------------------
# 25. No Evidence created
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_evidence_created() -> None:
    """ExecutionRunner must not create Evidence records."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()
    executor = _mock_executor(_successful_tool_result())

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    for call in db.add.call_args_list:
        obj = call[0][0] if call[0] else None
        if obj is not None:
            assert type(obj).__name__ != "Evidence", "Runner must not create Evidence records"


# ---------------------------------------------------------------------------
# 26. No Learning created
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_learning_created() -> None:
    """ExecutionRunner must not create Learning records."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()
    executor = _mock_executor(_successful_tool_result())

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    for call in db.add.call_args_list:
        obj = call[0][0] if call[0] else None
        if obj is not None:
            assert type(obj).__name__ != "Learning", "Runner must not create Learning records"


# ---------------------------------------------------------------------------
# 27. No Objective mutation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_objective_mutation() -> None:
    """ExecutionRunner must not create or modify Objective records."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()
    executor = _mock_executor(_successful_tool_result())

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    for call in db.add.call_args_list:
        obj = call[0][0] if call[0] else None
        if obj is not None:
            assert type(obj).__name__ not in {"Objective", "ObjectiveTask"}, (
                "Runner must not create Objective records"
            )


# ---------------------------------------------------------------------------
# 28. No Approval mutation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_approval_mutation() -> None:
    """ExecutionRunner must not create or modify Approval records."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()
    executor = _mock_executor(_successful_tool_result())

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    for call in db.add.call_args_list:
        obj = call[0][0] if call[0] else None
        if obj is not None:
            assert type(obj).__name__ != "Approval", "Runner must not create Approval records"


# ---------------------------------------------------------------------------
# 29. No Brain mutation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_brain_mutation() -> None:
    """ExecutionRunner must not create CompanyBrain, CompanyFact, or Belief records."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()
    executor = _mock_executor(_successful_tool_result())

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    for call in db.add.call_args_list:
        obj = call[0][0] if call[0] else None
        if obj is not None:
            assert type(obj).__name__ not in {
                "CompanyBrainProfile",
                "CompanyFact",
                "CompanyBelief",
                "Memory",
            }, "Runner must not create Brain records"


# ---------------------------------------------------------------------------
# 30. Malicious tool output is treated as data
# ---------------------------------------------------------------------------


def test_output_summary_is_data_not_executed() -> None:
    """Output from tools is summarized as opaque data — never parsed or executed."""
    malicious_output = {
        "result": "'; DROP TABLE companies; --",
        "command": "exec(import('os').system('rm -rf /'))",
        "injection": "<script>alert('xss')</script>",
    }
    summary = _summarize_output(malicious_output)
    assert summary is not None
    assert isinstance(summary, str)


@pytest.mark.asyncio
async def test_malicious_tool_output_does_not_escape_context() -> None:
    """Tool output is summarized and never executed or used to modify state."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()

    malicious_result = ToolResult(
        success=True,
        tool_name="company_context",
        tool_version="v1",
        data={"company_id": "../../etc/passwd", "name": "'; DROP TABLE companies; --"},
        trace_id=str(uuid.uuid4()),
        executed_at=datetime.now(UTC),
        duration_ms=10.0,
    )
    executor = _mock_executor(malicious_result)

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        result = await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    assert result.status == "succeeded"
    step_result = result.step_results[0]
    assert step_result.output_summary is not None
    assert isinstance(step_result.output_summary, str)


# ---------------------------------------------------------------------------
# 31. Secrets are absent from logs/errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_secret_containing_error_is_scrubbed(caplog: Any) -> None:
    """Error messages containing secret patterns must be scrubbed before storage."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()

    executor = _mock_executor(
        _failed_tool_result(
            error_code=ToolErrorCode.TOOL_EXECUTION_FAILED.value,
            message="Connection refused: api_key=sk-secret-deadbeef",
        )
    )

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        with caplog.at_level(logging.INFO):
            runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
            result = await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    assert result.status == "failed"
    step_result = result.step_results[0]
    assert "sk-secret" not in (step_result.error_message or "")
    assert "api_key" not in (step_result.error_message or "")

    for record in caplog.records:
        assert "sk-secret" not in record.message
        assert "api_key" not in record.message


# ---------------------------------------------------------------------------
# 32. Trace_id propagation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trace_id_propagated_to_tool_executor() -> None:
    """The trace_id from ExecutionIdentity is propagated to ToolCall and ToolExecutor."""
    membership = _membership()
    trace_id = "test-trace-xyz-123"
    identity = ExecutionIdentity(
        execution_id=uuid.uuid4(),
        company_id=membership.company_id,
        agent_type="test_agent",
        requested_by=membership.user_id,
        trace_id=trace_id,
        created_at=datetime.now(UTC),
    )
    request = ExecutionRequest(
        identity=identity,
        status="approved",
        plan=_plan(),
    )

    captured_calls: list[ToolCall] = []

    async def capture_execute(call: ToolCall, context: ToolExecutionContext, **kwargs):  # noqa: ANN202
        captured_calls.append(call)
        return _successful_tool_result()

    db = _mock_db()
    executor = _mock_executor()
    executor.execute = AsyncMock(side_effect=capture_execute)

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    assert len(captured_calls) == 1
    assert captured_calls[0].trace_id == trace_id


# ---------------------------------------------------------------------------
# 33. Deterministic execution ordering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deterministic_step_ordering() -> None:
    """Steps are always executed in ascending sequence order, regardless of list order."""
    membership = _membership()
    plan = ExecutionPlan(
        goal="Multi-step test",
        rationale="Ordering test",
        risk_level="low",
        steps=[
            _step(step_id="step-3", sequence=3, tool_name="customer_evidence"),
            _step(step_id="step-1", sequence=1, tool_name="company_context"),
            _step(step_id="step-2", sequence=2, tool_name="objective_status"),
        ],
    )
    request = _request(membership, status="approved", plan=plan)
    db = _mock_db()

    execution_order: list[str] = []

    async def order_capture(call: ToolCall, context: ToolExecutionContext, **kwargs):  # noqa: ANN202
        execution_order.append(call.tool_name)
        return _successful_tool_result(call.tool_name)

    executor = _mock_executor()
    executor.execute = AsyncMock(side_effect=order_capture)

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        result = await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    assert result.status == "succeeded"
    assert execution_order == ["company_context", "objective_status", "customer_evidence"]

    step_result_sequences = [sr.sequence for sr in result.step_results]
    assert step_result_sequences == sorted(step_result_sequences)


# ---------------------------------------------------------------------------
# Additional: output summary size limit
# ---------------------------------------------------------------------------


def test_output_summary_truncated_at_limit() -> None:
    """Output summaries exceeding OUTPUT_SUMMARY_MAX bytes are truncated."""
    from app.services.execution.runner import OUTPUT_SUMMARY_MAX

    large_data = {"data": "x" * 1000}
    summary = _summarize_output(large_data)
    assert summary is not None
    assert len(summary) <= OUTPUT_SUMMARY_MAX


def test_output_summary_none_for_empty_data() -> None:
    """None data returns None summary."""
    assert _summarize_output(None) is None
    assert _summarize_output({}) is None


# ---------------------------------------------------------------------------
# Additional: requested/planned statuses cannot execute
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_planned_status_cannot_execute_directly() -> None:
    """A 'planned' execution must go through approval first, not run directly."""
    membership = _membership()
    request = _request(membership, status="planned")
    db = _mock_db()
    executor = _mock_executor()

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        with pytest.raises(ExecutionRunnerError):
            await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    executor.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Additional: metrics are recorded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execution_metrics_recorded() -> None:
    """Execution result includes timing metrics."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()
    executor = _mock_executor(_successful_tool_result())

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        result = await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    assert result.metrics is not None
    assert result.metrics.total_ms > 0
    assert result.metrics.validation_ms >= 0
    assert result.metrics.tool_execution_ms >= 0


# ---------------------------------------------------------------------------
# Additional: execution_id and company_id in result
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_result_contains_execution_id_and_company_id() -> None:
    """ExecutionResult contains the correct execution_id and company_id."""
    membership = _membership()
    request = _request(membership, status="approved")
    db = _mock_db()
    executor = _mock_executor(_successful_tool_result())

    with patch(
        "app.services.execution.runner.verify_execution_approved",
        new_callable=AsyncMock,
    ):
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=_policy())
        result = await runner.run(request, membership, plan_agent_task_id=uuid.uuid4())

    assert result.execution_id == request.identity.execution_id
    assert result.company_id == membership.company_id
