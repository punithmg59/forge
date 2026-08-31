"""Execution runtime policy from settings."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.schemas.execution import ExecutionPolicy


@dataclass(frozen=True)
class ExecutionRuntimePolicy:
    max_steps_per_plan: int
    max_tool_calls_per_step: int
    max_retries_per_step: int
    max_total_duration_ms: int

    @classmethod
    def from_settings(cls) -> ExecutionRuntimePolicy:
        return cls(
            max_steps_per_plan=settings.execution_max_steps_per_plan,
            max_tool_calls_per_step=settings.execution_max_tool_calls_per_step,
            max_retries_per_step=settings.execution_max_retries_per_step,
            max_total_duration_ms=settings.execution_max_duration_ms,
        )

    def as_schema(self) -> ExecutionPolicy:
        return ExecutionPolicy(
            max_steps_per_plan=self.max_steps_per_plan,
            max_tool_calls_per_step=self.max_tool_calls_per_step,
            max_retries_per_step=self.max_retries_per_step,
            max_total_duration_ms=self.max_total_duration_ms,
        )

    @classmethod
    def default(cls) -> ExecutionRuntimePolicy:
        return cls.from_settings()
