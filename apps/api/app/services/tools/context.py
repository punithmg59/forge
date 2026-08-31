"""Build ToolExecutionContext from authenticated membership."""

from __future__ import annotations

import uuid

from app.models.company_member import CompanyMember
from app.schemas.tool import ToolExecutionContext
from app.services.tools.authorization import permissions_for_role


def build_tool_execution_context(
    membership: CompanyMember,
    *,
    agent_type: str,
    trace_id: str | None = None,
    request_id: str | None = None,
) -> ToolExecutionContext:
    return ToolExecutionContext(
        company_id=membership.company_id,
        user_id=membership.user_id,
        membership_role=membership.role,
        agent_type=agent_type,
        trace_id=trace_id or str(uuid.uuid4()),
        request_id=request_id,
        permissions=permissions_for_role(membership.role),
    )
