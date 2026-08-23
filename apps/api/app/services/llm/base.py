"""LLM provider interface. Consumers depend on this, not a vendor SDK."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.llm.types import (
    CompletionRequest,
    CompletionResult,
    EmbeddingRequest,
    EmbeddingResult,
)


class LLMProvider(ABC):
    """Minimal completion + embedding contract for Newtron and future providers."""

    name: str

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResult:
        """Return normalized text for the given chat messages."""

    @abstractmethod
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Return a normalized embedding vector for the given text."""
