"""In-process tool registry with read-only enforcement."""

from __future__ import annotations

from app.core.config import settings
from app.schemas.tool import ToolEffect
from app.services.tools.base import Tool
from app.services.tools.builtins.company_context import CompanyContextTool
from app.services.tools.builtins.customer_evidence import CustomerEvidenceTool
from app.services.tools.builtins.objective_status import ObjectiveStatusTool
from app.services.tools.errors import ToolNotFoundError, ToolWriteNotAllowedError

_REGISTRY: dict[str, Tool] = {}
_DISABLED: set[str] = set()


def _ensure_builtins_registered() -> None:
    if _REGISTRY:
        return
    register(CompanyContextTool())
    register(ObjectiveStatusTool())
    register(CustomerEvidenceTool())


def register(tool: Tool, *, allow_write: bool | None = None) -> None:
    """Register a tool. Write tools are rejected unless explicitly allowed."""
    if tool.effect is ToolEffect.WRITE:
        permitted = allow_write if allow_write is not None else settings.tool_allow_write_tools
        if not permitted:
            raise ToolWriteNotAllowedError(tool.qualified_name)
    qualified = tool.qualified_name
    if qualified in _REGISTRY:
        raise ValueError(f"Duplicate tool registration: {qualified}")
    _REGISTRY[qualified] = tool


def unregister(qualified_name: str) -> None:
    """Remove a tool from the registry (testing only)."""
    _REGISTRY.pop(qualified_name, None)
    _DISABLED.discard(qualified_name)


def disable_tool(qualified_name: str) -> None:
    _ensure_builtins_registered()
    if qualified_name not in _REGISTRY:
        raise ToolNotFoundError(qualified_name)
    _DISABLED.add(qualified_name)


def enable_tool(qualified_name: str) -> None:
    _DISABLED.discard(qualified_name)


def is_tool_enabled(qualified_name: str) -> bool:
    _ensure_builtins_registered()
    tool = _REGISTRY.get(qualified_name)
    if tool is None:
        return False
    return tool.enabled and qualified_name not in _DISABLED


def get_tool(qualified_name: str) -> Tool:
    """Resolve tool by qualified name. Unknown tools fail explicitly."""
    _ensure_builtins_registered()
    tool = _REGISTRY.get(qualified_name)
    if tool is None:
        raise ToolNotFoundError(qualified_name)
    return tool


def list_tools(*, include_disabled: bool = False) -> tuple[Tool, ...]:
    """List registered tools. By default only enabled tools are returned."""
    _ensure_builtins_registered()
    tools = list(_REGISTRY.values())
    if include_disabled:
        return tuple(tools)
    return tuple(t for t in tools if is_tool_enabled(t.qualified_name))


def registered_tool_names() -> frozenset[str]:
    _ensure_builtins_registered()
    return frozenset(_REGISTRY.keys())
