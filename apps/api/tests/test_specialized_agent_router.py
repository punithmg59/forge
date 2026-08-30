"""Task 9.2 specialized agent routing tests."""

from __future__ import annotations

import ast
import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.agent_run import AgentRun
from app.models.company import Company
from app.models.company_member import CompanyMember
from app.models.user import User
from app.schemas.brain import CompanyContext, ContextCompany
from app.schemas.specialized_agent_types import AgentDomain, SpecializedAgentType
from app.schemas.specialized_routing_types import RoutingIntent
from app.services.llm import CompletionResult, LLMProvider
from app.services.specialized_agents import get_specialized_agent
from app.services.specialized_agents.routing import (
    classify_deterministic,
    classify_with_llm,
    route_specialized_agent,
)
from app.services.specialized_agents.routing.errors import InvalidClassification
from app.services.specialized_agents.routing.llm_classifier import (
    classification_to_decision,
    _parse_classification_text,
)


class _StubProvider(LLMProvider):
    name = "stub"

    def __init__(self, response_text: str) -> None:
        self.complete_mock = AsyncMock(
            return_value=CompletionResult(text=response_text, model="stub-model")
        )
        self.embed_mock = AsyncMock()

    async def complete(self, request):  # noqa: ANN001
        return await self.complete_mock(request)

    async def embed(self, request):  # noqa: ANN001
        return await self.embed_mock(request)


def _company_context(company_id: uuid.UUID, name: str) -> CompanyContext:
    return CompanyContext(company=ContextCompany(id=company_id, name=name, stage="mvp"))


async def _seed_membership(
    session: AsyncSession,
    *,
    company_name: str,
) -> tuple[CompanyMember, Company]:
    user = User(email=f"route-{uuid.uuid4()}@example.com", name="Router User")
    session.add(user)
    await session.flush()
    company = Company(name=company_name, slug=f"route-{uuid.uuid4().hex[:8]}", stage="mvp")
    session.add(company)
    await session.flush()
    membership = CompanyMember(
        company_id=company.id,
        user_id=user.id,
        role="founder",
    )
    session.add(membership)
    await session.flush()
    return membership, company


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("How do we improve customer acquisition?", RoutingIntent.CUSTOMER_ACQUISITION),
        ("We need a customer interview plan.", RoutingIntent.CUSTOMER_INTERVIEWS),
        ("How can we improve customer retention?", RoutingIntent.CUSTOMER_RETENTION),
        ("What should our product roadmap look like?", RoutingIntent.PRODUCT_ROADMAP),
        ("Which product feature should we build next?", RoutingIntent.PRODUCT_FEATURES),
        ("How should we handle feature prioritization this quarter?", RoutingIntent.PRODUCT_PRIORITIZATION),
    ],
)
def test_deterministic_routes_domain_questions(question: str, intent: RoutingIntent) -> None:
    result = classify_deterministic(question)
    assert result.decision is not None
    assert result.decision.routing_method == "deterministic"
    assert result.decision.intent == intent
    assert result.decision.confidence == "high"
    assert not result.decision.fallback_to_head_agent


def test_customer_acquisition_routes_to_customer_growth() -> None:
    result = classify_deterministic("How do we get more customers through acquisition?")
    assert result.decision is not None
    assert result.decision.selected_agent == SpecializedAgentType.CUSTOMER_GROWTH
    assert result.decision.domain == AgentDomain.CUSTOMER_GROWTH


def test_product_roadmap_routes_to_product() -> None:
    result = classify_deterministic("Let's plan our product roadmap for next quarter.")
    assert result.decision is not None
    assert result.decision.selected_agent == SpecializedAgentType.PRODUCT
    assert result.decision.domain == AgentDomain.PRODUCT


def test_strong_deterministic_route_skips_llm() -> None:
    provider = _StubProvider("{}")
    result = classify_deterministic("How do we improve customer acquisition?")
    assert result.decision is not None
    assert result.decision.routing_method == "deterministic"
    provider.complete_mock.assert_not_called()


