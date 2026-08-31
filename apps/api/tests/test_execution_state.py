"""Execution state machine tests."""

from __future__ import annotations

import pytest

from app.services.execution.errors import ExecutionStateError
from app.services.execution.state import (
    can_retry_execution,
    is_execution_terminal,
    validate_execution_status_transition,
    validate_step_status_transition,
)


def test_execution_happy_path_transitions() -> None:
    validate_execution_status_transition("requested", "planned")
    validate_execution_status_transition("planned", "waiting_for_approval")
    validate_execution_status_transition("waiting_for_approval", "approved")
    validate_execution_status_transition("approved", "running")
    validate_execution_status_transition("running", "succeeded")


def test_execution_failure_and_retry_path() -> None:
    validate_execution_status_transition("running", "failed")
    validate_execution_status_transition("failed", "retrying")
    validate_execution_status_transition("retrying", "running")


def test_execution_terminal_states_reject_transitions() -> None:
    with pytest.raises(ExecutionStateError):
        validate_execution_status_transition("succeeded", "running")
    with pytest.raises(ExecutionStateError):
        validate_execution_status_transition("cancelled", "planned")


def test_invalid_execution_transition_rejected() -> None:
    with pytest.raises(ExecutionStateError):
        validate_execution_status_transition("requested", "running")


def test_step_transitions_and_terminal() -> None:
    validate_step_status_transition("pending", "running")
    validate_step_status_transition("running", "succeeded")
    with pytest.raises(ExecutionStateError):
        validate_step_status_transition("succeeded", "running")


def test_retry_helpers() -> None:
    assert can_retry_execution("failed", attempt_count=1, max_attempts=3) is True
    assert can_retry_execution("failed", attempt_count=3, max_attempts=3) is False
    assert is_execution_terminal("succeeded") is True
    assert is_execution_terminal("running") is False
