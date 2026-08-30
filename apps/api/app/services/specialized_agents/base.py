"""Specialized agent base contract. Foundation stubs do not call LLM or mutate state."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_member import CompanyMember
from app.schemas.brain import CompanyContext
from app.schemas.specialized_agent import (
    SpecializedAgentContext,
    SpecializedAgentRecommendResponse,
)
from app.services.brain_context import BrainContextError, build_company_brain_context
from app.services.llm.types import CompletionRequest
from app.services.retrieval.scope import RetrievalScope
from app.services.specialized_agents.context import (
    assert_scope_matches_membership,
    build_specialized_agent_context,
)
from app.services.specialized_agents.domain import (
    INTENTS_BY_DOMAIN,
    AgentDomain,
    SpecializedAgentType,
    domain_for_agent_type,
)
from app.services.specialized_agents.errors import (
    SpecializedAgentContextError,
    SpecializedAgentReasoningNotImplemented,
)

TContextBuilder = Callable[..., Awaitable[CompanyContext]]


class SpecializedAgent(ABC):
    """Contract for domain-scoped reasoning agents."""

    @property
    @abstractmethod
    def agent_type(self) -> SpecializedAgentType:
        """Canonical agent identifier."""

    @property
    def domain(self) -> AgentDomain:
        return domain_for_agent_type(self.agent_type)

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable specialist name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Short specialist purpose statement."""

    @property
    def supported_intents(self) -> frozenset[str]:
        return INTENTS_BY_DOMAIN[self.domain]

    async def retrieve_context(
        self,
        db: AsyncSession,
        *,
        membership: CompanyMember,
        query: str,
        context_builder: TContextBuilder = build_company_brain_context,
    ) -> SpecializedAgentContext:
        """Retrieve domain-scoped Company Brain context via existing retrieval pipeline."""
        scope = RetrievalScope.from_membership(membership)
        assert_scope_matches_membership(
            scope,
            company_id=membership.company_id,
            user_id=membership.user_id,
        )
        try:
            company_context = await context_builder(
                db,
                membership=membership,
                query=query,
            )
        except BrainContextError as exc:
            raise SpecializedAgentContextError(exc.detail, exc.status_code) from exc

        return build_specialized_agent_context(
            scope=scope,
            domain=self.domain,
            company_context=company_context,
        )

    def build_prompt(
        self,
        *,
        question: str,
        context: SpecializedAgentContext,
    ) -> CompletionRequest:
        """Build provider completion request. Not implemented in Task 9.1 stubs."""
        raise SpecializedAgentReasoningNotImplemented(self.agent_type.value)

    async def recommend(
        self,
        db: AsyncSession,
        *,
        membership: CompanyMember,
        question: str | None = None,
        context_builder: TContextBuilder = build_company_brain_context,
        provider_factory: Callable[[], object] | None = None,
    ) -> SpecializedAgentRecommendResponse:
        """Produce a grounded specialist proposal. Not implemented in Task 9.1 stubs."""
        raise SpecializedAgentReasoningNotImplemented(self.agent_type.value)
