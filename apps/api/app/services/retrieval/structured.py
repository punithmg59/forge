"""Structured Brain retrieval contract. No SQL implementation in Task 5.1."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.brain import CompanyContext
from app.services.retrieval.scope import RetrievalScope


class StructuredRetriever(ABC):
    """Read structured Brain records for an authorized company.

    Future implementations must take RetrievalScope (from CompanyMember),
    not an unauthenticated company_id.
    """

    @abstractmethod
    async def retrieve(
        self,
        scope: RetrievalScope,
        *,
        query: str | None = None,
    ) -> CompanyContext:
        """Return structured context. Must not run until a later Task 5 stage."""
        raise NotImplementedError
