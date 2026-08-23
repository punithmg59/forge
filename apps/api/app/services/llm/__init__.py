"""LLM provider abstraction."""

from app.services.llm.base import LLMProvider
from app.services.llm.errors import (
    ProviderAuthError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnexpectedError,
)
from app.services.llm.factory import get_llm_provider
from app.services.llm.newtron import NewtronProvider
from app.services.llm.types import (
    ChatMessage,
    CompletionRequest,
    CompletionResult,
    EmbeddingRequest,
    EmbeddingResult,
)

__all__ = [
    "ChatMessage",
    "CompletionRequest",
    "CompletionResult",
    "EmbeddingRequest",
    "EmbeddingResult",
    "LLMProvider",
    "NewtronProvider",
    "ProviderAuthError",
    "ProviderError",
    "ProviderInvalidResponseError",
    "ProviderRateLimitError",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "ProviderUnexpectedError",
    "get_llm_provider",
]
