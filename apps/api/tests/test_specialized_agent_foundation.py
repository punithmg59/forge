"""Task 9.1 specialized agent foundation tests."""

from __future__ import annotations

import ast
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.company import Company
from app.models.company_member import CompanyMember
from app.models.user import User
from app.schemas.brain import (
    CompanyContext,
    ContextCompany,
    ContextFact,
    ContextObjective,
    ContextSource,
)
from app.schemas.head_agent import ProposedAction
from app.schemas.specialized_agent import SpecializedAgentRecommendation
from app.services.brain_context import BrainContextError
from app.services.retrieval.scope import RetrievalScope
from app.services.specialized_agents import (
    AgentDomain,
    CustomerGrowthAgent,
    ProductAgent,
    SPECIALIZED_AGENT_TASK_TYPE,
    SpecializedAgentScopeError,
    UnknownSpecializedAgent,
    assert_scope_matches_membership,
    build_specialized_agent_context,
    domain_for_agent_type,
    get_specialized_agent,
    ground_specialized_recommendation,
    new_specialized_agent_run,
    new_specialized_agent_task,
    parse_agent_type,
    parse_domain,
    parse_specialized_recommendation_payload,
    registered_agent_types,
)
from app.schemas.specialized_agent_types import SpecializedAgentType
from app.services.specialized_agents.customer_growth_agent import CustomerGrowthAgentError
from app.services.specialized_agents.product_agent import ProductAgentError
from app.services.specialized_agents.errors import (
    SpecializedAgentContextError,
)


def _company_context(
    *,
    company_id: uuid.UUID,
    company_name: str = "Scope Co",
) -> CompanyContext:
    fact_id = uuid.uuid4()
    return CompanyContext(
        company=ContextCompany(id=company_id, name=company_name, stage="mvp"),
        objective=ContextObjective(
            id=uuid.uuid4(),
            title="Grow customers",
            status="active",
            priority="300",
        ),
        facts=[ContextFact(id=fact_id, key="customers", value="10")],
        sources=[
            ContextSource(
                entity_type="fact",
                entity_id=str(fact_id),
                source_type="manual",
            )
        ],
    )


async def _seed_membership(
    session: AsyncSession,
    *,
    company_name: str,
) -> tuple[CompanyMember, Company]:
    user = User(email=f"spec-{uuid.uuid4()}@example.com", name="Spec User")
    session.add(user)
    await session.flush()
    company = Company(name=company_name, slug=f"spec-{uuid.uuid4().hex[:8]}", stage="mvp")
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


def test_agent_type_identifiers() -> None:
    assert SpecializedAgentType.CUSTOMER_GROWTH.value == "customer_growth"
    assert SpecializedAgentType.PRODUCT.value == "product"
    assert parse_agent_type("customer_growth") == SpecializedAgentType.CUSTOMER_GROWTH
    assert parse_agent_type("PRODUCT") == SpecializedAgentType.PRODUCT


def test_domain_identifiers() -> None:
    assert AgentDomain.CUSTOMER_GROWTH.value == "customer_growth"
    assert AgentDomain.PRODUCT.value == "product"
    assert parse_domain("product") == AgentDomain.PRODUCT
    assert domain_for_agent_type(SpecializedAgentType.PRODUCT) == AgentDomain.PRODUCT


def test_domain_intents_are_centralized() -> None:
    agent = CustomerGrowthAgent()
    assert "customer_acquisition" in agent.supported_intents
    assert "marketing" in agent.supported_intents
    product = ProductAgent()
    assert "product_roadmap" in product.supported_intents
    assert "ux" in product.supported_intents
    assert "product_features" in product.supported_intents


def test_registry_lookup_returns_agents() -> None:
    growth = get_specialized_agent("customer_growth")
    product = get_specialized_agent(SpecializedAgentType.PRODUCT)
    assert growth.agent_type == SpecializedAgentType.CUSTOMER_GROWTH
    assert product.agent_type == SpecializedAgentType.PRODUCT
    assert registered_agent_types() == frozenset(
        {SpecializedAgentType.CUSTOMER_GROWTH, SpecializedAgentType.PRODUCT}
    )


def test_registry_unknown_agent_raises() -> None:
    with pytest.raises(UnknownSpecializedAgent) as exc_info:
        get_specialized_agent("finance")
    assert exc_info.value.status_code == 404
    assert "finance" in exc_info.value.detail


