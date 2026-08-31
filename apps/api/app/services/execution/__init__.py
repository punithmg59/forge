"""Controlled autonomous execution foundation."""

from __future__ import annotations

from app.services.execution.audit import (
    EXECUTION_PLAN_TASK_TYPE,
    EXECUTION_RUNNER_AGENT_TYPE,
    EXECUTION_STATUS_TASK_TYPE,
    new_execution_plan_task,
    new_execution_run,
    new_execution_status_task,
)
from app.services.execution.errors import (
    ExecutionError,
    ExecutionNotApprovedError,
    ExecutionRunnerError,
)
from app.services.execution.identity import assert_execution_tenant, new_execution_identity
from app.services.execution.orchestrator import ExecutionFoundationOrchestrator
from app.services.execution.plan_validation import validate_execution_plan
from app.services.execution.policy import ExecutionRuntimePolicy
from app.services.execution.runner import ExecutionRunner
from app.services.execution.state import (
    can_retry_execution,
    is_execution_terminal,
    validate_execution_status_transition,
    validate_step_status_transition,
)

__all__ = [
    "EXECUTION_PLAN_TASK_TYPE",
    "EXECUTION_RUNNER_AGENT_TYPE",
    "EXECUTION_STATUS_TASK_TYPE",
    "ExecutionError",
    "ExecutionFoundationOrchestrator",
    "ExecutionNotApprovedError",
    "ExecutionRunner",
    "ExecutionRunnerError",
    "ExecutionRuntimePolicy",
    "assert_execution_tenant",
    "can_retry_execution",
    "is_execution_terminal",
    "new_execution_identity",
    "new_execution_plan_task",
    "new_execution_run",
    "new_execution_status_task",
    "validate_execution_plan",
    "validate_execution_status_transition",
    "validate_step_status_transition",
]
