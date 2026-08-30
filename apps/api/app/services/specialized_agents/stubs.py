"""Foundation stub for Product Agent (Task 9.4)."""

from __future__ import annotations

from app.services.specialized_agents.base import SpecializedAgent
from app.services.specialized_agents.domain import SpecializedAgentType


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
