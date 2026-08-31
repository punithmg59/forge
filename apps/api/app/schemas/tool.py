"""Tool execution contracts. Tools are capabilities — not Brain truth."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToolCategory(str, Enum):
    COMPANY = "company"
    ANALYTICS = "analytics"
    CUSTOMER = "customer"
    PRODUCT = "product"
    EXTERNAL = "external"
    SYSTEM = "system"


class ToolPermission(str, Enum):
    COMPANY_READ = "company_read"
    ANALYTICS_READ = "analytics_read"
    CUSTOMER_READ = "customer_read"
    PRODUCT_READ = "product_read"
    EXTERNAL_READ = "external_read"


class ToolEffect(str, Enum):
    READ = "read"
    WRITE = "write"


class ToolErrorCode(str, Enum):
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_DISABLED = "TOOL_DISABLED"
    TOOL_UNAUTHORIZED = "TOOL_UNAUTHORIZED"
    TOOL_INVALID_INPUT = "TOOL_INVALID_INPUT"
    TOOL_INVALID_OUTPUT = "TOOL_INVALID_OUTPUT"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_RESULT_TOO_LARGE = "TOOL_RESULT_TOO_LARGE"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"
    TOOL_WRITE_NOT_ALLOWED = "TOOL_WRITE_NOT_ALLOWED"
    TOOL_POLICY_LIMIT = "TOOL_POLICY_LIMIT"


MAX_TOOL_INPUT_BYTES = 8192
MAX_TOOL_OUTPUT_BYTES = 65536
MAX_TOOL_RECORDS = 100


class ToolExecutionContext(BaseModel):
    """Server-side execution context. Tenant scope is never taken from tool arguments."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    company_id: uuid.UUID
    user_id: uuid.UUID
    membership_role: str
    agent_type: str
    trace_id: str
    request_id: str | None = None
    permissions: frozenset[ToolPermission] = Field(default_factory=frozenset)


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(min_length=1, max_length=128)
    tool_version: str = Field(min_length=1, max_length=32)
    input: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None

    @property
    def qualified_name(self) -> str:
        return f"{self.tool_name}:{self.tool_version}"

    @field_validator("tool_name", "tool_version")
    @classmethod
    def strip_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class ToolResultProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    company_id: uuid.UUID


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    tool_name: str
    tool_version: str
    data: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    trace_id: str
    executed_at: datetime
    provenance: ToolResultProvenance | None = None
    duration_ms: float | None = None


# --- Built-in tool I/O models ---


class CompanyContextOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: uuid.UUID
    name: str | None = None
    slug: str | None = None
    stage: str | None = None
    mission: str | None = None
    vision: str | None = None
    product_description: str | None = None
    target_customer: str | None = None


class CompanyContextInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ObjectiveStatusOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    has_active_objective: bool
    objective_id: uuid.UUID | None = None
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    target_value: str | None = None
    target_unit: str | None = None
    deadline: str | None = None


class ObjectiveStatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    type: str
    title: str
    content_preview: str
    source_type: str
    observed_at: str | None = None


class CustomerEvidenceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence: list[EvidenceSummary] = Field(default_factory=list)
    count: int


class CustomerEvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=20, ge=1, le=MAX_TOOL_RECORDS)
    evidence_type: str | None = Field(default=None, max_length=128)

    @field_validator("evidence_type")
    @classmethod
    def normalize_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None
