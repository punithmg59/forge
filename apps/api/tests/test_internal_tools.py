"""Internal read-only tool execution tests."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.schemas.tool import ToolCall
from app.services.tools.context import build_tool_execution_context
from app.services.tools.executor import ToolExecutor
from app.testing.seed_helpers import seed_company_with_evidence


@pytest.mark.asyncio
async def test_company_context_tool_returns_company_metadata(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, company, _, _ = await seed_company_with_evidence(
            session,
            name="Context Co",
        )
        context = build_tool_execution_context(
            membership,
            agent_type="test_agent",
            trace_id="trace-context",
        )
        executor = ToolExecutor(session, audit=False)
        result = await executor.execute(
            ToolCall(tool_name="company_context", tool_version="v1", input={}),
            context,
        )
        assert result.success is True
        assert result.data is not None
        assert result.data["company_id"] == str(company.id)
        assert result.data["name"] == "Context Co"
        assert result.data["stage"] == "mvp"


@pytest.mark.asyncio
async def test_objective_status_tool_returns_current_objective(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, _, objective, _ = await seed_company_with_evidence(
            session,
            name="Objective Co",
        )
        context = build_tool_execution_context(membership, agent_type="test_agent")
        executor = ToolExecutor(session, audit=False)
        result = await executor.execute(
            ToolCall(tool_name="objective_status", tool_version="v1", input={}),
            context,
        )
        assert result.success is True
        assert result.data is not None
        assert result.data["has_active_objective"] is True
        assert result.data["title"] == "Grow customers"
        assert result.data["objective_id"] == str(objective.id)


@pytest.mark.asyncio
async def test_customer_evidence_tool_returns_company_evidence(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, _, _, evidence = await seed_company_with_evidence(
            session,
            name="Evidence Co",
            evidence_title="Onboarding call",
            evidence_content="Users struggle with signup flow.",
        )
        context = build_tool_execution_context(membership, agent_type="test_agent")
        executor = ToolExecutor(session, audit=False)
        result = await executor.execute(
            ToolCall(
                tool_name="customer_evidence",
                tool_version="v1",
                input={"limit": 10},
            ),
            context,
        )
        assert result.success is True
        assert result.data is not None
        assert result.data["count"] == 1
        assert result.data["evidence"][0]["id"] == str(evidence.id)
        assert "signup" in result.data["evidence"][0]["content_preview"]


@pytest.mark.asyncio
async def test_cross_company_evidence_isolation(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership_a, company_a, _, evidence_a = await seed_company_with_evidence(
            session,
            name="Company A",
            evidence_title="A evidence",
            evidence_content="Company A secret",
        )
        membership_b, company_b, _, evidence_b = await seed_company_with_evidence(
            session,
            name="Company B",
            evidence_title="B evidence",
            evidence_content="Company B secret",
        )
        assert company_a.id != company_b.id
        context_a = build_tool_execution_context(membership_a, agent_type="test_agent")
        executor = ToolExecutor(session, audit=False)
        result_a = await executor.execute(
            ToolCall(tool_name="customer_evidence", tool_version="v1", input={}),
            context_a,
        )
        ids_a = {row["id"] for row in result_a.data["evidence"]}
        assert str(evidence_a.id) in ids_a
        assert str(evidence_b.id) not in ids_a
