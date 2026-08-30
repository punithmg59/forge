"""Domain-specific errors for specialized agent foundation."""

from __future__ import annotations


class SpecializedAgentError(Exception):
    """Base error for specialized agent operations."""

    def __init__(self, detail: str, status_code: int = 500) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class UnknownSpecializedAgent(SpecializedAgentError):  # noqa: N818
    """Requested agent type is not registered."""

    def __init__(self, agent_type: str) -> None:
        super().__init__(f"Unknown specialized agent: {agent_type}", status_code=404)


class UnsupportedDomain(SpecializedAgentError):  # noqa: N818
    """Domain is not supported by the requested agent."""

    def __init__(self, domain: str, agent_type: str) -> None:
        super().__init__(
            f"Domain '{domain}' is not supported by agent '{agent_type}'",
            status_code=400,
        )


class SpecializedAgentContextError(SpecializedAgentError):
    """Brain context could not be built for a specialist."""

    def __init__(self, detail: str, status_code: int = 500) -> None:
        super().__init__(detail, status_code=status_code)


class SpecializedAgentReasoningNotImplemented(SpecializedAgentError):  # noqa: N818
    """Specialist reasoning is not implemented yet (Task 9.1 foundation stub)."""

    def __init__(self, agent_type: str) -> None:
        super().__init__(
            f"Specialized agent '{agent_type}' reasoning is not implemented yet",
            status_code=501,
        )


class SpecializedAgentScopeError(SpecializedAgentError):
    """Company scope validation failed."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=403)
