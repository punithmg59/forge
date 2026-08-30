"""Registry for specialized reasoning agents."""

from __future__ import annotations

from app.services.specialized_agents.base import SpecializedAgent
from app.services.specialized_agents.customer_growth_agent import CustomerGrowthAgent
from app.services.specialized_agents.domain import SpecializedAgentType, parse_agent_type
from app.services.specialized_agents.errors import UnknownSpecializedAgent
from app.services.specialized_agents.product_agent import ProductAgent

_REGISTRY: dict[SpecializedAgentType, SpecializedAgent] = {}


def _ensure_builtins_registered() -> None:
    if _REGISTRY:
        return
    register(CustomerGrowthAgent())
    register(ProductAgent())


def register(agent: SpecializedAgent) -> None:
    """Register a specialized agent instance."""
    _REGISTRY[agent.agent_type] = agent


def get_specialized_agent(agent_type: str | SpecializedAgentType) -> SpecializedAgent:
    """Return a registered specialist. Unknown types fail explicitly."""
    _ensure_builtins_registered()
    if isinstance(agent_type, SpecializedAgentType):
        resolved = agent_type
    else:
        try:
            resolved = parse_agent_type(agent_type)
        except ValueError:
            raise UnknownSpecializedAgent(agent_type) from None
    agent = _REGISTRY.get(resolved)
    if agent is None:
        raise UnknownSpecializedAgent(str(agent_type))
    return agent


def registered_agent_types() -> frozenset[SpecializedAgentType]:
    """Return all registered agent type identifiers."""
    _ensure_builtins_registered()
    return frozenset(_REGISTRY.keys())
