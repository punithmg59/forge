"""Centralized safe tool execution boundary."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tool import (
    ToolCall,
    ToolCategory,
    ToolErrorCode,
    ToolExecutionContext,
    ToolResult,
    ToolResultProvenance,
)
from app.services.tools.audit import persist_tool_execution_audit
from app.services.tools.authorization import authorize_tool_execution
from app.services.tools.base import Tool
from app.services.tools.errors import (
    ToolDisabledError,
    ToolError,
    ToolInvalidInputError,
    ToolInvalidOutputError,
    ToolPolicyLimitError,
    ToolResultTooLargeError,
)
from app.services.tools.policy import ToolExecutionPolicy
from app.services.tools.registry import get_tool, is_tool_enabled

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Single security boundary for tool execution."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        policy: ToolExecutionPolicy | None = None,
        audit: bool = True,
    ) -> None:
        self._db = db
        self._policy = policy or ToolExecutionPolicy.default()
        self._audit = audit
        self._calls_this_request = 0
        self._total_ms_this_request = 0.0

    async def execute(
        self,
        call: ToolCall,
        context: ToolExecutionContext,
        *,
        agent_run_id: uuid.UUID | None = None,
    ) -> ToolResult:
        trace_id = call.trace_id or context.trace_id
        started = time.perf_counter()
        tool_name = call.tool_name
        tool_version = call.tool_version
        qualified_name = call.qualified_name

        logger.info(
            "tool_execution_started tool_name=%s version=%s company_id=%s "
            "agent_type=%s trace_id=%s",
            tool_name,
            tool_version,
            context.company_id,
            context.agent_type,
            trace_id,
        )

        try:
            self._enforce_request_policy()
            tool = get_tool(qualified_name)
            if not is_tool_enabled(qualified_name):
                raise ToolDisabledError(qualified_name)
            authorize_tool_execution(context, tool.required_permissions)
            validated_input = self._validate_input(tool, call.input)
            timeout_ms = tool.timeout_ms or self._timeout_for_category(tool.category)
            raw_output = await asyncio.wait_for(
                tool.execute(self._db, context, validated_input),
                timeout=timeout_ms / 1000.0,
            )
            validated_output = self._validate_output(tool, raw_output)
            output_dict = validated_output.model_dump(mode="json")
            self._enforce_output_size(output_dict)
            duration_ms = (time.perf_counter() - started) * 1000
            self._record_request_usage(duration_ms)
            result = ToolResult(
                success=True,
                tool_name=tool_name,
                tool_version=tool_version,
                data=output_dict,
                trace_id=trace_id,
                executed_at=datetime.now(UTC),
                provenance=ToolResultProvenance(
                    source="tool_layer",
                    company_id=context.company_id,
                ),
                duration_ms=duration_ms,
            )
            if self._audit:
                await persist_tool_execution_audit(
                    self._db,
                    context=context,
                    tool_name=tool_name,
                    tool_version=tool_version,
                    success=True,
                    duration_ms=duration_ms,
                    agent_run_id=agent_run_id,
                )
            logger.info(
                "tool_execution_completed tool_name=%s version=%s company_id=%s "
                "agent_type=%s trace_id=%s duration_ms=%.1f status=success",
                tool_name,
                tool_version,
                context.company_id,
                context.agent_type,
                trace_id,
                duration_ms,
            )
            return result
        except ToolError as exc:
            return await self._failure_result(
                tool_name=tool_name,
                tool_version=tool_version,
                trace_id=trace_id,
                error_code=exc.error_code,
                message=exc.message,
                started=started,
                context=context,
                agent_run_id=agent_run_id,
            )
        except TimeoutError:
            return await self._failure_result(
                tool_name=tool_name,
                tool_version=tool_version,
                trace_id=trace_id,
                error_code=ToolErrorCode.TOOL_TIMEOUT,
                message="Tool execution timed out.",
                started=started,
                context=context,
                agent_run_id=agent_run_id,
            )
        except Exception:
            logger.exception(
                "tool_execution_failed tool_name=%s version=%s company_id=%s trace_id=%s",
                tool_name,
                tool_version,
                context.company_id,
                trace_id,
            )
            return await self._failure_result(
                tool_name=tool_name,
                tool_version=tool_version,
                trace_id=trace_id,
                error_code=ToolErrorCode.TOOL_EXECUTION_FAILED,
                message="Tool execution failed.",
                started=started,
                context=context,
                agent_run_id=agent_run_id,
            )

    def _enforce_request_policy(self) -> None:
        if self._calls_this_request >= self._policy.max_calls_per_request:
            raise ToolPolicyLimitError("Maximum tool calls per request exceeded.")
        if self._total_ms_this_request >= self._policy.max_total_execution_ms:
            raise ToolPolicyLimitError("Maximum total tool execution time exceeded.")

    def _record_request_usage(self, duration_ms: float) -> None:
        self._calls_this_request += 1
        self._total_ms_this_request += duration_ms

    def _validate_input(self, tool: Tool, raw_input: dict[str, Any]) -> Any:
        encoded = json.dumps(raw_input, ensure_ascii=False)
        if len(encoded.encode("utf-8")) > self._policy.max_input_bytes:
            raise ToolInvalidInputError("Tool input exceeds allowed size.")
        try:
            return tool.input_model.model_validate(raw_input)
        except ValidationError as exc:
            raise ToolInvalidInputError("Tool input is invalid.") from exc

    def _validate_output(self, tool: Tool, raw_output: Any) -> Any:
        if not isinstance(raw_output, tool.output_model):
            try:
                return tool.output_model.model_validate(raw_output)
            except ValidationError as exc:
                raise ToolInvalidOutputError() from exc
        return raw_output

    def _enforce_output_size(self, output_dict: dict[str, Any]) -> None:
        encoded = json.dumps(output_dict, ensure_ascii=False)
        if len(encoded.encode("utf-8")) > self._policy.max_output_bytes:
            raise ToolResultTooLargeError()

    def _timeout_for_category(self, category: ToolCategory) -> int:
        if category is ToolCategory.EXTERNAL:
            return self._policy.external_timeout_ms
        return self._policy.default_timeout_ms

    async def _failure_result(
        self,
        *,
        tool_name: str,
        tool_version: str,
        trace_id: str,
        error_code: ToolErrorCode,
        message: str,
        started: float,
        context: ToolExecutionContext,
        agent_run_id: uuid.UUID | None,
    ) -> ToolResult:
        duration_ms = (time.perf_counter() - started) * 1000
        self._record_request_usage(duration_ms)
        if self._audit:
            await persist_tool_execution_audit(
                self._db,
                context=context,
                tool_name=tool_name,
                tool_version=tool_version,
                success=False,
                duration_ms=duration_ms,
                error_code=error_code,
                agent_run_id=agent_run_id,
            )
        logger.info(
            "tool_execution_failed tool_name=%s version=%s company_id=%s "
            "agent_type=%s trace_id=%s duration_ms=%.1f status=%s",
            tool_name,
            tool_version,
            context.company_id,
            context.agent_type,
            trace_id,
            duration_ms,
            error_code.value,
        )
        return ToolResult(
            success=False,
            tool_name=tool_name,
            tool_version=tool_version,
            error_code=error_code.value,
            error_message=message,
            trace_id=trace_id,
            executed_at=datetime.now(UTC),
            duration_ms=duration_ms,
        )
