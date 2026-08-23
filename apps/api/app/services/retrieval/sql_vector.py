"""pgvector similarity search over company memories."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import EMBEDDING_DIMENSION, Memory
from app.services.company_service import get_membership
from app.services.llm import EmbeddingRequest, LLMProvider, ProviderError, get_llm_provider
from app.services.retrieval.scope import RetrievalScope
from app.services.retrieval.sql import RetrievalAccessError
from app.services.retrieval.vector import VectorHit, VectorRetriever

DEFAULT_LIMIT = 10


class VectorRetrievalError(Exception):
    """Normalized vector retrieval failure. No provider or DB internals leaked."""


class SqlVectorRetriever(VectorRetriever):
    """Company-scoped cosine similarity over memories.embedding."""

    def __init__(self, db: AsyncSession, provider: LLMProvider | None = None) -> None:
        self._db = db
        self._provider = provider

    async def retrieve(
        self,
        scope: RetrievalScope,
        *,
        query_text: str | None = None,
        embedding: list[float] | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> list[VectorHit]:
        text = (query_text or "").strip()
        if not text and embedding is None:
            return []
        if limit < 1:
            return []

        membership = await get_membership(
            self._db, user_id=scope.user_id, company_id=scope.company_id
        )
        if membership is None:
            raise RetrievalAccessError("Not allowed to access this company")

        try:
            query_vector = await self._resolve_embedding(text=text, embedding=embedding)
            self._require_dimension(query_vector)
            return await self._search(membership.company_id, query_vector, limit)
        except VectorRetrievalError:
            raise
        except ProviderError as exc:
            raise VectorRetrievalError("Embedding provider failed") from exc
        except SQLAlchemyError as exc:
            raise VectorRetrievalError("Vector retrieval failed") from exc

    async def _resolve_embedding(
        self,
        *,
        text: str,
        embedding: list[float] | None,
    ) -> list[float]:
        if embedding is not None:
            return [float(value) for value in embedding]
        provider = self._provider or get_llm_provider()
        result = await provider.embed(EmbeddingRequest(input=text))
        return list(result.embedding)

    @staticmethod
    def _require_dimension(vector: list[float]) -> None:
        if len(vector) != EMBEDDING_DIMENSION:
            raise VectorRetrievalError("Embedding dimension does not match memories.embedding")

    async def _search(
        self,
        company_id: object,
        query_vector: list[float],
        limit: int,
    ) -> list[VectorHit]:
        distance = Memory.embedding.cosine_distance(query_vector)
        stmt = (
            select(Memory, distance.label("distance"))
            .where(
                Memory.company_id == company_id,
                Memory.embedding.is_not(None),
            )
            .order_by(distance, Memory.created_at.desc(), Memory.id.desc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        hits: list[VectorHit] = []
        for memory, raw_distance in result.all():
            score = None if raw_distance is None else 1.0 - float(raw_distance)
            hits.append(
                VectorHit(
                    memory_id=str(memory.id),
                    content=memory.content,
                    score=score,
                    source_type=memory.source_type,
                    source_reference=memory.source_reference,
                    memory_type=memory.memory_type,
                    created_at=memory.created_at,
                )
            )
        return hits
