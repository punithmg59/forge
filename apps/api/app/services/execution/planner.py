"""Enterprise execution planner. Plans read-only tool usage without executing."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from pydantic import ValidationError

from app.models.company_member import CompanyMember
from app.schemas.execution import (
    ExecutionPlan,
    ExecutionPlanningMetrics,
    ExecutionPlanningRequest,
    ExecutionPlanningResult,
    ExecutionStep,
    ExecutionStepCategory,
)
from app.schemas.tool import ToolEffect
from app.services.execution.approval_policy import apply_approval_policy_to_plan
from app.services.execution.errors import (
    ExecutionError,
    ExecutionPlanError,
    ExecutionScopeError,
)
from app.services.execution.plan_validation import validate_execution_plan
from app.services.execution.planner_prompt import build_planner_completion_request
from app.services.execution.policy import ExecutionRuntimePolicy
from app.services.llm import (
    LLMProvider,
    ProviderError,
    get_llm_provider,
)
from app.services.tools.registry import list_tools

logger = logging.getLogger(__name__)


class ExecutionPlanner:
    """
    Synthesizes safe, validated execution plans from founder goals.

    Hard architectural boundary:
    - NEVER executes tools
    - NEVER calls ToolExecutor
    - NEVER creates or modifies database records
    - NEVER approves its own plan
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        *,
        runtime_policy: ExecutionRuntimePolicy | None = None,
    ) -> None:
        self._llm = llm_provider
        self._policy = runtime_policy or ExecutionRuntimePolicy.default()

    async def plan(
        self,
        request: ExecutionPlanningRequest,
        membership: CompanyMember,
    ) -> ExecutionPlanningResult:
        """Transform a founder request into a validated, structured ExecutionPlan."""
        total_start = time.perf_counter()
        metrics = ExecutionPlanningMetrics()
        trace_id = request.trace_id or str(uuid.uuid4())

        # 1. Tenant Isolation
        if request.company_id != membership.company_id:
            raise ExecutionScopeError()

        # 2. Resolve Available Registered Read-Only Tools
        all_registered = list_tools(include_disabled=False)
        available_tools = [t for t in all_registered if t.effect is ToolEffect.READ]

        if request.available_tools:
            requested_names = set(request.available_tools)
            available_tools = [
                t
                for t in available_tools
                if t.qualified_name in requested_names or t.name in requested_names
            ]

        if not available_tools:
            metrics.total_ms = (time.perf_counter() - total_start) * 1000
            return ExecutionPlanningResult(
                decision="no_execution",
                reason="No enabled read-only tools available for planning.",
                planner_trace_id=trace_id,
                metrics=metrics,
            )

        # 3. LLM Completion
        llm = self._llm or get_llm_provider()
        completion_req = build_planner_completion_request(
            request,
            available_tools,
            timeout=30.0,
        )

        llm_start = time.perf_counter()
        try:
            completion_result = await llm.complete(completion_req)
            metrics.llm_ms = (time.perf_counter() - llm_start) * 1000
        except ProviderError as exc:
            metrics.llm_ms = (time.perf_counter() - llm_start) * 1000
            metrics.total_ms = (time.perf_counter() - total_start) * 1000
            safe_message = _sanitize_error_message(str(exc))
            logger.warning(
                "execution_planning_llm_failed company_id=%s trace_id=%s error=%s",
                membership.company_id,
                trace_id,
                safe_message,
            )
            return ExecutionPlanningResult(
                decision="plan_rejected",
                validation_errors=[safe_message],
                planner_trace_id=trace_id,
                metrics=metrics,
            )
        except Exception as exc:
            metrics.llm_ms = (time.perf_counter() - llm_start) * 1000
            metrics.total_ms = (time.perf_counter() - total_start) * 1000
            safe_message = _sanitize_error_message(str(exc))
            logger.warning(
                "execution_planning_unexpected_error company_id=%s trace_id=%s error=%s",
                membership.company_id,
                trace_id,
                safe_message,
            )
            return ExecutionPlanningResult(
                decision="plan_rejected",
                validation_errors=["LLM provider error occurred during planning."],
                planner_trace_id=trace_id,
                metrics=metrics,
            )

        # 4. Parse & Sanitize LLM Output
        raw_text = completion_result.text.strip()
        parsed_payload = _parse_json_payload(raw_text)
        if parsed_payload is None:
            metrics.total_ms = (time.perf_counter() - total_start) * 1000
            return ExecutionPlanningResult(
                decision="plan_rejected",
                validation_errors=["LLM returned invalid JSON payload."],
                planner_trace_id=trace_id,
                metrics=metrics,
            )

        decision = parsed_payload.get("decision")
        reason = parsed_payload.get("reason")

        if decision == "no_execution":
            metrics.total_ms = (time.perf_counter() - total_start) * 1000
            return ExecutionPlanningResult(
                decision="no_execution",
                reason=reason or "Execution is not required for this request.",
                planner_trace_id=trace_id,
                metrics=metrics,
            )

        raw_plan = parsed_payload.get("plan")
        if not isinstance(raw_plan, dict):
            metrics.total_ms = (time.perf_counter() - total_start) * 1000
            return ExecutionPlanningResult(
                decision="no_execution",
                reason="No execution steps were planned.",
                planner_trace_id=trace_id,
                metrics=metrics,
            )

        raw_steps = raw_plan.get("steps")
        if not isinstance(raw_steps, list) or len(raw_steps) == 0:
            metrics.total_ms = (time.perf_counter() - total_start) * 1000
            return ExecutionPlanningResult(
                decision="no_execution",
                reason="No execution steps were planned.",
                planner_trace_id=trace_id,
                metrics=metrics,
            )

        # 5. Construct Candidate Plan Structure
        candidate_plan, candidate_error = _construct_candidate_plan(
            raw_plan,
            fallback_goal=request.founder_question,
        )
        if candidate_plan is None:
            metrics.total_ms = (time.perf_counter() - total_start) * 1000
            return ExecutionPlanningResult(
                decision="plan_rejected",
                validation_errors=[candidate_error or "Malformed candidate plan."],
                planner_trace_id=trace_id,
                metrics=metrics,
            )

        # 6. Deterministic Validation & Policy Application
        validation_start = time.perf_counter()
        try:
            resolved_tools = validate_execution_plan(
                candidate_plan,
                runtime_policy=self._policy,
            )
            annotated_plan = apply_approval_policy_to_plan(candidate_plan, resolved_tools)
            metrics.validation_ms = (time.perf_counter() - validation_start) * 1000
        except (ExecutionPlanError, ExecutionError, ValidationError) as exc:
            metrics.validation_ms = (time.perf_counter() - validation_start) * 1000
            metrics.total_ms = (time.perf_counter() - total_start) * 1000
            safe_error = _sanitize_error_message(str(exc))
            return ExecutionPlanningResult(
                decision="plan_rejected",
                validation_errors=[safe_error],
                planner_trace_id=trace_id,
                metrics=metrics,
            )

        # 7. Success Result
        metrics.total_ms = (time.perf_counter() - total_start) * 1000
        logger.info(
            "execution_plan_ready company_id=%s trace_id=%s step_count=%d total_ms=%.1f",
            membership.company_id,
            trace_id,
            len(annotated_plan.steps),
            metrics.total_ms,
        )
        return ExecutionPlanningResult(
            decision="plan_ready",
            plan=annotated_plan,
            reason=reason or "Execution plan synthesized and validated successfully.",
            approval_required=True,
            planner_trace_id=trace_id,
            metrics=metrics,
        )


