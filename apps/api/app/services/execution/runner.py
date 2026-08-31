"""Controlled sequential execution of approved read-only plans."""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_member import CompanyMember
from app.schemas.execution import (
    ExecutionAttempt,
    ExecutionRequest,
    ExecutionResult,
    ExecutionRunMetrics,
    ExecutionStep,
    ExecutionStepResult,
)
from app.schemas.tool import ToolCall, ToolErrorCode
from app.services.execution.approval_verification import verify_execution_approved
from app.services.execution.errors import (
    ExecutionNotApprovedError,
    ExecutionPlanError,
    ExecutionRunnerError,
    ExecutionScopeError,
)
from app.services.execution.identity import assert_execution_tenant
from app.services.execution.plan_validation import validate_execution_plan
from app.services.execution.policy import ExecutionRuntimePolicy
from app.services.execution.state import (
    validate_execution_status_transition,
    validate_step_status_transition,
)
from app.services.tools.context import build_tool_execution_context
from app.services.tools.executor import ToolExecutor

logger = logging.getLogger(__name__)

RETRYABLE_TOOL_CODES = frozenset(
    {
        ToolErrorCode.TOOL_TIMEOUT.value,
        ToolErrorCode.TOOL_EXECUTION_FAILED.value,
    }
)
NON_RETRYABLE_TOOL_CODES = frozenset(
    {
        ToolErrorCode.TOOL_NOT_FOUND.value,
        ToolErrorCode.TOOL_DISABLED.value,
        ToolErrorCode.TOOL_UNAUTHORIZED.value,
        ToolErrorCode.TOOL_INVALID_INPUT.value,
        ToolErrorCode.TOOL_INVALID_OUTPUT.value,
        ToolErrorCode.TOOL_WRITE_NOT_ALLOWED.value,
        ToolErrorCode.TOOL_RESULT_TOO_LARGE.value,
        ToolErrorCode.TOOL_POLICY_LIMIT.value,
    }
)
OUTPUT_SUMMARY_MAX = 240
EXECUTABLE_STATUSES = frozenset({"approved", "running", "retrying", "failed"})


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _summarize_output(data: dict | None) -> str | None:
    if not data:
        return None
    encoded = json.dumps(data, ensure_ascii=False, default=str)
    if len(encoded) <= OUTPUT_SUMMARY_MAX:
        return encoded
    return encoded[:OUTPUT_SUMMARY_MAX]


def _safe_error_message(message: str | None) -> str:
    text = (message or "Tool execution failed.").strip()
    lowered = text.lower()
    for secret in ("api_key", "password", "secret", "authorization", "bearer "):
        if secret in lowered:
            return "Tool execution failed."
    return text[:500]


