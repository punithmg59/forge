"""Canonical domain and agent-type identifiers for specialized reasoning agents."""

from __future__ import annotations

from enum import Enum


class AgentDomain(str, Enum):
    """Business domain a specialized agent reasons about."""

    CUSTOMER_GROWTH = "customer_growth"
    PRODUCT = "product"


class SpecializedAgentType(str, Enum):
    """Typed specialist agent identifiers."""

    CUSTOMER_GROWTH = "customer_growth"
    PRODUCT = "product"


AGENT_TYPE_TO_DOMAIN: dict[SpecializedAgentType, AgentDomain] = {
    SpecializedAgentType.CUSTOMER_GROWTH: AgentDomain.CUSTOMER_GROWTH,
    SpecializedAgentType.PRODUCT: AgentDomain.PRODUCT,
}

DOMAIN_TO_AGENT_TYPE: dict[AgentDomain, SpecializedAgentType] = {
    AgentDomain.CUSTOMER_GROWTH: SpecializedAgentType.CUSTOMER_GROWTH,
    AgentDomain.PRODUCT: SpecializedAgentType.PRODUCT,
}

CUSTOMER_GROWTH_INTENTS: frozenset[str] = frozenset(
    {
        "acquisition",
        "retention",
        "icp",
        "customer_discovery",
        "growth",
    }
)

PRODUCT_INTENTS: frozenset[str] = frozenset(
    {
        "roadmap",
        "features",
        "prioritization",
        "product_discovery",
        "ux",
    }
)

INTENTS_BY_DOMAIN: dict[AgentDomain, frozenset[str]] = {
    AgentDomain.CUSTOMER_GROWTH: CUSTOMER_GROWTH_INTENTS,
    AgentDomain.PRODUCT: PRODUCT_INTENTS,
}


def parse_agent_type(value: str) -> SpecializedAgentType:
    """Resolve a string to a known agent type or raise ValueError."""
    normalized = value.strip().lower()
    try:
        return SpecializedAgentType(normalized)
    except ValueError:
        raise ValueError(f"Unknown specialized agent type: {value}") from None


def parse_domain(value: str) -> AgentDomain:
    """Resolve a string to a known domain or raise ValueError."""
    normalized = value.strip().lower()
    try:
        return AgentDomain(normalized)
    except ValueError:
        raise ValueError(f"Unknown agent domain: {value}") from None


def domain_for_agent_type(agent_type: SpecializedAgentType) -> AgentDomain:
    return AGENT_TYPE_TO_DOMAIN[agent_type]
