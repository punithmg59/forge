"""Comprehensive database tests for Task 2 models."""

import uuid

import pytest
from sqlalchemy import text

from app.models.agent_run import AgentRun
from app.models.agent_task import AgentTask
from app.models.approval import Approval
from app.models.artifact import Artifact
from app.models.company import Company
from app.models.company_belief import CompanyBelief
from app.models.company_brain_profile import CompanyBrainProfile
from app.models.company_constraint import CompanyConstraint
from app.models.company_fact import CompanyFact
from app.models.company_member import CompanyMember
from app.models.decision import Decision
from app.models.evidence import Evidence
from app.models.experiment import Experiment
from app.models.experiment_result import ExperimentResult
from app.models.hypothesis import Hypothesis
from app.models.integration import Integration
from app.models.learning import Learning
from app.models.memory import Memory
from app.models.metric import Metric
from app.models.metric_observation import MetricObservation
from app.models.objective import Objective
from app.models.objective_task import ObjectiveTask
from app.models.user import User


@pytest.mark.asyncio
async def test_company_creation(async_session_factory) -> None:
    """Test company creation."""
    async with async_session_factory() as session:
        company = Company(
            name=f"Test Company {uuid.uuid4()}",
            slug=f"test-company-{uuid.uuid4()}",
            mission="Test mission",
            stage="MVP",
        )
        session.add(company)
        await session.commit()
        await session.refresh(company)

        assert company.id is not None
        assert company.name.startswith("Test Company")