class ExecutionRunner:
    """Runs an approved ExecutionPlan through ToolExecutor only."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        tool_executor: ToolExecutor,
        runtime_policy: ExecutionRuntimePolicy | None = None,
    ) -> None:
        self._db = db
        self._executor = tool_executor
        self._policy = runtime_policy or ExecutionRuntimePolicy.default()

    async def run(
        self,
        request: ExecutionRequest,
        membership: CompanyMember,
        *,
        plan_agent_task_id: uuid.UUID,
        prior_results: list[ExecutionStepResult] | None = None,
        agent_run_id: uuid.UUID | None = None,
    ) -> ExecutionResult:
        total_start = time.perf_counter()
        metrics = ExecutionRunMetrics()
        validation_start = time.perf_counter()

        try:
            assert_execution_tenant(request.identity, membership)
        except ExecutionScopeError:
            raise

        if request.status == "cancelled":
            raise ExecutionRunnerError("Cancelled execution cannot run.")
        if request.status == "succeeded":
            return ExecutionResult(
                execution_id=request.identity.execution_id,
                company_id=request.identity.company_id,
                status="succeeded",
                step_results=list(prior_results or []),
                completed_at=request.completed_at or _utcnow(),
                metrics=metrics,
            )
        if request.status not in EXECUTABLE_STATUSES and request.status != "waiting_for_approval":
            raise ExecutionRunnerError(
                f"Execution cannot run from status '{request.status}'.",
            )

        if request.plan is None:
            raise ExecutionPlanError("Execution plan is required.")

        validate_execution_plan(request.plan, runtime_policy=self._policy)
        metrics.validation_ms = (time.perf_counter() - validation_start) * 1000

        if request.status in {"requested", "planned"}:
            raise ExecutionRunnerError(
                f"Execution cannot run from status '{request.status}'.",
            )
        if request.status == "waiting_for_approval":
            try:
                await self._require_approval(request, membership, plan_agent_task_id)
            except ExecutionNotApprovedError:
                raise
            request = request.model_copy(update={"status": "approved"})
        else:
            await self._require_approval(request, membership, plan_agent_task_id)

        logger.info(
            "execution_started execution_id=%s company_id=%s trace_id=%s agent_type=%s",
            request.identity.execution_id,
            request.identity.company_id,
            request.identity.trace_id,
            request.identity.agent_type,
        )

        working = request
        if working.status == "failed":
            validate_execution_status_transition("failed", "retrying")
            working = working.model_copy(update={"status": "retrying"})
        if working.status in {"approved", "retrying"}:
            validate_execution_status_transition(working.status, "running")
            working = working.model_copy(
                update={"status": "running", "started_at": working.started_at or _utcnow()}
            )

        context = build_tool_execution_context(
            membership,
            agent_type=request.identity.agent_type,
            trace_id=request.identity.trace_id,
            request_id=str(request.identity.execution_id),
        )

        results_by_id = {result.step_id: result for result in (prior_results or [])}
        ordered_steps = sorted(request.plan.steps, key=lambda step: step.sequence)
        deadline = total_start + (self._policy.max_total_duration_ms / 1000.0)

        for step in ordered_steps:
            existing = results_by_id.get(step.step_id)
            if existing is not None and existing.status == "succeeded":
                continue
            if time.perf_counter() >= deadline:
                failure = "Execution exceeded maximum duration."
                working = working.model_copy(
                    update={
                        "status": "failed",
                        "failure_reason": failure,
                        "completed_at": _utcnow(),
                    }
                )
                logger.info(
                    "execution_completed execution_id=%s status=failed reason=timeout",
                    request.identity.execution_id,
                )
                metrics.total_ms = (time.perf_counter() - total_start) * 1000
                return self._result(working, list(results_by_id.values()), metrics)

            step_result = await self._run_step(
                step=step,
                request=working,
                context=context,
                prior=existing,
                agent_run_id=agent_run_id,
                deadline=deadline,
                metrics=metrics,
            )
            results_by_id[step.step_id] = step_result
            if step_result.status == "failed":
                working = working.model_copy(
                    update={
                        "status": "failed",
                        "failure_reason": step_result.error_message or "Step failed.",
                        "completed_at": _utcnow(),
                    }
                )
                metrics.total_ms = (time.perf_counter() - total_start) * 1000
                logger.info(
                    "execution_completed execution_id=%s status=failed step_id=%s",
                    request.identity.execution_id,
                    step.step_id,
                )
                return self._result(
                    working,
                    _ordered_results(ordered_steps, results_by_id),
                    metrics,
                )

        working = working.model_copy(
            update={"status": "succeeded", "completed_at": _utcnow(), "failure_reason": None}
        )
        metrics.total_ms = (time.perf_counter() - total_start) * 1000
        logger.info(
            "execution_completed execution_id=%s company_id=%s trace_id=%s "
            "status=succeeded total_ms=%.1f",
            request.identity.execution_id,
            request.identity.company_id,
            request.identity.trace_id,
            metrics.total_ms,
        )
        return self._result(working, _ordered_results(ordered_steps, results_by_id), metrics)

    async def _require_approval(
        self,
        request: ExecutionRequest,
        membership: CompanyMember,
        plan_agent_task_id: uuid.UUID,
    ) -> None:
        await verify_execution_approved(
            self._db,
            company_id=membership.company_id,
            plan_agent_task_id=plan_agent_task_id,
        )

    async def _run_step(
        self,
        *,
        step: ExecutionStep,
        request: ExecutionRequest,
        context,
        prior: ExecutionStepResult | None,
        agent_run_id: uuid.UUID | None,
        deadline: float,
        metrics: ExecutionRunMetrics,
    ) -> ExecutionStepResult:
        max_attempts = _max_attempts(step, self._policy)
        prior_attempts = list(prior.attempts) if prior is not None else []
        current_status: str = prior.status if prior is not None else "pending"
        if current_status == "failed":
            validate_step_status_transition("failed", "running")
            current_status = "running"
        elif current_status == "pending":
            validate_step_status_transition("pending", "running")
            current_status = "running"
        elif current_status in {"approved", "waiting_for_approval"}:
            validate_step_status_transition(current_status, "running")
            current_status = "running"

        logger.info(
            "execution_step_started execution_id=%s step_id=%s tool_name=%s trace_id=%s",
            request.identity.execution_id,
            step.step_id,
            step.tool_qualified_name,
            request.identity.trace_id,
        )

        tool_calls_this_step = 0
        last_error_code: str | None = None
        last_error_message: str | None = None
        retryable = False
        started_at = _utcnow()

        while True:
            if time.perf_counter() >= deadline:
                return _failed_step(
                    step,
                    error_code="EXECUTION_TIMEOUT",
                    error_message="Execution exceeded maximum duration.",
                    retryable=False,
                    attempts=prior_attempts,
                    started_at=started_at,
                )
            if tool_calls_this_step >= self._policy.max_tool_calls_per_step:
                return _failed_step(
                    step,
                    error_code="EXECUTION_POLICY_DENIED",
                    error_message="Maximum tool calls per step exceeded.",
                    retryable=False,
                    attempts=prior_attempts,
                    started_at=started_at,
                )

            attempt_number = len(prior_attempts) + 1
            if attempt_number > max_attempts:
                return _failed_step(
                    step,
                    error_code=last_error_code or "EXECUTION_STEP_FAILED",
                    error_message=last_error_message or "Retry limit reached.",
                    retryable=False,
                    attempts=prior_attempts,
                    started_at=started_at,
                )

            tool_start = time.perf_counter()
            call = ToolCall(
                tool_name=step.tool_name,
                tool_version=step.tool_version,
                input=step.input,
                trace_id=request.identity.trace_id,
            )
            tool_result = await self._executor.execute(
                call,
                context,
                agent_run_id=agent_run_id,
                timeout_override_ms=step.timeout_ms,
            )
            tool_ms = (time.perf_counter() - tool_start) * 1000
            metrics.tool_execution_ms += tool_ms
            tool_calls_this_step += 1

            attempt = ExecutionAttempt(
                attempt_id=uuid.uuid4(),
                execution_id=request.identity.execution_id,
                step_id=step.step_id,
                attempt_number=attempt_number,
                status="succeeded" if tool_result.success else "failed",
                started_at=started_at,
                completed_at=_utcnow(),
                error_code=tool_result.error_code,
                error_message=_safe_error_message(tool_result.error_message)
                if not tool_result.success
                else None,
                trace_id=request.identity.trace_id,
            )
            prior_attempts.append(attempt)

            if tool_result.success:
                completed = _utcnow()
                logger.info(
                    "execution_step_succeeded execution_id=%s step_id=%s "
                    "tool_name=%s duration_ms=%.1f",
                    request.identity.execution_id,
                    step.step_id,
                    step.tool_qualified_name,
                    tool_ms,
                )
                return ExecutionStepResult(
                    step_id=step.step_id,
                    sequence=step.sequence,
                    status="succeeded",
                    tool_qualified_name=step.tool_qualified_name,
                    output_summary=_summarize_output(tool_result.data),
                    started_at=started_at,
                    completed_at=completed,
                    duration_ms=tool_ms,
                    attempts=prior_attempts,
                )

            last_error_code = tool_result.error_code
            last_error_message = _safe_error_message(tool_result.error_message)
            retryable = (tool_result.error_code or "") in RETRYABLE_TOOL_CODES
            logger.info(
                "execution_step_failed execution_id=%s step_id=%s tool_name=%s error_code=%s",
                request.identity.execution_id,
                step.step_id,
                step.tool_qualified_name,
                last_error_code,
            )
            if not retryable or last_error_code in NON_RETRYABLE_TOOL_CODES:
                return _failed_step(
                    step,
                    error_code=last_error_code or "EXECUTION_STEP_FAILED",
                    error_message=last_error_message or "Step failed.",
                    retryable=False,
                    attempts=prior_attempts,
                    started_at=started_at,
                )
            if attempt_number >= max_attempts:
                return _failed_step(
                    step,
                    error_code=last_error_code or "EXECUTION_STEP_FAILED",
                    error_message=last_error_message or "Retry limit reached.",
                    retryable=False,
                    attempts=prior_attempts,
                    started_at=started_at,
                )
            logger.info(
                "execution_retry execution_id=%s step_id=%s attempt=%s",
                request.identity.execution_id,
                step.step_id,
                attempt_number + 1,
            )

    def _result(
        self,
        request: ExecutionRequest,
        step_results: list[ExecutionStepResult],
        metrics: ExecutionRunMetrics,
    ) -> ExecutionResult:
        return ExecutionResult(
            execution_id=request.identity.execution_id,
            company_id=request.identity.company_id,
            status=request.status,
            step_results=step_results,
            completed_at=request.completed_at,
            failure_reason=request.failure_reason,
            metrics=metrics,
        )


def _max_attempts(step: ExecutionStep, policy: ExecutionRuntimePolicy) -> int:
    if step.retry_policy is not None:
        return min(step.retry_policy.max_attempts, policy.max_retries_per_step + 1)
    return max(1, min(policy.max_retries_per_step + 1, 5))


def _failed_step(
    step: ExecutionStep,
    *,
    error_code: str,
    error_message: str,
    retryable: bool,
    attempts: list[ExecutionAttempt],
    started_at: datetime,
) -> ExecutionStepResult:
    completed = _utcnow()
    return ExecutionStepResult(
        step_id=step.step_id,
        sequence=step.sequence,
        status="failed",
        tool_qualified_name=step.tool_qualified_name,
        error_code=error_code,
        error_message=error_message,
        retryable=retryable,
        started_at=started_at,
        completed_at=completed,
        duration_ms=None,
        attempts=attempts,
    )


def _ordered_results(
    steps: list[ExecutionStep],
    results_by_id: dict[str, ExecutionStepResult],
) -> list[ExecutionStepResult]:
    return [results_by_id[step.step_id] for step in steps if step.step_id in results_by_id]
