"""Deterministic routing term patterns."""

from __future__ import annotations

from app.schemas.specialized_agent_types import SpecializedAgentType
from app.schemas.specialized_routing_types import RoutingIntent

_CUSTOMER_GROWTH_INTENT_TERMS: dict[RoutingIntent, tuple[str, ...]] = {
    RoutingIntent.CUSTOMER_ACQUISITION: (
        "customer acquisition",
        "acquire customers",
        "get customers",
        "getting customers",
        "gain customers",
        "more customers",
        "find customers",
        "sales pipeline",
        "close deals",
        "sales",
    ),
    RoutingIntent.CUSTOMER_RETENTION: (
        "customer retention",
        "retain customers",
        "retention",
        "churn",
        "reduce churn",
    ),
    RoutingIntent.CUSTOMER_DISCOVERY: (
        "customer discovery",
        "ideal customer",
        "target customer",
        "icp",
        "who is our customer",
    ),
    RoutingIntent.CUSTOMER_INTERVIEWS: (
        "customer interview",
        "customer interviews",
        "interview customers",
        "talk to customers",
        "user interviews",
    ),
    RoutingIntent.PRICING_DEMAND: (
        "willingness to pay",
        "pricing strategy",
        "customer demand",
        "price sensitivity",
        "pricing",
    ),
    RoutingIntent.GROWTH: (
        "growth strategy",
        "go to market",
        "gtm",
    ),
    RoutingIntent.MARKETING: (
        "marketing strategy",
        "marketing channel",
        "marketing",
        "customer outreach",
    ),
}

_PRODUCT_INTENT_TERMS: dict[RoutingIntent, tuple[str, ...]] = {
    RoutingIntent.PRODUCT_ROADMAP: (
        "product roadmap",
        "roadmap",
    ),
    RoutingIntent.PRODUCT_FEATURES: (
        "product feature",
        "product features",
        "new feature",
        "feature request",
        "build feature",
    ),
    RoutingIntent.PRODUCT_PRIORITIZATION: (
        "product priorit",
        "prioritize features",
        "feature priorit",
        "prioritization",
        "what to build next",
    ),
    RoutingIntent.PRODUCT_QUALITY: (
        "product quality",
        "bug fixes",
        "reliability",
        "quality issues",
        "technical debt",
    ),
    RoutingIntent.PRODUCT_STRATEGY: (
        "product strategy",
        "product direction",
        "product vision",
    ),
    RoutingIntent.UX: (
        "user experience",
        "usability",
        "user interface",
        "ux",
        "ui design",
    ),
}

INTENT_TERMS: dict[RoutingIntent, tuple[str, ...]] = {
    **_CUSTOMER_GROWTH_INTENT_TERMS,
    **_PRODUCT_INTENT_TERMS,
}

AMBIGUOUS_OPERATING_PATTERNS: tuple[str, ...] = (
    "what should we do next",
    "what should i do next",
    "what should we do",
    "what should i focus on",
    "what should we focus on",
    "what do we do next",
    "what do i do next",
    "help me decide what to do",
    "what is the highest-leverage",
)

INJECTION_PATTERNS: tuple[str, ...] = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard previous",
    "forget previous instructions",
    "you must route",
    "route to product",
    "route to customer",
)


def intent_for_agent_type(agent_type: SpecializedAgentType) -> RoutingIntent:
    defaults = {
        SpecializedAgentType.CUSTOMER_GROWTH: RoutingIntent.CUSTOMER_ACQUISITION,
        SpecializedAgentType.PRODUCT: RoutingIntent.PRODUCT_ROADMAP,
    }
    return defaults[agent_type]
