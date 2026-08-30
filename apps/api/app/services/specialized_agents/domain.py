"""Re-export canonical domain identifiers from schemas layer."""

from app.schemas.specialized_agent_types import (
    AGENT_TYPE_TO_DOMAIN,
    CUSTOMER_GROWTH_INTENTS,
    DOMAIN_TO_AGENT_TYPE,
    INTENTS_BY_DOMAIN,
    PRODUCT_INTENTS,
    AgentDomain,
    SpecializedAgentType,
    domain_for_agent_type,
    parse_agent_type,
    parse_domain,
)

__all__ = [
    "AGENT_TYPE_TO_DOMAIN",
    "CUSTOMER_GROWTH_INTENTS",
    "DOMAIN_TO_AGENT_TYPE",
    "INTENTS_BY_DOMAIN",
    "PRODUCT_INTENTS",
    "AgentDomain",
    "SpecializedAgentType",
    "domain_for_agent_type",
    "parse_agent_type",
    "parse_domain",
]
