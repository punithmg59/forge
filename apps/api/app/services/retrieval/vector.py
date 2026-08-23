"""Vector Brain retrieval contract. No pgvector search in Task 5.1."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.services.retrieval.scope import RetrievalScope


class VectorHit(BaseModel):
    """Normalized vector match. Ranking/reranking belong to later stages."""

    model_config = ConfigDict(extra="forbid")

    content: str
    score: float | None = None
    source_type: str | None = None
    source_reference: str | None = None
    memory_id: str | None = None
    memory_type: str | None = None
    created_at: datetime | None = None


class VectorRetriever(ABC):
    """Similarity search over company memories for an authorized company.

    Future implementations must take RetrievalScope (from CompanyMember),
    not an unauthenticated company_id.
    """

    @abstractmethod
    async def retrieve(
        self,
        scope: RetrievalScope,
        *,
        query_text: str | None = None,
        embedding: list[float] | None = None,
        limit: int = 10,
    ) -> list[VectorHit]:
        """Return vector hits. Must not run until a later Task 5 stage."""
        raise NotImplementedError
