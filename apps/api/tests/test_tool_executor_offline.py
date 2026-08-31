"""Tool executor tests that do not require a database connection."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.schemas.tool import ToolCall, ToolExecutionContext, ToolPermission
from app.services.tools.executor import ToolExecutor
from app.services.tools.policy import ToolExecutionPolicy
from app.services.tools.registry import disable_tool, enable_tool


@pytest.mark.asyncio
async def test_unknown_tool_rejected_without_database() -> None:
    db = AsyncMock()
    context = ToolExecutionContext(
        company_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        membership_role="founder",
        agent_type="offline_test",
        trace_id="trace-offline-unknown",
        permissions=frozenset(ToolPermission),
    )
    result = await ToolExecutor(db, audit=False).execute(
        ToolCall(tool_name="stripe_revenue", tool_version="v1", input={}),
        context,
    )
    assert result.success is False
    assert result.error_code == "TOOL_NOT_FOUND"
    db.get.assert_not_called()


@pytest.mark.asyncio
async def test_unauthorized_execution_without_database() -> None:
    db = AsyncMock()
    context = ToolExecutionContext(
        company_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        membership_role="founder",
        agent_type="offline_test",
        trace_id="trace-offline-unauth",
        permissions=frozenset(),
    )
    result = await ToolExecutor(db, audit=False).execute(
        ToolCall(tool_name="company_context", tool_version="v1", input={}),
        context,
    )
    assert result.success is False
    assert result.error_code == "TOOL_UNAUTHORIZED"


@pytest.mark.asyncio
async def test_disabled_tool_rejected_without_database() -> None:
    disable_tool("company_context:v1")
    db = AsyncMock()
    context = ToolExecutionContext(
        company_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        membership_role="founder",
        agent_type="offline_test",
        trace_id="trace-offline-disabled",
        permissions=frozenset(ToolPermission),
    )
    result = await ToolExecutor(db, audit=False).execute(
        ToolCall(tool_name="company_context", tool_version="v1", input={}),
        context,
    )
    assert result.success is False
    assert result.error_code == "TOOL_DISABLED"
    enable_tool("company_context:v1")


@pytest.mark.asyncio
async def test_policy_limit_without_database() -> None:
    db = AsyncMock()
    context = ToolExecutionContext(
        company_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        membership_role="founder",
        agent_type="offline_test",
        trace_id="trace-offline-policy",
        permissions=frozenset(ToolPermission),
    )
    policy = ToolExecutionPolicy(
        max_calls_per_request=0,
        max_total_execution_ms=30000,
        default_timeout_ms=5000,
        external_timeout_ms=15000,
        max_input_bytes=8192,
        max_output_bytes=65536,
        max_records=100,
    )
    result = await ToolExecutor(db, policy=policy, audit=False).execute(
        ToolCall(tool_name="company_context", tool_version="v1", input={}),
        context,
    )
    assert result.success is False
    assert result.error_code == "TOOL_POLICY_LIMIT"
