"""Foundation stub implementations for Task 9.1. No LLM calls."""

from __future__ import annotations

from app.services.specialized_agents.base import SpecializedAgent
from app.services.specialized_agents.domain import SpecializedAgentType


class CustomerGrowthAgent(SpecializedAgent):
    @property
    def agent_type(self) -> SpecializedAgentType:
        return SpecializedAgentType.CUSTOMER_GROWTH

    @property
    def display_name(self) -> str:
        return "Customer & Growth Agent"

    @property
    def description(self) -> str:
        return (
            "Reasons about customer discovery, acquisition, retention, and growth "
            "using domain-scoped Company Brain context."
        )


class ProductAgent(SpecializedAgent):
    @property
    def agent_type(self) -> SpecializedAgentType:
        return SpecializedAgentType.PRODUCT

    @property
    def display_name(self) -> str:
        return "Product Agent"

    @property
    def description(self) -> str:
        return (
            "Reasons about product direction, prioritization, and discovery "
            "using domain-scoped Company Brain context."
        )
