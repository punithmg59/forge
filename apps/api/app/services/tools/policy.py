"""Centralized tool execution policy."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class ToolExecutionPolicy:
    max_calls_per_request: int
    max_total_execution_ms: int
    default_timeout_ms: int
    external_timeout_ms: int
    max_input_bytes: int
    max_output_bytes: int
    max_records: int

    @classmethod
    def from_settings(cls) -> ToolExecutionPolicy:
        return cls(
            max_calls_per_request=settings.tool_max_calls_per_request,
            max_total_execution_ms=settings.tool_max_total_execution_ms,
            default_timeout_ms=settings.tool_default_timeout_ms,
            external_timeout_ms=settings.tool_external_timeout_ms,
            max_input_bytes=settings.tool_max_input_bytes,
            max_output_bytes=settings.tool_max_output_bytes,
            max_records=settings.tool_max_records,
        )

    @classmethod
    def default(cls) -> ToolExecutionPolicy:
        return cls.from_settings()
