"""Execution lifecycle state machine validation."""

from __future__ import annotations

from app.schemas.execution import (
    EXECUTION_STEP_TERMINAL_STATUSES,
    EXECUTION_TERMINAL_STATUSES,
    ExecutionStatus,
    ExecutionStepStatus,
)
from app.services.execution.errors import ExecutionStateError

_EXECUTION_TRANSITIONS: dict[ExecutionStatus, frozenset[ExecutionStatus]] = {
    "requested": frozenset({"planned", "cancelled"}),
    "planned": frozenset({"waiting_for_approval", "approved", "cancelled"}),
    "waiting_for_approval": frozenset({"approved", "cancelled", "failed"}),
    "approved": frozenset({"running", "cancelled"}),
    "running": frozenset({"succeeded", "failed", "cancelled", "retrying"}),
    "retrying": frozenset({"running", "failed", "cancelled"}),
    "succeeded": frozenset(),
    "failed": frozenset({"retrying", "cancelled"}),
    "cancelled": frozenset(),
}

_STEP_TRANSITIONS: dict[ExecutionStepStatus, frozenset[ExecutionStepStatus]] = {
    "pending": frozenset({"waiting_for_approval", "approved", "running", "skipped", "cancelled"}),
    "waiting_for_approval": frozenset({"approved", "cancelled", "failed"}),
    "approved": frozenset({"running", "cancelled"}),
    "running": frozenset({"succeeded", "failed", "cancelled"}),
    "succeeded": frozenset(),
    "failed": frozenset({"running", "cancelled"}),
    "skipped": frozenset(),
    "cancelled": frozenset(),
}


def validate_execution_status_transition(
    current_status: ExecutionStatus,
    next_status: ExecutionStatus,
) -> None:
    if current_status == next_status:
        return
    if current_status in EXECUTION_TERMINAL_STATUSES:
        raise ExecutionStateError(
            f"Execution is terminal in status '{current_status}' and cannot transition."
        )
    allowed = _EXECUTION_TRANSITIONS.get(current_status, frozenset())
    if next_status not in allowed:
        raise ExecutionStateError(
            f"Cannot transition execution from '{current_status}' to '{next_status}'."
        )


def validate_step_status_transition(
    current_status: ExecutionStepStatus,
    next_status: ExecutionStepStatus,
) -> None:
    if current_status == next_status:
        return
    if current_status in EXECUTION_STEP_TERMINAL_STATUSES:
        raise ExecutionStateError(
            f"Execution step is terminal in status '{current_status}' and cannot transition."
        )
    allowed = _STEP_TRANSITIONS.get(current_status, frozenset())
    if next_status not in allowed:
        raise ExecutionStateError(
            f"Cannot transition execution step from '{current_status}' to '{next_status}'."
        )


def can_retry_execution(
    status: ExecutionStatus,
    attempt_count: int,
    max_attempts: int,
) -> bool:
    return status == "failed" and attempt_count < max_attempts


def is_execution_terminal(status: ExecutionStatus) -> bool:
    return status in EXECUTION_TERMINAL_STATUSES