def test_agent_contract_metadata() -> None:
    agent = CustomerGrowthAgent()
    assert agent.display_name == "Customer & Growth"
    assert agent.domain == AgentDomain.CUSTOMER_GROWTH
    assert "customer discovery" in agent.description.lower()
    product = ProductAgent()
    assert product.display_name == "Product"
    assert product.domain == AgentDomain.PRODUCT
    assert "roadmap" in product.description.lower()


def test_context_contract_maps_company_context() -> None:
    company_id = uuid.uuid4()
    scope = RetrievalScope(company_id=company_id, user_id=uuid.uuid4(), role="founder")
    brain = _company_context(company_id=company_id)
    context = build_specialized_agent_context(
        scope=scope,
        domain=AgentDomain.CUSTOMER_GROWTH,
        company_context=brain,
    )
    assert context.domain == AgentDomain.CUSTOMER_GROWTH
    assert context.company is not None
    assert context.company.name == "Scope Co"
    assert len(context.facts) == 1
    assert len(context.sources) >= 1
    assert context.scope.company_id == company_id


def test_scope_mismatch_raises() -> None:
    scope = RetrievalScope(company_id=uuid.uuid4(), user_id=uuid.uuid4(), role="founder")
    with pytest.raises(SpecializedAgentScopeError):
        assert_scope_matches_membership(
            scope,
            company_id=uuid.uuid4(),
            user_id=scope.user_id,
        )


