"""Focused tests for Task 5.2 structured Company Brain retrieval."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.company import Company
from app.models.company_belief import CompanyBelief
from app.models.company_brain_profile import CompanyBrainProfile
from app.models.company_constraint import CompanyConstraint
from app.models.company_fact import CompanyFact
from app.models.company_member import CompanyMember
from app.models.decision import Decision
from app.models.evidence import Evidence
from app.models.experiment import Experiment
from app.models.learning import Learning
from app.models.memory import Memory
from app.models.objective import Objective
from app.models.user import User
from app.schemas.brain import CompanyContext, ContextBelief
from app.services.retrieval import (
    RetrievalAccessError,
    RetrievalScope,
    SqlStructuredRetriever,
    assemble_context,
)


async def _user(session: AsyncSession) -> User:
    user = User(email=f"retrieve-{uuid.uuid4()}@example.com", name="Retriever")
    session.add(user)
    await session.flush()
    return user


async def _company(session: AsyncSession, *, name: str, user: User) -> Company:
    company = Company(
        name=name,
        slug=f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}",
        mission=f"{name} mission",
        stage="mvp",
        product_description=f"{name} product",
    )
    session.add(company)
    await session.flush()
    session.add(CompanyMember(company_id=company.id, user_id=user.id, role="founder"))
    await session.flush()
    return company


def _scope(company: Company, user: User) -> RetrievalScope:
    return RetrievalScope(company_id=company.id, user_id=user.id, role="founder")


@pytest.mark.asyncio
async def test_retrieves_correct_company_brain(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="Alpha Brain", user=user)
        session.add(
            CompanyBrainProfile(
                company_id=company.id,
                current_bottlenecks="bandwidth",
                strategy="focus",
            )
        )
        session.add(
            CompanyFact(
                company_id=company.id,
                key="mrr",
                value="12000",
                value_type="number",
                source_type="manual",
                status="active",
            )
        )
        session.add(
            CompanyBelief(
                company_id=company.id,
                statement="Founders want speed",
                status="active",
            )
        )
        await session.commit()

        context = await SqlStructuredRetriever(session).retrieve(_scope(company, user))

    assert context.company is not None
    assert context.company.id == company.id
    assert context.company.name == "Alpha Brain"
    assert context.bottleneck == "bandwidth"
    assert context.facts[0].key == "mrr"
    assert context.beliefs[0].statement == "Founders want speed"
    assert context.memories == []
    assert context.meta is not None
    assert context.meta.structured_used is True
    assert context.meta.vector_used is False


@pytest.mark.asyncio
async def test_cross_company_data_is_never_returned(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        user_a = await _user(session)
        user_b = await _user(session)
        company_a = await _company(session, name="Tenant A", user=user_a)
        company_b = await _company(session, name="Tenant B", user=user_b)
        secret_key = f"secret-{uuid.uuid4().hex}"
        session.add(
            CompanyFact(
                company_id=company_a.id,
                key="a-only",
                value="alpha",
                value_type="string",
                source_type="manual",
                status="active",
            )
        )
        session.add(
            CompanyFact(
                company_id=company_b.id,
                key=secret_key,
                value="bravo",
                value_type="string",
                source_type="manual",
                status="active",
            )
        )
        session.add(
            CompanyBelief(
                company_id=company_b.id,
                statement="B belief must not leak",
                status="active",
            )
        )
        session.add(
            CompanyConstraint(
                company_id=company_b.id,
                type="budget",
                name="b-burn",
                severity="high",
                status="active",
            )
        )
        await session.commit()

        context = await SqlStructuredRetriever(session).retrieve(_scope(company_a, user_a))

    fact_keys = [fact.key for fact in context.facts]
    belief_texts = [belief.statement for belief in context.beliefs]
    constraint_names = [row.name for row in context.constraints]
    assert "a-only" in fact_keys
    assert secret_key not in fact_keys
    assert "B belief must not leak" not in belief_texts
    assert "b-burn" not in constraint_names
    assert context.company is not None
    assert context.company.id == company_a.id
    assert context.company.id != company_b.id


@pytest.mark.asyncio
async def test_forged_scope_cannot_read_another_company(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        user_a = await _user(session)
        user_b = await _user(session)
        await _company(session, name="Owner A", user=user_a)
        company_b = await _company(session, name="Owner B", user=user_b)
        session.add(
            CompanyFact(
                company_id=company_b.id,
                key="b-private",
                value="hidden",
                value_type="string",
                source_type="manual",
                status="active",
            )
        )
        await session.commit()
        forged = RetrievalScope(
            company_id=company_b.id,
            user_id=user_a.id,
            role="founder",
        )
        with pytest.raises(RetrievalAccessError):
            await SqlStructuredRetriever(session).retrieve(forged)


@pytest.mark.asyncio
async def test_facts_and_beliefs_remain_separate(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="Epistemology Co", user=user)
        session.add(
            CompanyFact(
                company_id=company.id,
                key="users",
                value="10",
                value_type="number",
                source_type="manual",
                status="active",
            )
        )
        session.add(
            CompanyBelief(
                company_id=company.id,
                statement="We believe CLI is better",
                status="active",
            )
        )
        await session.commit()
        context = await SqlStructuredRetriever(session).retrieve(_scope(company, user))

    assert "knowledge" not in CompanyContext.model_fields
    assert [fact.value for fact in context.facts] == ["10"]
    assert [belief.statement for belief in context.beliefs] == ["We believe CLI is better"]
    assert context.facts[0].key == "users"
    assert "key" not in ContextBelief.model_fields
    assert context.evidence == []


@pytest.mark.asyncio
async def test_retrieved_evidence_maps_to_evidence_section(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="Evidence Co", user=user)
        session.add(
            CompanyFact(
                company_id=company.id,
                key="users",
                value="10",
                value_type="number",
                source_type="manual",
                status="active",
            )
        )
        session.add(
            CompanyBelief(
                company_id=company.id,
                statement="We believe CLI is better",
                status="active",
            )
        )
        session.add(
            Evidence(
                company_id=company.id,
                type="interview",
                title="Founder interview",
                content="Onboarding was too long",
                source_type="customer_feedback",
                source_reference="notes",
                confidence=0.8,
                observed_at="2026-08-22T00:00:00Z",
            )
        )
        await session.commit()
        retrieved = await SqlStructuredRetriever(session).retrieve(_scope(company, user))
        assembled = assemble_context(retrieved, [], None)

    assert len(retrieved.evidence) == 1
    assert retrieved.evidence[0].title == "Founder interview"
    assert retrieved.evidence[0].provenance is not None
    assert retrieved.evidence[0].provenance.source_type == "customer_feedback"
    assert retrieved.evidence[0].provenance.source_reference == "notes"
    assert retrieved.evidence[0].provenance.observed_at == "2026-08-22T00:00:00Z"
    assert retrieved.facts[0].key == "users"
    assert retrieved.beliefs[0].statement == "We believe CLI is better"
    assert assembled.evidence[0].id == retrieved.evidence[0].id
    assert assembled.evidence[0].content == "Onboarding was too long"
    assert len(assembled.evidence) == 1
    evidence_sources = [s for s in retrieved.sources if s.entity_type == "evidence"]
    assert len(evidence_sources) == 1
    assert evidence_sources[0].entity_id == str(retrieved.evidence[0].id)


@pytest.mark.asyncio
async def test_active_objective_is_retrieved(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="Objectives Co", user=user)
        session.add(
            Objective(
                company_id=company.id,
                title="Old completed goal",
                status="completed",
                priority="low",
            )
        )
        await session.flush()
        session.add(
            Objective(
                company_id=company.id,
                title="Current active goal",
                status="active",
                priority="high",
            )
        )
        await session.commit()
        context = await SqlStructuredRetriever(session).retrieve(_scope(company, user))

    assert context.objective is not None
    assert context.objective.title == "Current active goal"
    assert context.objective.status == "active"


@pytest.mark.asyncio
async def test_active_constraints_are_retrieved(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="Constraints Co", user=user)
        session.add(
            CompanyConstraint(
                company_id=company.id,
                type="budget",
                name="retired-limit",
                severity="low",
                status="inactive",
            )
        )
        session.add(
            CompanyConstraint(
                company_id=company.id,
                type="budget",
                name="monthly-burn",
                value="5000",
                severity="high",
                status="active",
            )
        )
        await session.commit()
        context = await SqlStructuredRetriever(session).retrieve(_scope(company, user))

    names = [row.name for row in context.constraints]
    assert "monthly-burn" in names
    assert "retired-limit" not in names
    assert context.constraints[0].status == "active"


@pytest.mark.asyncio
async def test_recent_decisions_and_experiments_are_retrieved(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="Decisions Co", user=user)
        objective = Objective(
            company_id=company.id,
            title="Ship retrieval",
            status="active",
            priority="high",
        )
        session.add(objective)
        await session.flush()
        session.add(
            Decision(
                company_id=company.id,
                objective_id=objective.id,
                title="Use SQL first",
                decision="Structured retrieval before vectors",
                rationale="Deterministic context",
                status="active",
            )
        )
        session.add(
            Experiment(
                company_id=company.id,
                objective_id=objective.id,
                name="Onboarding A/B",
                description="Test shorter onboarding",
                status="planned",
            )
        )
        session.add(
            Learning(
                company_id=company.id,
                objective_id=objective.id,
                statement="Shorter onboarding helped",
                status="active",
            )
        )
        session.add(
            Evidence(
                company_id=company.id,
                type="interview",
                title="Founder interview",
                content="Onboarding was too long",
                source_type="customer_feedback",
                source_reference="notes",
            )
        )
        await session.commit()
        context = await SqlStructuredRetriever(session).retrieve(_scope(company, user))

    assert [row.title for row in context.decisions] == ["Use SQL first"]
    assert [row.name for row in context.experiments] == ["Onboarding A/B"]
    assert context.learnings[0].statement == "Shorter onboarding helped"
    assert len(context.evidence) == 1
    assert context.evidence[0].title == "Founder interview"
    assert context.evidence[0].content == "Onboarding was too long"
    assert context.evidence[0].type == "interview"
    assert context.evidence[0].provenance is not None
    assert context.evidence[0].provenance.source_type == "customer_feedback"
    assert context.evidence[0].provenance.source_reference == "notes"
    assert context.sources[0].entity_type == "evidence"
    assert context.sources[0].entity_id == str(context.evidence[0].id)
    assert context.sources[0].title == "Founder interview"


@pytest.mark.asyncio
async def test_empty_brain_returns_valid_empty_sections(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="Empty Brain", user=user)
        await session.commit()
        context = await SqlStructuredRetriever(session).retrieve(_scope(company, user))

    assert context.company is not None
    assert context.company.name == "Empty Brain"
    assert context.objective is None
    assert context.bottleneck is None
    assert context.constraints == []
    assert context.facts == []
    assert context.beliefs == []
    assert context.evidence == []
    assert context.decisions == []
    assert context.experiments == []
    assert context.learnings == []
    assert context.memories == []
    assert context.sources == []


@pytest.mark.asyncio
async def test_memories_are_not_retrieved(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="No Vectors Yet", user=user)
        session.add(
            Memory(
                company_id=company.id,
                memory_type="semantic",
                content="should not appear in structured retrieval",
                source_type="founder_input",
            )
        )
        await session.commit()
        context = await SqlStructuredRetriever(session).retrieve(_scope(company, user))

    assert context.memories == []
