"""Routing intent identifiers and domain mappings."""

from __future__ import annotations

from enum import Enum

from app.schemas.specialized_agent_types import (
    DOMAIN_TO_AGENT_TYPE,
    AgentDomain,
    SpecializedAgentType,
)


class RoutingIntent(str, Enum):
    """Canonical routing intents."""

    CUSTOMER_ACQUISITION = "customer_acquisition"
    CUSTOMER_RETENTION = "customer_retention"
    CUSTOMER_DISCOVERY = "customer_discovery"
    CUSTOMER_INTERVIEWS = "customer_interviews"
    PRICING_DEMAND = "pricing_demand"
    GROWTH = "growth"
    MARKETING = "marketing"
    PRODUCT_ROADMAP = "product_roadmap"
    PRODUCT_FEATURES = "product_features"
    PRODUCT_PRIORITIZATION = "product_prioritization"
    PRODUCT_QUALITY = "product_quality"
    PRODUCT_STRATEGY = "product_strategy"
    UX = "ux"
    GENERAL = "general"


INTENT_TO_DOMAIN: dict[RoutingIntent, AgentDomain | None] = {
    RoutingIntent.CUSTOMER_ACQUISITION: AgentDomain.CUSTOMER_GROWTH,
    RoutingIntent.CUSTOMER_RETENTION: AgentDomain.CUSTOMER_GROWTH,
    RoutingIntent.CUSTOMER_DISCOVERY: AgentDomain.CUSTOMER_GROWTH,
    RoutingIntent.CUSTOMER_INTERVIEWS: AgentDomain.CUSTOMER_GROWTH,
    RoutingIntent.PRICING_DEMAND: AgentDomain.CUSTOMER_GROWTH,
    RoutingIntent.GROWTH: AgentDomain.CUSTOMER_GROWTH,
    RoutingIntent.MARKETING: AgentDomain.CUSTOMER_GROWTH,
    RoutingIntent.PRODUCT_ROADMAP: AgentDomain.PRODUCT,
    RoutingIntent.PRODUCT_FEATURES: AgentDomain.PRODUCT,
    RoutingIntent.PRODUCT_PRIORITIZATION: AgentDomain.PRODUCT,
    RoutingIntent.PRODUCT_QUALITY: AgentDomain.PRODUCT,
    RoutingIntent.PRODUCT_STRATEGY: AgentDomain.PRODUCT,
    RoutingIntent.UX: AgentDomain.PRODUCT,
    RoutingIntent.GENERAL: None,
}

INTENT_TO_AGENT_TYPE: dict[RoutingIntent, SpecializedAgentType | None] = {
    intent: DOMAIN_TO_AGENT_TYPE[domain] if domain is not None else None
    for intent, domain in INTENT_TO_DOMAIN.items()
}
