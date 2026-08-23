"""Normalized LLM provider errors. Do not expose raw provider exceptions to APIs."""

from __future__ import annotations


class ProviderError(Exception):
    """Base error for LLM provider failures."""


class ProviderAuthError(ProviderError):
    """API key missing, rejected, or otherwise unauthorized."""


class ProviderUnavailableError(ProviderError):
    """Provider could not be reached or returned a server failure."""


class ProviderTimeoutError(ProviderError):
    """Provider request exceeded the configured timeout."""


class ProviderRateLimitError(ProviderError):
    """Provider rejected the request due to rate limiting."""


class ProviderInvalidResponseError(ProviderError):
    """Provider returned a body that could not be normalized."""


class ProviderUnexpectedError(ProviderError):
    """Catch-all for other provider failures."""
