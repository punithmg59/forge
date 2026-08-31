"""Specialized agent routing layer."""

from app.schemas.specialized_routing_types import RoutingIntent
from app.services.specialized_agents.routing.deterministic import (
    classify_deterministic,
    head_agent_fallback_decision,
)
from app.services.specialized_agents.routing.domain_retrieval import DOMAIN_RETRIEVAL_SECTIONS
from app.services.specialized_agents.routing.errors import (
    InvalidClassification,
    RoutingClassificationError,
    RoutingError,
    UnsupportedSpecializedRoute,
)
from app.services.specialized_agents.routing.llm_classifier import classify_with_llm
from app.services.specialized_agents.routing.router import (
    recommend_routed_specialist,
    route_specialized_agent,
)

__all__ = [
    "DOMAIN_RETRIEVAL_SECTIONS",
    "InvalidClassification",
    "RoutingClassificationError",
    "RoutingError",
    "RoutingIntent",
    "UnsupportedSpecializedRoute",
    "classify_deterministic",
    "classify_with_llm",
    "head_agent_fallback_decision",
    "recommend_routed_specialist",
    "route_specialized_agent",
]
