"""Centralized tool permission enforcement."""

from __future__ import annotations

from app.schemas.tool import ToolExecutionContext, ToolPermission
from app.services.company_service import ROLE_ADMIN, ROLE_FOUNDER, ROLE_MEMBER
from app.services.tools.errors import ToolUnauthorizedError

_ALL_READ_PERMISSIONS = frozenset(ToolPermission)


def permissions_for_role(role: str) -> frozenset[ToolPermission]:
    if role in {ROLE_FOUNDER, ROLE_ADMIN}:
        return _ALL_READ_PERMISSIONS
    if role == ROLE_MEMBER:
        return frozenset(
            {
                ToolPermission.COMPANY_READ,
                ToolPermission.CUSTOMER_READ,
                ToolPermission.PRODUCT_READ,
                ToolPermission.ANALYTICS_READ,
            }
        )
    return frozenset({ToolPermission.COMPANY_READ})


def authorize_tool_execution(
    context: ToolExecutionContext,
    required_permissions: frozenset[ToolPermission],
) -> None:
    if not required_permissions:
        return
    if not required_permissions.issubset(context.permissions):
        raise ToolUnauthorizedError()