@pytest.mark.asyncio
async def test_company_brain_profile_creation(async_session_factory) -> None:
    """Test company brain profile creation."""
    async with async_session_factory() as session:
        company = Company(name=f"Test {uuid.uuid4()}", slug=f"test-{uuid.uuid4()}")
        session.add(company)
        await session.flush()

        profile = CompanyBrainProfile(
            company_id=company.id,
            strategy="Test strategy",
            version=1,
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

        assert profile.id is not None
        assert profile.company_id == company.id


@pytest.mark.asyncio
async def test_company_fact_creation(async_session_factory) -> None:
    """Test company fact creation."""
    async with async_session_factory() as session:
        company = Company(name=f"Test {uuid.uuid4()}", slug=f"test-{uuid.uuid4()}")
        session.add(company)
        await session.flush()

        fact = CompanyFact(
            company_id=company.id,
            key=f"test_key_{uuid.uuid4()}",
            value="test_value",
            value_type="string",
            source_type="manual",
            status="active",
        )
        session.add(fact)
        await session.commit()
        await session.refresh(fact)

        assert fact.id is not None
        assert fact.key.startswith("test_key_")


@pytest.mark.asyncio
async def test_company_belief_creation(async_session_factory) -> None:
    """Test company belief creation."""
    async with async_session_factory() as session:
        company = Company(name=f"Test {uuid.uuid4()}", slug=f"test-{uuid.uuid4()}")
        session.add(company)
        await session.flush()

        belief = CompanyBelief(
            company_id=company.id,
            statement=f"Test belief {uuid.uuid4()}",
            status="active",
        )
        session.add(belief)
        await session.commit()
        await session.refresh(belief)

        assert belief.id is not None
        assert belief.statement.startswith("Test belief")


@pytest.mark.asyncio
async def test_objective_hypothesis_relationship(async_session_factory) -> None:
    """Test objective -> hypothesis relationship."""
    async with async_session_factory() as session:
        company = Company(name=f"Test {uuid.uuid4()}", slug=f"test-{uuid.uuid4()}")
        session.add(company)
        await session.flush()

        objective = Objective(
            company_id=company.id,
            title=f"Test Objective {uuid.uuid4()}",
            status="active",
            priority="high",
        )
        session.add(objective)
        await session.flush()

        hypothesis = Hypothesis(
            company_id=company.id,
            objective_id=objective.id,
            statement=f"Test hypothesis {uuid.uuid4()}",
            status="active",
        )
        session.add(hypothesis)
        await session.commit()
        await session.refresh(hypothesis)

        assert hypothesis.objective_id == objective.id


@pytest.mark.asyncio
async def test_objective_task_relationship(async_session_factory) -> None:
    """Test objective -> task relationship."""
    async with async_session_factory() as session:
        company = Company(name=f"Test {uuid.uuid4()}", slug=f"test-{uuid.uuid4()}")
        session.add(company)
        await session.flush()

        objective = Objective(
            company_id=company.id,
            title=f"Test Objective {uuid.uuid4()}",
            status="active",
            priority="high",
        )
        session.add(objective)
        await session.flush()

        task = ObjectiveTask(
            company_id=company.id,
            objective_id=objective.id,
            title=f"Test Task {uuid.uuid4()}",
            capability="engineering",
            status="pending",
            priority="medium",
            requires_approval=False,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)

        assert task.objective_id == objective.id


@pytest.mark.asyncio
async def test_experiment_result_relationship(async_session_factory) -> None:
    """Test experiment -> result relationship."""
    async with async_session_factory() as session:
        company = Company(name=f"Test {uuid.uuid4()}", slug=f"test-{uuid.uuid4()}")
        session.add(company)
        await session.flush()

        objective = Objective(
            company_id=company.id,
            title=f"Test Objective {uuid.uuid4()}",
            status="active",
            priority="high",
        )
        session.add(objective)
        await session.flush()

        experiment = Experiment(
            company_id=company.id,
            objective_id=objective.id,
            name=f"Test Experiment {uuid.uuid4()}",
            status="planned",
        )
        session.add(experiment)
        await session.flush()

        result = ExperimentResult(
            experiment_id=experiment.id,
            company_id=company.id,
            metric_name=f"test_metric_{uuid.uuid4()}",
            result_value="100",
            recorded_at="2026-08-22T00:00:00Z",
        )
        session.add(result)
        await session.commit()
        await session.refresh(result)

        assert result.experiment_id == experiment.id


@pytest.mark.asyncio
async def test_decision_creation(async_session_factory) -> None:
    """Test decision creation."""
    async with async_session_factory() as session:
        company = Company(name=f"Test {uuid.uuid4()}", slug=f"test-{uuid.uuid4()}")
        session.add(company)
        await session.flush()

        decision = Decision(
            company_id=company.id,
            title=f"Test Decision {uuid.uuid4()}",
            decision="Test decision text",
            rationale="Test rationale",
            status="active",
        )
        session.add(decision)
        await session.commit()
        await session.refresh(decision)

        assert decision.id is not None
        assert decision.title.startswith("Test Decision")


@pytest.mark.asyncio
async def test_learning_creation(async_session_factory) -> None:
    """Test learning creation."""
    async with async_session_factory() as session:
        company = Company(name=f"Test {uuid.uuid4()}", slug=f"test-{uuid.uuid4()}")
        session.add(company)
        await session.flush()

        learning = Learning(
            company_id=company.id,
            statement=f"Test learning {uuid.uuid4()}",
            status="active",
        )
        session.add(learning)
        await session.commit()
        await session.refresh(learning)

        assert learning.id is not None
        assert learning.statement.startswith("Test learning")


@pytest.mark.asyncio
async def test_evidence_creation(async_session_factory) -> None:
    """Test evidence creation."""
    async with async_session_factory() as session:
        company = Company(name=f"Test {uuid.uuid4()}", slug=f"test-{uuid.uuid4()}")
        session.add(company)
        await session.flush()

        evidence = Evidence(
            company_id=company.id,
            type="customer_feedback",
            title=f"Test Evidence {uuid.uuid4()}",
            content="Test content",
            source_type="manual",
        )
        session.add(evidence)
        await session.commit()
        await session.refresh(evidence)

        assert evidence.id is not None
        assert evidence.title.startswith("Test Evidence")


@pytest.mark.asyncio
async def test_memory_with_vector_field(async_session_factory) -> None:
    """Test memory with vector field."""
    async with async_session_factory() as session:
        company = Company(name=f"Test {uuid.uuid4()}", slug=f"test-{uuid.uuid4()}")
        session.add(company)
        await session.flush()

        memory = Memory(
            company_id=company.id,
            memory_type="semantic",
            content=f"Test memory content {uuid.uuid4()}",
            embedding=None,  # Nullable for now
            source_type="manual",
        )
        session.add(memory)
        await session.commit()
        await session.refresh(memory)

        assert memory.id is not None
        assert memory.memory_type == "semantic"


@pytest.mark.asyncio
async def test_agent_run_creation(async_session_factory) -> None:
    """Test agent run creation."""
    async with async_session_factory() as session:
        company = Company(name=f"Test {uuid.uuid4()}", slug=f"test-{uuid.uuid4()}")
        session.add(company)
        await session.flush()

        agent_run = AgentRun(
            company_id=company.id,
            agent_type="head_agent",
            status="completed",
        )
        session.add(agent_run)
        await session.commit()
        await session.refresh(agent_run)

        assert agent_run.id is not None
        assert agent_run.agent_type == "head_agent"


@pytest.mark.asyncio
async def test_approval_creation(async_session_factory) -> None:
    """Test approval creation."""
    async with async_session_factory() as session:
        company = Company(name=f"Test {uuid.uuid4()}", slug=f"test-{uuid.uuid4()}")
        session.add(company)
        await session.flush()

        approval = Approval(
            company_id=company.id,
            action_type="code_change",
            description=f"Test approval {uuid.uuid4()}",
            risk_level="low",
            status="pending",
            requested_at="2026-08-22T00:00:00Z",
        )
        session.add(approval)
        await session.commit()
        await session.refresh(approval)

        assert approval.id is not None
        assert approval.status == "pending"


@pytest.mark.asyncio
async def test_metric_observation_relationship(async_session_factory) -> None:
    """Test metric -> observation relationship."""
    async with async_session_factory() as session:
        company = Company(name=f"Test {uuid.uuid4()}", slug=f"test-{uuid.uuid4()}")
        session.add(company)
        await session.flush()

        metric = Metric(
            company_id=company.id,
            name=f"test_metric_{uuid.uuid4()}",
        )
        session.add(metric)
        await session.flush()

        observation = MetricObservation(
            company_id=company.id,
            metric_id=metric.id,
            value="100",
            observed_at="2026-08-22T00:00:00Z",
        )
        session.add(observation)
        await session.commit()
        await session.refresh(observation)

        assert observation.metric_id == metric.id


@pytest.mark.asyncio
async def test_company_isolation(async_session_factory) -> None:
    """Test company isolation - records from Company A cannot be retrieved by Company B."""
    async with async_session_factory() as session:
        # Create Company A and a fact
        company_a = Company(name=f"Company A {uuid.uuid4()}", slug=f"company-a-{uuid.uuid4()}")
        session.add(company_a)
        await session.flush()

        fact_a = CompanyFact(
            company_id=company_a.id,
            key="secret",
            value="company_a_secret",
            value_type="string",
            source_type="manual",
            status="active",
        )
        session.add(fact_a)
        await session.commit()
        company_a_id = company_a.id

    # Create Company B in a new session
    async with async_session_factory() as session:
        company_b = Company(name=f"Company B {uuid.uuid4()}", slug=f"company-b-{uuid.uuid4()}")
        session.add(company_b)
        await session.commit()
        company_b_id = company_b.id

    # Query facts for Company B - should not see Company A's facts
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT * FROM company_facts WHERE company_id = :company_id"),
            {"company_id": company_b_id},
        )
        facts_b = result.fetchall()
        assert len(facts_b) == 0

        # Verify Company A's fact exists
        result = await session.execute(
            text("SELECT * FROM company_facts WHERE company_id = :company_id"),
            {"company_id": company_a_id},
        )
        facts_a = result.fetchall()
        assert len(facts_a) == 1
        assert facts_a[0].key == "secret"

