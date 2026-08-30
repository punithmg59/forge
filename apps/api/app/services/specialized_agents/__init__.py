"""Specialized reasoning agent foundation (Task 9.1)."""

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
from app.services.specialized_agents.audit import (
    SPECIALIZED_AGENT_TASK_TYPE,
    new_specialized_agent_run,
    new_specialized_agent_task,
)
from app.services.specialized_agents.base import SpecializedAgent
from app.services.specialized_agents.context import (
    assert_scope_matches_membership,
    build_specialized_agent_context,
)
from app.services.specialized_agents.errors import (
    SpecializedAgentContextError,
    SpecializedAgentError,
    SpecializedAgentReasoningNotImplemented,
    SpecializedAgentScopeError,
    UnknownSpecializedAgent,
    UnsupportedDomain,
)
from app.services.specialized_agents.grounding import (
    ground_specialized_recommendation,
    parse_specialized_recommendation_payload,
)
from app.services.specialized_agents.registry import (
    get_specialized_agent,
    register,
    registered_agent_types,
)
from app.services.specialized_agents.stubs import CustomerGrowthAgent, ProductAgent

__all__ = [
    "AGENT_TYPE_TO_DOMAIN",
    "AgentDomain",
    "CUSTOMER_GROWTH_INTENTS",
    "CustomerGrowthAgent",
    "DOMAIN_TO_AGENT_TYPE",
    "INTENTS_BY_DOMAIN",
    "PRODUCT_INTENTS",
    "ProductAgent",
    "SPECIALIZED_AGENT_TASK_TYPE",
    "SpecializedAgent",
    "SpecializedAgentContextError",
    "SpecializedAgentError",
    "SpecializedAgentReasoningNotImplemented",
    "SpecializedAgentScopeError",
    "SpecializedAgentType",
    "UnknownSpecializedAgent",
    "UnsupportedDomain",
    "assert_scope_matches_membership",
    "build_specialized_agent_context",
    "domain_for_agent_type",
    "get_specialized_agent",
    "ground_specialized_recommendation",
    "new_specialized_agent_run",
    "new_specialized_agent_task",
    "parse_agent_type",
    "parse_domain",
    "parse_specialized_recommendation_payload",
    "register",
    "registered_agent_types",
]
