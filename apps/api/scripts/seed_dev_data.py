"""Development seed data script.

This script is for development only and creates sample data for testing.
"""

import asyncio
import uuid

from app.core.security import hash_password
from app.db.session import async_session_factory
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


async def seed_dev_data() -> None:
    """Seed development data."""
    async with async_session_factory() as session:
        # Create user
        user = User(
            email="founder@forge.dev",
            name="Forge Founder",
            password_hash=hash_password("forge-dev-password"),
        )
        session.add(user)
        await session.flush()

        # Create company
        company = Company(
            name="Forge Demo Company",
            slug="forge-demo",
            mission="Help ambitious founders operate their startups with AI leverage.",
            vision="Every founder has an AI co-founder.",
            product_description="AI operating system for solo technical founders.",
            target_customer="Solo technical founders and 1-5 person software startups.",
            stage="MVP",
        )
        session.add(company)
        await session.flush()

        # Create company member
        member = CompanyMember(
            company_id=company.id,
            user_id=user.id,
            role="founder",
        )
        session.add(member)
        await session.flush()

        # Create brain profile
        brain_profile = CompanyBrainProfile(
            company_id=company.id,
            strategy="Focus on technical founders through developer communities",
            non_goals="Enterprise sales, B2B partnerships, non-technical markets",
            current_priorities="User acquisition, product stability, documentation",
            current_bottlenecks="Limited engineering bandwidth, need more user feedback",
            working_style="Agile with weekly sprints, async-first communication",
            version=1,
        )
        session.add(brain_profile)
        await session.flush()

        # Create fact
        fact = CompanyFact(
            company_id=company.id,
            key="registered_users",
            value="1240",
            value_type="number",
            source_type="analytics",
            source_reference="mixpanel",
            confidence=0.95,
            status="active",
            observed_at="2026-08-22T00:00:00Z",
        )
        session.add(fact)
        await session.flush()

        # Create belief
        belief = CompanyBelief(
            company_id=company.id,
            statement="Technical founders prefer CLI tools over GUI dashboards",
            reasoning="Based on user interviews and GitHub activity patterns",
            confidence=0.8,
            status="active",
            source="founder_input",
        )
        session.add(belief)
        await session.flush()

        # Create constraint
        constraint = CompanyConstraint(
            company_id=company.id,
            type="budget",
            name="monthly_burn",
            description="Monthly budget constraint",
            value="50000",
            severity="medium",
            status="active",
        )
        session.add(constraint)
        await session.flush()

        # Create objective
        objective = Objective(
            company_id=company.id,
            title="Get the first 20 paying customers",
            description="Acquire 20 paying customers to validate product-market fit",
            status="active",
            priority="high",
            target_value="20",
            target_unit="customers",
            deadline="2026-12-31",
            created_by=user.id,
        )
        session.add(objective)
        await session.flush()

        # Create hypothesis
        hypothesis = Hypothesis(
            company_id=company.id,
            objective_id=objective.id,
            statement="Simplifying founder onboarding will improve activation",
            reasoning="Complex onboarding is a common friction point",
            confidence=0.7,
            status="active",
        )
        session.add(hypothesis)
        await session.flush()

        # Create objective task
        objective_task = ObjectiveTask(
            company_id=company.id,
            objective_id=objective.id,
            hypothesis_id=hypothesis.id,
            title="Simplify onboarding flow",
            description="Reduce steps from signup to first successful AI interaction",
            capability="product",
            status="pending",
            priority="high",
            assigned_agent="head_agent",
            requires_approval=False,
        )
        session.add(objective_task)
        await session.flush()

        # Create decision
        decision = Decision(
            company_id=company.id,
            objective_id=objective.id,
            title="Focus initial distribution on technical founders",
            decision="Prioritize developer communities over general startup forums",
            rationale="Technical founders are our ideal customer profile",
            expected_outcome="Higher conversion rates from targeted communities",
            status="active",
            confidence=0.85,
            created_by=user.id,
        )
        session.add(decision)
        await session.flush()

        # Create experiment
        experiment = Experiment(
            company_id=company.id,
            objective_id=objective.id,
            hypothesis_id=hypothesis.id,
            name="Onboarding simplification test",
            description="Test simplified onboarding vs current flow",
            method="A/B test",
            primary_metric="activation_rate",
            target_value="0.4",
            status="planned",
        )
        session.add(experiment)
        await session.flush()

        # Create experiment result
        experiment_result = ExperimentResult(
            experiment_id=experiment.id,
            company_id=company.id,
            metric_name="activation_rate",
            baseline_value="0.25",
            result_value="0.35",
            unit="percentage",
            interpretation="40% improvement in activation rate",
            success=True,
            recorded_at="2026-08-22T00:00:00Z",
        )
        session.add(experiment_result)
        await session.flush()

        # Create learning
        learning = Learning(
            company_id=company.id,
            objective_id=objective.id,
            experiment_id=experiment.id,
            statement="Reducing onboarding steps from 5 to 3 increases activation by 40%",
            evidence_summary="A/B test showed significant improvement",
            confidence=0.9,
            status="active",
        )
        session.add(learning)
        await session.flush()

        # Create evidence
        evidence = Evidence(
            company_id=company.id,
            type="customer_feedback",
            title="User feedback on onboarding",
            content="Onboarding was confusing, too many steps",
            source_type="customer_feedback",
            source_reference="intercom",
            confidence=0.8,
            observed_at="2026-08-22T00:00:00Z",
        )
        session.add(evidence)
        await session.flush()

        # Create memory
        memory = Memory(
            company_id=company.id,
            memory_type="semantic",
            content="Technical founders value CLI tools and automation",
            embedding=None,  # Will be populated when embedding generation is implemented
            source_type="founder_input",
            source_reference="internal",
            importance=0.8,
            confidence=0.85,
        )
        session.add(memory)
        await session.flush()

        # Create agent run
        agent_run = AgentRun(
            company_id=company.id,
            agent_type="head_agent",
            objective_id=objective.id,
            task_id=objective_task.id,
            status="completed",
            model_provider="openai",
            model_name="gpt-4",
            input_tokens=1500,
            output_tokens=800,
            estimated_cost=0.05,
            started_at="2026-08-22T00:00:00Z",
            completed_at="2026-08-22T00:05:00Z",
            trace_id="trace_12345",
        )
        session.add(agent_run)
        await session.flush()

        # Create agent task
        agent_task = AgentTask(
            company_id=company.id,
            agent_run_id=agent_run.id,
            objective_task_id=objective_task.id,
            agent_type="head_agent",
            task_type="analysis",
            status="completed",
            input={"task": "analyze onboarding"},
            output={"recommendation": "simplify flow"},
            cost=0.05,
            started_at="2026-08-22T00:00:00Z",
            completed_at="2026-08-22T00:05:00Z",
        )
        session.add(agent_task)
        await session.flush()

        # Create approval
        approval = Approval(
            company_id=company.id,
            agent_task_id=agent_task.id,
            action_type="code_change",
            description="Proposed onboarding simplification changes",
            risk_level="low",
            status="approved",
            requested_at="2026-08-22T00:00:00Z",
            resolved_at="2026-08-22T00:10:00Z",
            resolved_by=user.id,
        )
        session.add(approval)
        await session.flush()

        # Create integration
        integration = Integration(
            company_id=company.id,
            provider="github",
            integration_type="code_repository",
            status="active",
            scopes=["read", "write"],
            meta={"repo": "forge/forge"},
        )
        session.add(integration)
        await session.flush()

        # Create metric
        metric = Metric(
            company_id=company.id,
            name="activation_rate",
            description="Percentage of users who complete onboarding",
            source="analytics",
            unit="percentage",
            target_value="0.4",
        )
        session.add(metric)
        await session.flush()

        # Create metric observation
        metric_observation = MetricObservation(
            company_id=company.id,
            metric_id=metric.id,
            value="0.35",
            observed_at="2026-08-22T00:00:00Z",
            source_reference="mixpanel",
        )
        session.add(metric_observation)
        await session.flush()

        # Create artifact
        artifact = Artifact(
            company_id=company.id,
            agent_task_id=agent_task.id,
            artifact_type="code",
            name="onboarding_simplification.py",
            storage_uri="s3://forge-artifacts/onboarding_simplification.py",
            mime_type="text/x-python",
            meta={"lines": 150, "language": "python"},
        )
        session.add(artifact)

        await session.commit()
        print("✅ Development seed data created successfully!")


if __name__ == "__main__":
    asyncio.run(seed_dev_data())
