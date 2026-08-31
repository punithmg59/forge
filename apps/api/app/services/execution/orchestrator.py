"""Orchestrates execution planning and approved read-only runs."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_member import CompanyMember
from app.schemas.execution import (
    ExecutionPlan,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStepResult,
)
from app.services.execution.approval_policy import apply_approval_policy_to_plan
from app.services.execution.errors import ExecutionRunnerError
from app.services.execution.identity import assert_execution_tenant, new_execution_identity
from app.services.execution.plan_validation import validate_execution_plan
from app.services.execution.policy import ExecutionRuntimePolicy
from app.services.execution.runner import ExecutionRunner
from app.services.execution.state import validate_execution_status_transition
from app.services.tools.executor import ToolExecutor


class ExecutionFoundationOrchestrator:
    """
    Architectural boundary for controlled autonomous execution.

    Plans are validated here. Tool execution is delegated to ExecutionRunner
    and may only proceed after persisted founder approval.
    """

    def __init__(
        self,
        *,
        runtime_policy: ExecutionRuntimePolicy | None = None,
    ) -> None:
        self._policy = runtime_policy or ExecutionRuntimePolicy.default()

    def build_request(
        self,
        membership: CompanyMember,
        *,
        agent_type: str,
        objective_id: uuid.UUID | None = None,
        objective_task_id: uuid.UUID | None = None,
        trace_id: str | None = None,
    ) -> ExecutionRequest:
        identity = new_execution_identity(
            membership,
            agent_type=agent_type,
            objective_id=objective_id,
            objective_task_id=objective_task_id,
            trace_id=trace_id,
        )
        return ExecutionRequest(identity=identity, status="requested")

    def validate_request_scope(
        self,
        request: ExecutionRequest,
        membership: CompanyMember,
    ) -> None:
        assert_execution_tenant(request.identity, membership)

    def validate_status_transition(
        self,
        request: ExecutionRequest,
        next_status: str,
    ) -> None:
        validate_execution_status_transition(request.status, next_status)

    def validate_and_annotate_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        tools = validate_execution_plan(plan, runtime_policy=self._policy)
        return apply_approval_policy_to_plan(plan, tools)

    def attach_plan(
        self,
        request: ExecutionRequest,
        plan: ExecutionPlan,
        membership: CompanyMember,
    ) -> ExecutionRequest:
        self.validate_request_scope(request, membership)
        annotated = self.validate_and_annotate_plan(plan)
        validate_execution_status_transition(request.status, "planned")
        return request.model_copy(update={"plan": annotated, "status": "planned"})

    async def run_execution(
        self,
        request: ExecutionRequest,
        membership: CompanyMember,
        *,
        db: AsyncSession,
        plan_agent_task_id: uuid.UUID,
        prior_results: list[ExecutionStepResult] | None = None,
        agent_run_id: uuid.UUID | None = None,
        tool_executor: ToolExecutor | None = None,
    ) -> ExecutionResult:
        """Run an approved plan through ToolExecutor. Does not self-approve."""
        executor = tool_executor or ToolExecutor(db)
        runner = ExecutionRunner(db, tool_executor=executor, runtime_policy=self._policy)
        return await runner.run(
            request,
            membership,
            plan_agent_task_id=plan_agent_task_id,
            prior_results=prior_results,
            agent_run_id=agent_run_id,
        )

    async def execute_step(self, request: ExecutionRequest, step_id: str) -> None:
        raise ExecutionRunnerError("Individual step execution is not exposed.")

    async def cancel_execution(
        self,
        request: ExecutionRequest,
        membership: CompanyMember,
        reason: str,
    ) -> ExecutionRequest:
        self.validate_request_scope(request, membership)
        validate_execution_status_transition(request.status, "cancelled")
        return request.model_copy(
            update={"status": "cancelled", "cancel_reason": reason.strip()},
        )
