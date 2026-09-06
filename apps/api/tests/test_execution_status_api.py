"""Execution status API contract tests."""

from __future__ import annotations

import uuid

from app.schemas.execution import ExecutionStatusResponse


def test_execution_status_response_contract():
    """ExecutionStatusResponse schema validates correctly."""
    execution_id = uuid.uuid4()
    company_id = uuid.uuid4()

    response = ExecutionStatusResponse(
        execution_id=execution_id,
        company_id=company_id,
        objective_id=None,
        objective_task_id=None,
        agent_type="execution_runner",
        requested_by=uuid.uuid4(),
        trace_id="test-trace",
        status="running",
        created_at="2024-01-01T00:00:00Z",
        started_at="2024-01-01T00:00:01Z",
        completed_at=None,
        failure_reason=None,
        cancel_reason=None,
        plan=None,
        plan_fingerprint=None,
        approval_status=None,
        approval_expires_at=None,
        step_results=[],
        metrics=None,
    )

    assert response.execution_id == execution_id
    assert response.company_id == company_id
    assert response.status == "running"
    assert response.agent_type == "execution_runner"


def test_execution_status_response_all_statuses():
    """ExecutionStatusResponse accepts all valid statuses."""
    execution_id = uuid.uuid4()
    company_id = uuid.uuid4()

    for status in ["requested", "planned", "waiting_for_approval", "approved", "running", "succeeded", "failed", "cancelled", "retrying"]:
        response = ExecutionStatusResponse(
            execution_id=execution_id,
            company_id=company_id,
            objective_id=None,
            objective_task_id=None,
            agent_type="execution_runner",
            requested_by=uuid.uuid4(),
            trace_id="test-trace",
            status=status,  # type: ignore
            created_at="2024-01-01T00:00:00Z",
            started_at=None,
            completed_at=None,
            failure_reason=None,
            cancel_reason=None,
            plan=None,
            plan_fingerprint=None,
            approval_status=None,
            approval_expires_at=None,
            step_results=[],
            metrics=None,
        )
        assert response.status == status