@pytest.mark.asyncio
async def test_retrieve_context_propagates_membership_scope(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, company = await _seed_membership(session, company_name="Retrieve Co")
        brain = _company_context(company_id=company.id, company_name="Retrieve Co")
        agent = get_specialized_agent("customer_growth")

        async def _builder(db, membership=membership, query=""):  # noqa: ARG001
            return brain

        context = await agent.retrieve_context(
            session,
            membership=membership,
            query="Who are our customers?",
            context_builder=_builder,
        )
        assert context.scope.company_id == membership.company_id
        assert context.scope.user_id == membership.user_id
        assert context.company is not None
        assert context.company.id == company.id


@pytest.mark.asyncio
async def test_retrieve_context_maps_brain_context_error(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, _ = await _seed_membership(session, company_name="Error Co")
        agent = get_specialized_agent("product")

        async def _fail(db, membership=membership, query=""):  # noqa: ARG001
            raise BrainContextError("Brain context retrieval failed", 502)

        with pytest.raises(SpecializedAgentContextError) as exc_info:
            await agent.retrieve_context(
                session,
                membership=membership,
                query="roadmap?",
                context_builder=_fail,
            )
        assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_tenant_isolation_context_scope(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership_a, company_a = await _seed_membership(session, company_name="Tenant A")
        membership_b, company_b = await _seed_membership(session, company_name="Tenant B")
        brain_a = _company_context(company_id=company_a.id, company_name="Tenant A")
        brain_b = _company_context(company_id=company_b.id, company_name="Tenant B")
        agent = get_specialized_agent("customer_growth")

        async def _builder_a(db, membership=membership_a, query=""):  # noqa: ARG001
            return brain_a

        async def _builder_b(db, membership=membership_b, query=""):  # noqa: ARG001
            return brain_b

        context_a = await agent.retrieve_context(
            session,
            membership=membership_a,
            query="customers",
            context_builder=_builder_a,
        )
        context_b = await agent.retrieve_context(
            session,
            membership=membership_b,
            query="customers",
            context_builder=_builder_b,
        )
        assert context_a.scope.company_id == company_a.id
        assert context_b.scope.company_id == company_b.id
        assert context_a.company is not None and context_a.company.name == "Tenant A"
        assert context_b.company is not None and context_b.company.name == "Tenant B"
        assert context_a.scope.company_id != context_b.scope.company_id


@pytest.mark.asyncio
async def test_product_recommend_requires_non_empty_question(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, _ = await _seed_membership(session, company_name="No LLM Co")
        agent = get_specialized_agent("product")
        provider_factory = MagicMock()

        with pytest.raises(ProductAgentError):
            await agent.recommend(
                session,
                membership=membership,
                question="",
                provider_factory=provider_factory,
            )
        provider_factory.assert_not_called()


def test_product_build_prompt_returns_completion_request() -> None:
    agent = ProductAgent()
    scope = RetrievalScope(company_id=uuid.uuid4(), user_id=uuid.uuid4(), role="founder")
    context = build_specialized_agent_context(
        scope=scope,
        domain=AgentDomain.PRODUCT,
        company_context=_company_context(company_id=scope.company_id),
    )
    request = agent.build_prompt(question="roadmap?", context=context)
    assert request.response_format == "json_object"
    assert len(request.messages) == 2


def test_structured_output_validation() -> None:
    recommendation = parse_specialized_recommendation_payload(
        {
            "title": "Validate ICP",
            "recommendation": "Interview more customers.",
            "rationale": "Sparse customer evidence.",
            "proposed_action": {"type": "task", "title": "Interview", "description": "10 calls"},
            "sources": [],
            "confidence": "medium",
        }
    )
    assert recommendation.title == "Validate ICP"
    assert recommendation.proposed_action.type == "task"


def test_grounding_contract_filters_unknown_sources() -> None:
    company_id = uuid.uuid4()
    brain = _company_context(company_id=company_id)
    scope = RetrievalScope(company_id=company_id, user_id=uuid.uuid4(), role="founder")
    context = build_specialized_agent_context(
        scope=scope,
        domain=AgentDomain.CUSTOMER_GROWTH,
        company_context=brain,
    )
    recommendation = SpecializedAgentRecommendation(
        title="Test",
        recommendation="Grounded",
        rationale="Because",
        proposed_action=ProposedAction(type="none"),
        sources=[
            ContextSource(entity_type="fact", entity_id=str(brain.facts[0].id)),
            ContextSource(entity_type="fact", entity_id=str(uuid.uuid4())),
        ],
        confidence="high",
    )
    grounded = ground_specialized_recommendation(recommendation, context)
    assert len(grounded.sources) == 1
    assert grounded.confidence == "high"


def test_audit_contract_uses_existing_tables() -> None:
    company_id = uuid.uuid4()
    objective_id = uuid.uuid4()
    run = new_specialized_agent_run(
        company_id=company_id,
        agent_type=SpecializedAgentType.CUSTOMER_GROWTH,
        objective_id=objective_id,
    )
    assert run.agent_type == "customer_growth"
    assert run.company_id == company_id
    assert run.objective_id == objective_id
    assert run.status == "running"
    assert run.trace_id is not None

    recommendation = parse_specialized_recommendation_payload(
        {
            "title": "Audit",
            "recommendation": "Proposal only",
            "rationale": "Not brain truth",
            "proposed_action": {"type": "none"},
            "sources": [],
            "confidence": "low",
        }
    )
    task = new_specialized_agent_task(
        company_id=company_id,
        agent_run=run,
        agent_type=SpecializedAgentType.CUSTOMER_GROWTH,
        domain=AgentDomain.CUSTOMER_GROWTH,
        question="growth?",
        recommendation=recommendation,
    )
    assert task.agent_type == "customer_growth"
    assert task.task_type == SPECIALIZED_AGENT_TASK_TYPE
    assert task.input is not None and task.input["domain"] == "customer_growth"
    assert task.output is not None and task.output["title"] == "Audit"


def test_specialized_modules_do_not_import_newtron_provider() -> None:
    root = Path(__file__).resolve().parents[1] / "app" / "services" / "specialized_agents"
    forbidden = ("newtron", "NewtronProvider")
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(token in alias.name for token in forbidden)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(token in node.module for token in forbidden)


@pytest.mark.asyncio
async def test_retrieve_context_does_not_mutate_company_state(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        membership, company = await _seed_membership(session, company_name="Immutable Co")
        original_name = company.name
        brain = _company_context(company_id=company.id, company_name=original_name)
        agent = get_specialized_agent("customer_growth")

        async def _builder(db, membership=membership, query=""):  # noqa: ARG001
            return brain

        await agent.retrieve_context(
            session,
            membership=membership,
            query="customers",
            context_builder=_builder,
        )
        await session.refresh(company)
        assert company.name == original_name

        with pytest.raises(CustomerGrowthAgentError):
            await agent.recommend(
                session,
                membership=membership,
                question="",
                provider_factory=AsyncMock(),
            )

        await session.refresh(company)
        assert company.name == original_name
