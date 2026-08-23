"""Retrieval service boundaries. No retrieval logic in Task 5.1."""

from app.services.retrieval.scope import RetrievalScope
from app.services.retrieval.structured import StructuredRetriever
from app.services.retrieval.vector import VectorHit, VectorRetriever

__all__ = [
    "RetrievalScope",
    "StructuredRetriever",
    "VectorHit",
    "VectorRetriever",
]
