"""Build domain-scoped specialist context from existing Company Brain retrieval."""

from __future__ import annotations

from app.schemas.brain import CompanyContext
from app.schemas.specialized_agent import SpecializedAgentContext
from app.services.retrieval.scope import RetrievalScope
from app.services.specialized_agents.domain import AgentDomain
from app.services.specialized_agents.errors import SpecializedAgentScopeError


def assert_scope_matches_membership(
    scope: RetrievalScope,
    *,
    company_id: object,
    user_id: object,
) -> None:
    """Ensure retrieval scope was derived from the authorized membership."""
    if scope.company_id != company_id:
        raise SpecializedAgentScopeError(
            "Specialized agent scope company_id does not match membership",
        )
    if scope.user_id != user_id:
        raise SpecializedAgentScopeError(
            "Specialized agent scope user_id does not match membership",
        )


def build_specialized_agent_context(
    *,
    scope: RetrievalScope,
    domain: AgentDomain,
    company_context: CompanyContext,
) -> SpecializedAgentContext:
    """Map CompanyContext into a domain-scoped specialist snapshot.

    Task 9.1 passes through full context. Task 9.3+ will apply domain filters here.
    """
    return SpecializedAgentContext(
        scope=scope,
        domain=domain,
        company=company_context.company,
        objective=company_context.objective,
        constraints=list(company_context.constraints),
        facts=list(company_context.facts),
        beliefs=list(company_context.beliefs),
        decisions=list(company_context.decisions),
        evidence=list(company_context.evidence),
        learnings=list(company_context.learnings),
        sources=list(company_context.sources),
        meta=company_context.meta,
    )
