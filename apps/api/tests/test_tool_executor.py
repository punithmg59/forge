"""Tool executor boundary tests."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.schemas.tool import ToolCall, ToolCategory, ToolEffect, ToolExecutionContext, ToolPermission
from app.services.tools.base import Tool
from app.services.tools.context import build_tool_execution_context
from app.services.tools.executor import ToolExecutor
from app.services.tools.policy import ToolExecutionPolicy
from app.services.tools.registry import register, unregister
from app.testing.seed_helpers import seed_company_with_evidence


class _SlowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    delay_ms: int = 100


class _SlowOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool = True


class _SlowTool(Tool[_SlowInput, _SlowOutput]):
    @property
    def name(self) -> str:
        return "slow_tool"

    @property
    def version(self) -> str:
        return "v1"

    @property
    def description(self) -> str:
        return "slow tool"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SYSTEM

    @property
    def effect(self) -> ToolEffect:
        return ToolEffect.READ

    @property
    def required_permissions(self) -> frozenset[ToolPermission]:
        return frozenset({ToolPermission.COMPANY_READ})

    @property
    def timeout_ms(self) -> int | None:
        return 50

    @property
    def input_model(self) -> type[_SlowInput]:
        return _SlowInput

    @property
    def output_model(self) -> type[_SlowOutput]:
        return _SlowOutput

    async def execute(self, db, context, validated_input):  # noqa: ANN001
        await asyncio.sleep(validated_input.delay_ms / 1000.0)
        return _SlowOutput()


@pytest.mark.asyncio
async def test_invalid_input_rejected(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, _, _, _ = await seed_company_with_evidence(session, name="Input Co")
        context = build_tool_execution_context(membership, agent_type="test_agent")
        executor = ToolExecutor(session, audit=False)
        result = await executor.execute(
            ToolCall(
                tool_name="customer_evidence",
                tool_version="v1",
                input={"limit": 0},
            ),
            context,
        )
        assert result.success is False
        assert result.error_code == "TOOL_INVALID_INPUT"


@pytest.mark.asyncio
async def test_extra_input_fields_rejected(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, _, _, _ = await seed_company_with_evidence(session, name="Extra Co")
        context = build_tool_execution_context(membership, agent_type="test_agent")
        executor = ToolExecutor(session, audit=False)
        result = await executor.execute(
            ToolCall(
                tool_name="company_context",
                tool_version="v1",
                input={"company_id": "malicious"},
            ),
            context,
        )
        assert result.success is False
        assert result.error_code == "TOOL_INVALID_INPUT"


@pytest.mark.asyncio
async def test_timeout_returns_safe_error(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    register(_SlowTool())
    async with async_session_factory() as session:
        membership, _, _, _ = await seed_company_with_evidence(session, name="Timeout Co")
        context = build_tool_execution_context(membership, agent_type="test_agent")
        executor = ToolExecutor(session, audit=False)
        result = await executor.execute(
            ToolCall(
                tool_name="slow_tool",
                tool_version="v1",
                input={"delay_ms": 200},
            ),
            context,
        )
        assert result.success is False
        assert result.error_code == "TOOL_TIMEOUT"
        assert result.error_message == "Tool execution timed out."
    unregister("slow_tool:v1")


@pytest.mark.asyncio
async def test_output_size_limit_enforced(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, _, _, _ = await seed_company_with_evidence(
            session,
            name="Large Co",
            evidence_content="x" * 100000,
        )
        context = build_tool_execution_context(membership, agent_type="test_agent")
        policy = ToolExecutionPolicy(
            max_calls_per_request=10,
            max_total_execution_ms=30000,
            default_timeout_ms=5000,
            external_timeout_ms=15000,
            max_input_bytes=8192,
            max_output_bytes=200,
            max_records=100,
        )
        executor = ToolExecutor(session, policy=policy, audit=False)
        result = await executor.execute(
            ToolCall(tool_name="customer_evidence", tool_version="v1", input={}),
            context,
        )
        assert result.success is False
        assert result.error_code == "TOOL_RESULT_TOO_LARGE"


@pytest.mark.asyncio
async def test_per_request_call_limit(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, _, _, _ = await seed_company_with_evidence(session, name="Limit Co")
        context = build_tool_execution_context(membership, agent_type="test_agent")
        policy = ToolExecutionPolicy(
            max_calls_per_request=1,
            max_total_execution_ms=30000,
            default_timeout_ms=5000,
            external_timeout_ms=15000,
            max_input_bytes=8192,
            max_output_bytes=65536,
            max_records=100,
        )
        executor = ToolExecutor(session, policy=policy, audit=False)
        first = await executor.execute(
            ToolCall(tool_name="company_context", tool_version="v1", input={}),
            context,
        )
        second = await executor.execute(
            ToolCall(tool_name="company_context", tool_version="v1", input={}),
            context,
        )
        assert first.success is True
        assert second.success is False
        assert second.error_code == "TOOL_POLICY_LIMIT"
