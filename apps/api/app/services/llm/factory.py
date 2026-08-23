"""Construct an LLMProvider from application settings."""

from __future__ import annotations

from app.core.config import Settings, settings
from app.services.llm.base import LLMProvider
from app.services.llm.errors import ProviderUnexpectedError
from app.services.llm.newtron import NewtronProvider

SUPPORTED_PROVIDERS = frozenset({"newtron"})


def get_llm_provider(config: Settings | None = None) -> LLMProvider:
    """Return the configured provider. Consumers should not branch on vendor names."""
    cfg = config or settings
    name = cfg.llm_provider.strip().lower()
    if name == "newtron":
        return NewtronProvider.from_settings(cfg)
    if name in {"openai", "claude", "anthropic"}:
        raise ProviderUnexpectedError(f"LLM provider {name!r} is not implemented yet")
    raise ProviderUnexpectedError(f"Unsupported LLM provider: {name}")
