"""Retrieval service boundaries. No retrieval logic in Task 5.1."""

from app.services.retrieval.assemble import assemble_context
from app.services.retrieval.classifier import (
    QueryClassification,
    QueryIntent,
    StructuredSection,
    classify_query,
)
from app.services.retrieval.scope import RetrievalScope
from app.services.retrieval.sql import RetrievalAccessError, SqlStructuredRetriever
from app.services.retrieval.sql_vector import SqlVectorRetriever, VectorRetrievalError
from app.services.retrieval.structured import StructuredRetriever
from app.services.retrieval.vector import VectorHit, VectorRetriever

__all__ = [
    "QueryClassification",
    "QueryIntent",
    "RetrievalAccessError",
    "RetrievalScope",
    "SqlStructuredRetriever",
    "SqlVectorRetriever",
    "StructuredRetriever",
    "StructuredSection",
    "VectorHit",
    "VectorRetriever",
    "VectorRetrievalError",
    "assemble_context",
    "classify_query",
]
