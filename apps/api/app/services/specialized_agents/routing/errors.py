"""Routing-specific errors."""

from __future__ import annotations

from app.services.specialized_agents.errors import SpecializedAgentError


class RoutingError(SpecializedAgentError):
    """Base error for specialized agent routing."""


class RoutingClassificationError(RoutingError):
    """LLM or deterministic classification failed."""

    def __init__(self, detail: str, status_code: int = 502) -> None:
        super().__init__(detail, status_code=status_code)


class UnsupportedSpecializedRoute(RoutingError):  # noqa: N818
    """Route targets an unknown or unsupported specialist."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=400)


class InvalidClassification(RoutingError):  # noqa: N818
    """Structured classifier output failed validation."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=502)
