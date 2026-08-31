"""PostgreSQL structured Company Brain retrieval."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.models.company import Company
from app.models.company_belief import CompanyBelief
from app.models.company_brain_profile import CompanyBrainProfile
from app.models.company_constraint import CompanyConstraint
from app.models.company_fact import CompanyFact
from app.models.decision import Decision
from app.models.evidence import Evidence
from app.models.experiment import Experiment
from app.models.learning import Learning
from app.models.objective import Objective
from app.schemas.brain import (
    CompanyContext,
    ContextBelief,
    ContextCompany,
    ContextConstraint,
    ContextDecision,
    ContextEvidence,
    ContextExperiment,
    ContextFact,
    ContextLearning,
    ContextObjective,
    ContextSource,
    Provenance,
    RetrievalMeta,
)
from app.services.company_service import get_membership
from app.services.objective_service import STATUS_ACTIVE, select_current_objective
from app.services.retrieval.scope import RetrievalScope
from app.services.retrieval.structured import StructuredRetriever

RECENT_LIMIT = 25

T = TypeVar("T")


class RetrievalAccessError(Exception):
    """Raised when RetrievalScope does not match an existing membership."""


class SqlStructuredRetriever(StructuredRetriever):
    """Deterministic SQL retrieval. No vector search or ranking."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def retrieve(
        self,
        scope: RetrievalScope,
        *,
        query: str | None = None,
    ) -> CompanyContext:
        membership = await get_membership(
            self._db, user_id=scope.user_id, company_id=scope.company_id
        )
        if membership is None:
            raise RetrievalAccessError("Not allowed to access this company")

        company_id = membership.company_id
        company = await self._db.get(Company, company_id)
        profile = await self._one(
            select(CompanyBrainProfile).where(CompanyBrainProfile.company_id == company_id)
        )
        active_objectives = await self._list(
            Objective,
            Objective.company_id,
            company_id,
            status=STATUS_ACTIVE,
            created_at=Objective.created_at,
            id_col=Objective.id,
        )
        objective = select_current_objective(active_objectives)
        constraints = await self._list(
            CompanyConstraint,
            CompanyConstraint.company_id,
            company_id,
            status=STATUS_ACTIVE,
            created_at=CompanyConstraint.created_at,
            id_col=CompanyConstraint.id,
        )
        facts = await self._list(
            CompanyFact,
            CompanyFact.company_id,
            company_id,
            created_at=CompanyFact.created_at,
            id_col=CompanyFact.id,
        )
        beliefs = await self._list(
            CompanyBelief,
            CompanyBelief.company_id,
            company_id,
            created_at=CompanyBelief.created_at,
            id_col=CompanyBelief.id,
        )
        decisions = await self._list(
            Decision,
            Decision.company_id,
            company_id,
            created_at=Decision.created_at,
            id_col=Decision.id,
            limit=RECENT_LIMIT,
        )
        experiments = await self._list(
            Experiment,
            Experiment.company_id,
            company_id,
            created_at=Experiment.created_at,
            id_col=Experiment.id,
            limit=RECENT_LIMIT,
        )
        learnings = await self._list(
            Learning,
            Learning.company_id,
            company_id,
            status=STATUS_ACTIVE,
            created_at=Learning.created_at,
            id_col=Learning.id,
            limit=RECENT_LIMIT,
        )
        evidence_rows = await self._list(
            Evidence,
            Evidence.company_id,
            company_id,
            created_at=Evidence.created_at,
            id_col=Evidence.id,
            limit=RECENT_LIMIT,
        )

        return CompanyContext(
            company=self._map_company(company),
            objective=self._map_objective(objective),
            bottleneck=profile.current_bottlenecks if profile is not None else None,
            constraints=[self._map_constraint(row) for row in constraints],
            facts=[self._map_fact(row) for row in facts],
            beliefs=[self._map_belief(row) for row in beliefs],
            evidence=[self._map_evidence(row) for row in evidence_rows],
            decisions=[self._map_decision(row) for row in decisions],
            experiments=[self._map_experiment(row) for row in experiments],
            learnings=[self._map_learning(row) for row in learnings],
            memories=[],
            sources=[self._map_source(row) for row in evidence_rows],
            meta=RetrievalMeta(
                query=query,
                structured_used=True,
                vector_used=False,
                retrieved_at=datetime.now(UTC),
            ),
        )

    async def _one(self, stmt: Select[tuple[T]]) -> T | None:
        result = await self._db.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    async def _list(
        self,
        model: type[T],
        company_col: InstrumentedAttribute[object],
        company_id: object,
        *,
        created_at: InstrumentedAttribute[object],
        id_col: InstrumentedAttribute[object],
        status: str | None = None,
        limit: int | None = None,
    ) -> list[T]:
        stmt = select(model).where(company_col == company_id)
        if status is not None:
            stmt = stmt.where(model.status == status)  # type: ignore[attr-defined]
        stmt = stmt.order_by(created_at.desc(), id_col.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _map_company(company: Company | None) -> ContextCompany | None:
        if company is None:
            return None
        return ContextCompany(
            id=company.id,
            name=company.name,
            slug=company.slug,
            stage=company.stage,
            mission=company.mission,
            product_description=company.product_description,
        )

    @staticmethod
    def _map_objective(objective: Objective | None) -> ContextObjective | None:
        if objective is None:
            return None
        return ContextObjective(
            id=objective.id,
            title=objective.title,
            description=objective.description,
            status=objective.status,
            priority=objective.priority,
        )

    @staticmethod
    def _map_constraint(row: CompanyConstraint) -> ContextConstraint:
        return ContextConstraint(
            id=row.id,
            type=row.type,
            name=row.name,
            description=row.description,
            value=row.value,
            severity=row.severity,
            status=row.status,
        )

    @staticmethod
    def _map_fact(row: CompanyFact) -> ContextFact:
        return ContextFact(
            id=row.id,
            key=row.key,
            value=row.value,
            value_type=row.value_type,
            confidence=row.confidence,
            status=row.status,
            provenance=Provenance(
                source_type=row.source_type,
                source_reference=row.source_reference,
                observed_at=row.observed_at,
            ),
        )

    @staticmethod
    def _map_belief(row: CompanyBelief) -> ContextBelief:
        return ContextBelief(
            id=row.id,
            statement=row.statement,
            reasoning=row.reasoning,
            confidence=row.confidence,
            status=row.status,
            provenance=Provenance(source_type=row.source, source_reference=None),
        )

    @staticmethod
    def _map_decision(row: Decision) -> ContextDecision:
        return ContextDecision(
            id=row.id,
            title=row.title,
            decision=row.decision,
            rationale=row.rationale,
            status=row.status,
        )

    @staticmethod
    def _map_experiment(row: Experiment) -> ContextExperiment:
        return ContextExperiment(
            id=row.id,
            name=row.name,
            description=row.description,
            status=row.status,
        )

    @staticmethod
    def _map_learning(row: Learning) -> ContextLearning:
        return ContextLearning(
            id=row.id,
            statement=row.statement,
            evidence_summary=row.evidence_summary,
            confidence=row.confidence,
            status=row.status,
        )

    @staticmethod
    def _map_evidence(row: Evidence) -> ContextEvidence:
        return ContextEvidence(
            id=row.id,
            type=row.type,
            title=row.title,
            content=row.content,
            confidence=row.confidence,
            created_at=row.created_at,
            provenance=Provenance(
                source_type=row.source_type,
                source_reference=row.source_reference,
                observed_at=row.observed_at,
            ),
        )

    @staticmethod
    def _map_source(row: Evidence) -> ContextSource:
        return ContextSource(
            entity_type="evidence",
            entity_id=str(row.id),
            source_type=row.source_type,
            source_reference=row.source_reference,
            title=row.title,
        )
