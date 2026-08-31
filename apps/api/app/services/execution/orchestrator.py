"""Execution foundation orchestrator — validates boundaries, does not execute."""

from __future__ import annotations

import logging
import uuid

from app.models.company_member import CompanyMember
from app.schemas.execution import ExecutionPlan, ExecutionRequest
from app.services.execution.approval_policy import apply_approval_policy_to_plan
from app.services.execution.errors import ExecutionNotImplementedError
from app.services.execution.identity import assert_execution_tenant, new_execution_identity
from app.services.execution.plan_validation import validate_execution_plan
from app.services.execution.policy import ExecutionRuntimePolicy
from app.services.execution.state import validate_execution_status_transition

logger = logging.getLogger(__name__)


class ExecutionFoundationOrchestrator:
    """
    Architectural boundary for controlled autonomous execution.

    Task 9.8.1: validates requests and plans only.
    Does NOT call ToolExecutor.execute() or mutate company state.
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

    async def run_execution(self, request: ExecutionRequest) -> None:
        """Explicitly not implemented in Task 9.8.1."""
        logger.info(
            "execution_run_blocked execution_id=%s status=%s",
            request.identity.execution_id,
            request.status,
        )
        raise ExecutionNotImplementedError()

    async def execute_step(self, request: ExecutionRequest, step_id: str) -> None:
        """Explicitly not implemented in Task 9.8.1."""
        raise ExecutionNotImplementedError()

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
