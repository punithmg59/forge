"""Tool registry tests."""

from __future__ import annotations

import pytest

from app.schemas.tool import ToolCategory, ToolEffect, ToolPermission
from app.services.tools.base import Tool
from app.services.tools.builtins.company_context import CompanyContextTool
from app.services.tools.errors import ToolNotFoundError, ToolWriteNotAllowedError
from app.services.tools.registry import (
    disable_tool,
    enable_tool,
    get_tool,
    list_tools,
    register,
    registered_tool_names,
)
from pydantic import BaseModel, ConfigDict


class _EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _EmptyOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _WriteTool(Tool[_EmptyInput, _EmptyOutput]):
    @property
    def name(self) -> str:
        return "write_test"

    @property
    def version(self) -> str:
        return "v1"

    @property
    def description(self) -> str:
        return "write tool for tests"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SYSTEM

    @property
    def effect(self) -> ToolEffect:
        return ToolEffect.WRITE

    @property
    def required_permissions(self) -> frozenset[ToolPermission]:
        return frozenset({ToolPermission.COMPANY_READ})

    @property
    def input_model(self) -> type[_EmptyInput]:
        return _EmptyInput

    @property
    def output_model(self) -> type[_EmptyOutput]:
        return _EmptyOutput

    async def execute(self, db, context, validated_input):  # noqa: ANN001
        return _EmptyOutput()


def test_registry_lists_builtin_tools() -> None:
    names = registered_tool_names()
    assert "company_context:v1" in names
    assert "objective_status:v1" in names
    assert "customer_evidence:v1" in names


def test_get_tool_returns_registered_tool() -> None:
    tool = get_tool("company_context:v1")
    assert tool.name == "company_context"
    assert tool.version == "v1"


def test_unknown_tool_raises() -> None:
    with pytest.raises(ToolNotFoundError):
        get_tool("stripe_revenue:v1")


def test_duplicate_registration_rejected() -> None:
    duplicate = CompanyContextTool()
    with pytest.raises(ValueError, match="Duplicate"):
        register(duplicate)


def test_write_tool_rejected_by_default() -> None:
    write_tool = _WriteTool()
    with pytest.raises(ToolWriteNotAllowedError):
        register(write_tool)


def test_disabled_tool_not_listed() -> None:
    disable_tool("company_context:v1")
    enabled = {t.qualified_name for t in list_tools()}
    assert "company_context:v1" not in enabled
    enable_tool("company_context:v1")
    enabled_after = {t.qualified_name for t in list_tools()}
    assert "company_context:v1" in enabled_after


def test_registry_lookup_is_fast() -> None:
    import time

    start = time.perf_counter()
    for _ in range(1000):
        get_tool("objective_status:v1")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 50
