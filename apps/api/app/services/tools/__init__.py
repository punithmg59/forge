"""Enterprise tool registry and safe execution layer."""

from __future__ import annotations

from app.services.tools.audit import (
    TOOL_EXECUTION_TASK_TYPE,
    TOOL_RUNNER_AGENT_TYPE,
    persist_tool_execution_audit,
)
from app.services.tools.authorization import authorize_tool_execution, permissions_for_role
from app.services.tools.base import Tool
from app.services.tools.context import build_tool_execution_context
from app.services.tools.errors import ToolError
from app.services.tools.executor import ToolExecutor
from app.services.tools.policy import ToolExecutionPolicy
from app.services.tools.registry import (
    disable_tool,
    enable_tool,
    get_tool,
    list_tools,
    register,
    registered_tool_names,
    unregister,
)

__all__ = [
    "TOOL_EXECUTION_TASK_TYPE",
    "TOOL_RUNNER_AGENT_TYPE",
    "Tool",
    "ToolError",
    "ToolExecutor",
    "ToolExecutionPolicy",
    "authorize_tool_execution",
    "build_tool_execution_context",
    "disable_tool",
    "enable_tool",
    "get_tool",
    "list_tools",
    "permissions_for_role",
    "persist_tool_execution_audit",
    "register",
    "registered_tool_names",
    "unregister",
]