@pytest.mark.asyncio
async def test_route_specialized_agent_strong_match_no_llm(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, company = await _seed_membership(session, company_name="No LLM Co")
        provider = _StubProvider("{}")

        async def _builder(db, membership=membership, query=""):  # noqa: ARG001
            return _company_context(company.id, company.name)

        handoff = await route_specialized_agent(
            session,
            membership=membership,
            question="How do we improve customer acquisition?",
            context_builder=_builder,
            provider_factory=lambda: provider,
        )
        provider.complete_mock.assert_not_called()
        assert handoff.decision.selected_agent == SpecializedAgentType.CUSTOMER_GROWTH
        assert handoff.context is not None
        assert handoff.context.scope.company_id == membership.company_id


@pytest.mark.asyncio
async def test_ambiguous_question_falls_back_without_llm(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, _ = await _seed_membership(session, company_name="Ambiguous Co")
        provider = _StubProvider("{}")

        handoff = await route_specialized_agent(
            session,
            membership=membership,
            question="What should we do next?",
            include_context=False,
            provider_factory=lambda: provider,
        )
        provider.complete_mock.assert_not_called()
        assert handoff.decision.fallback_to_head_agent
        assert handoff.decision.selected_agent is None
        assert handoff.decision.confidence == "low"
        assert handoff.context is None


@pytest.mark.asyncio
async def test_weak_match_uses_llm_classifier() -> None:
    payload = json.dumps(
        {
            "intent": "growth",
            "agent_type": "customer_growth",
            "confidence": "medium",
            "reason": "Question concerns growth but lacked strong keywords.",
        }
    )
    provider = _StubProvider(payload)
    decision = await classify_with_llm(
        "How do we grow?",
        provider_factory=lambda: provider,
    )
    assert decision.routing_method == "llm"
    assert decision.selected_agent == SpecializedAgentType.CUSTOMER_GROWTH
    provider.complete_mock.assert_awaited_once()


def test_llm_classifier_structured_output() -> None:
    classification = _parse_classification_text(
        json.dumps(
            {
                "intent": "product_features",
                "agent_type": "product",
                "confidence": "high",
                "reason": "Explicit product feature question.",
            }
        )
    )
    decision = classification_to_decision(classification)
    assert decision.selected_agent == SpecializedAgentType.PRODUCT
    assert decision.intent == RoutingIntent.PRODUCT_FEATURES


def test_invalid_llm_output_raises() -> None:
    with pytest.raises(InvalidClassification):
        _parse_classification_text("not json")


def test_low_confidence_llm_falls_back_to_head_agent() -> None:
    classification = _parse_classification_text(
        json.dumps(
            {
                "intent": "customer_acquisition",
                "agent_type": "customer_growth",
                "confidence": "low",
                "reason": "Uncertain classification.",
            }
        )
    )
    decision = classification_to_decision(classification)
    assert decision.fallback_to_head_agent
    assert decision.selected_agent is None


def test_prompt_injection_llm_classifies_safely() -> None:
    classification = _parse_classification_text(
        json.dumps(
            {
                "intent": "general",
                "agent_type": "none",
                "confidence": "low",
                "reason": "Injection attempt; no semantic specialist intent.",
            }
        )
    )
    decision = classification_to_decision(classification)
    assert decision.fallback_to_head_agent
    assert decision.selected_agent is None


def test_unknown_intent_in_llm_output_fails_validation() -> None:
    with pytest.raises(InvalidClassification):
        _parse_classification_text(
            json.dumps(
                {
                    "intent": "finance",
                    "agent_type": "none",
                    "confidence": "low",
                    "reason": "unknown",
                }
            )
        )


def test_safe_fallback_on_general_intent() -> None:
    result = classify_deterministic("What should we do next?")
    assert result.decision is not None
    assert result.decision.fallback_to_head_agent
    assert result.decision.intent == RoutingIntent.GENERAL


@pytest.mark.asyncio
async def test_tenant_scope_on_context_handoff(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership_a, company_a = await _seed_membership(session, company_name="Tenant A")
        membership_b, company_b = await _seed_membership(session, company_name="Tenant B")

        async def _builder_a(db, membership=membership_a, query=""):  # noqa: ARG001
            return _company_context(company_a.id, "Tenant A")

        async def _builder_b(db, membership=membership_b, query=""):  # noqa: ARG001
            return _company_context(company_b.id, "Tenant B")

        handoff_a = await route_specialized_agent(
            session,
            membership=membership_a,
            question="How do we improve customer acquisition?",
            context_builder=_builder_a,
        )
        handoff_b = await route_specialized_agent(
            session,
            membership=membership_b,
            question="What is our product roadmap?",
            context_builder=_builder_b,
        )
        assert handoff_a.context is not None
        assert handoff_b.context is not None
        assert handoff_a.context.scope.company_id == company_a.id
        assert handoff_b.context.scope.company_id == company_b.id
        assert handoff_a.context.company is not None
        assert handoff_a.context.company.name == "Tenant A"
        assert handoff_b.context.company is not None
        assert handoff_b.context.company.name == "Tenant B"


@pytest.mark.asyncio
async def test_route_does_not_execute_specialist_reasoning(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, company = await _seed_membership(session, company_name="No Reason Co")

        async def _builder(db, membership=membership, query=""):  # noqa: ARG001
            return _company_context(company.id, company.name)

        runs_before = await session.scalar(select(func.count()).select_from(AgentRun))

        handoff = await route_specialized_agent(
            session,
            membership=membership,
            question="How do we improve customer acquisition?",
            context_builder=_builder,
        )

        runs_after = await session.scalar(select(func.count()).select_from(AgentRun))
        assert handoff.decision.selected_agent == SpecializedAgentType.CUSTOMER_GROWTH
        assert runs_before == runs_after


@pytest.mark.asyncio
async def test_route_does_not_mutate_company(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, company = await _seed_membership(session, company_name="Immutable Route Co")
        original = company.name

        async def _builder(db, membership=membership, query=""):  # noqa: ARG001
            return _company_context(company.id, company.name)

        await route_specialized_agent(
            session,
            membership=membership,
            question="How do we improve customer acquisition?",
            context_builder=_builder,
        )
        await session.refresh(company)
        assert company.name == original


def test_routing_modules_do_not_import_newtron() -> None:
    root = Path(__file__).resolve().parents[1] / "app" / "services" / "specialized_agents" / "routing"
    forbidden = ("newtron", "NewtronProvider")
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(token in alias.name for token in forbidden)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(token in node.module for token in forbidden)


def test_deterministic_routing_is_fast() -> None:
    import time

    start = time.perf_counter()
    for _ in range(100):
        classify_deterministic("How do we improve customer acquisition?")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 500
