"""Domain-scoped retrieval extension point for Task 9.3+."""

from __future__ import annotations

from app.schemas.specialized_agent_types import AgentDomain

# Sections future domain filters will scope. Not applied in Task 9.2.
DOMAIN_RETRIEVAL_SECTIONS: dict[AgentDomain, tuple[str, ...]] = {
    AgentDomain.CUSTOMER_GROWTH: (
        "evidence",
        "learnings",
        "decisions",
        "constraints",
        "facts",
        "beliefs",
    ),
    AgentDomain.PRODUCT: (
        "evidence",
        "learnings",
        "decisions",
        "constraints",
        "facts",
        "beliefs",
    ),
}
