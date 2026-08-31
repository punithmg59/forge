"""Tool abstraction. Agents call ToolExecutor — not tool.execute() directly."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tool import (
    ToolCategory,
    ToolEffect,
    ToolExecutionContext,
    ToolPermission,
)

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class Tool(ABC, Generic[InputT, OutputT]):
    """Read-only tool contract with validated input and output models."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable tool name without version suffix."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Tool version identifier (e.g. v1)."""

    @property
    def qualified_name(self) -> str:
        return f"{self.name}:{self.version}"

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable tool description."""

    @property
    @abstractmethod
    def category(self) -> ToolCategory:
        """Tool category for policy and observability."""

    @property
    @abstractmethod
    def effect(self) -> ToolEffect:
        """Read or write classification."""

    @property
    @abstractmethod
    def required_permissions(self) -> frozenset[ToolPermission]:
        """Permissions required before execution."""

    @property
    def enabled(self) -> bool:
        return True

    @property
    @abstractmethod
    def input_model(self) -> type[InputT]:
        """Pydantic model for validated tool input."""

    @property
    @abstractmethod
    def output_model(self) -> type[OutputT]:
        """Pydantic model for validated tool output."""

    @property
    def timeout_ms(self) -> int | None:
        """Per-tool timeout override. None uses policy default."""
        return None

    @abstractmethod
    async def execute(
        self,
        db: AsyncSession,
        context: ToolExecutionContext,
        validated_input: InputT,
    ) -> OutputT:
        """Execute tool logic. Tenant scope comes from context, never from input."""
