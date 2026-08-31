"""Build domain-scoped specialist context from existing Company Brain retrieval."""

from __future__ import annotations

from app.schemas.brain import CompanyContext
from app.schemas.specialized_agent import SpecializedAgentContext
from app.schemas.specialized_agent_types import AgentDomain
from app.services.retrieval.scope import RetrievalScope
from app.services.specialized_agents.domain_filter import filter_company_context_for_domain
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

    Task 9.1 passes through full context. Task 9.3+ applies domain filters here.
    """
    scoped = filter_company_context_for_domain(company_context, domain)
    return SpecializedAgentContext(
        scope=scope,
        domain=domain,
        company=scoped.company,
        objective=scoped.objective,
        constraints=list(scoped.constraints),
        facts=list(scoped.facts),
        beliefs=list(scoped.beliefs),
        decisions=list(scoped.decisions),
        evidence=list(scoped.evidence),
        learnings=list(scoped.learnings),
        sources=list(scoped.sources),
        meta=scoped.meta,
    )