def _parse_json_payload(text: str) -> dict[str, Any] | None:
    """Safely parse JSON response from LLM, stripping markdown wrappers if present."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```").strip()
        fence = stripped.rfind("```")
        if fence != -1:
            stripped = stripped[:fence].strip()
    try:
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return None


def _construct_candidate_plan(
    raw_plan: dict[str, Any],
    *,
    fallback_goal: str,
) -> tuple[ExecutionPlan | None, str | None]:
    """Construct an initial ExecutionPlan from parsed dictionary, catching structural issues."""
    goal = str(raw_plan.get("goal") or fallback_goal).strip()
    rationale = str(raw_plan.get("rationale") or "Execution plan synthesized by planner.").strip()
    risk_level = str(raw_plan.get("risk_level") or "low").strip().lower()
    if risk_level not in {"low", "medium", "high", "critical"}:
        risk_level = "low"

    raw_steps = raw_plan.get("steps", [])
    candidate_steps: list[ExecutionStep] = []

    for idx, raw_step in enumerate(raw_steps, start=1):
        if not isinstance(raw_step, dict):
            return None, f"Step {idx} is not a valid object."

        step_id = str(raw_step.get("step_id") or f"step-{idx}").strip()
        sequence = raw_step.get("sequence", idx)
        if not isinstance(sequence, int) or sequence < 1:
            sequence = idx

        tool_name = str(raw_step.get("tool_name") or "").strip()
        tool_version = str(raw_step.get("tool_version") or "v1").strip()
        purpose = str(raw_step.get("purpose") or f"Execute {tool_name}").strip()
        input_data = raw_step.get("input", {})
        if not isinstance(input_data, dict):
            input_data = {}

        expected_output = raw_step.get("expected_output")
        if expected_output is not None:
            expected_output = str(expected_output).strip() or None

        step_risk = str(raw_step.get("risk_level") or "low").strip().lower()
        if step_risk not in {"low", "medium", "high", "critical"}:
            step_risk = "low"

        try:
            step = ExecutionStep(
                step_id=step_id,
                sequence=sequence,
                tool_name=tool_name,
                tool_version=tool_version,
                purpose=purpose,
                input=input_data,
                expected_output=expected_output,
                risk_level=step_risk,  # type: ignore[arg-type]
                step_category=ExecutionStepCategory.READ_ONLY_LOW_RISK,
                approval_required=True,
            )
            candidate_steps.append(step)
        except ValidationError as exc:
            return None, f"Step {step_id} validation error: {exc.errors()[0].get('msg', 'invalid')}"

    try:
        plan = ExecutionPlan(
            goal=goal[:2000],
            rationale=rationale[:4000],
            risk_level=risk_level,  # type: ignore[arg-type]
            steps=candidate_steps,
        )
        return plan, None
    except ValidationError as exc:
        return None, f"Plan validation error: {exc.errors()[0].get('msg', 'invalid')}"


def _sanitize_error_message(message: str) -> str:
    """Scrub potential credentials or sensitive tokens from error messages."""
    text = (message or "Planning error occurred.").strip()
    lowered = text.lower()
    for secret in ("api_key", "password", "secret", "authorization", "bearer ", "token="):
        if secret in lowered:
            return "Planning operation failed."
    return text[:500]
