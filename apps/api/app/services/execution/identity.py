"""Server-side execution identity construction."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.models.company_member import CompanyMember
from app.schemas.execution import ExecutionIdentity


def new_execution_identity(
    membership: CompanyMember,
    *,
    agent_type: str,
    objective_id: uuid.UUID | None = None,
    objective_task_id: uuid.UUID | None = None,
    trace_id: str | None = None,
    execution_id: uuid.UUID | None = None,
) -> ExecutionIdentity:
    """Build execution identity from authenticated membership — never from agent input."""
    return ExecutionIdentity(
        execution_id=execution_id or uuid.uuid4(),
        company_id=membership.company_id,
        objective_id=objective_id,
        objective_task_id=objective_task_id,
        agent_type=agent_type.strip(),
        requested_by=membership.user_id,
        trace_id=trace_id or str(uuid.uuid4()),
        created_at=datetime.now(UTC),
    )


def assert_execution_tenant(
    identity: ExecutionIdentity,
    membership: CompanyMember,
) -> None:
    from app.services.execution.errors import ExecutionScopeError

    if identity.company_id != membership.company_id:
        raise ExecutionScopeError()
