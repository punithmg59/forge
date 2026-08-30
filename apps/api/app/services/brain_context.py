"""Orchestrate Brain context retrieval. No retrieval logic here."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_member import CompanyMember
from app.schemas.brain import CompanyContext
from app.services.retrieval import (
    RetrievalAccessError,
    RetrievalScope,
    StructuredRetriever,
    VectorRetriever,
    assemble_context,
    classify_query,
)
from app.services.retrieval.sql import SqlStructuredRetriever
from app.services.retrieval.sql_vector import SqlVectorRetriever, VectorRetrievalError

T = TypeVar("T", bound=StructuredRetriever)
V = TypeVar("V", bound=VectorRetriever)


class BrainContextError(Exception):
    def __init__(self, detail: str, status_code: int = 500) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


async def build_company_brain_context(
    db: AsyncSession,
    *,
    membership: CompanyMember,
    query: str,
    structured_retriever_factory: Callable[[AsyncSession], T] = SqlStructuredRetriever,
    vector_retriever_factory: Callable[[AsyncSession], V] = SqlVectorRetriever,
) -> CompanyContext:
    """Classify, retrieve structured/vector context, and assemble the response."""
    classification = classify_query(query)
    scope = RetrievalScope.from_membership(membership)
    structured_retriever = structured_retriever_factory(db)
    vector_retriever = vector_retriever_factory(db)

    try:
        structured = await structured_retriever.retrieve(scope, query=query)
        vector_hits = []
        if classification.vector_needed:
            vector_hits = await vector_retriever.retrieve(scope, query_text=query)
        return assemble_context(structured, vector_hits, classification)
    except RetrievalAccessError as exc:
        raise BrainContextError("Not allowed to access this company", 403) from exc
    except VectorRetrievalError as exc:
        if not classification.vector_needed:
            raise BrainContextError("Brain context retrieval failed", 502) from exc
        vector_hits: list = []
        return assemble_context(structured, vector_hits, classification)
    except SQLAlchemyError as exc:
        raise BrainContextError("Brain context retrieval failed", 500) from exc
