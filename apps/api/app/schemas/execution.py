"""Autonomous execution domain contracts. Plans are data — not executable instructions."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_EXECUTION_GOAL_LENGTH = 2000
MAX_EXECUTION_RATIONALE_LENGTH = 4000
MAX_STEP_PURPOSE_LENGTH = 1000
MAX_STEP_ID_LENGTH = 64
MAX_EXECUTION_ERROR_MESSAGE_LENGTH = 500
MAX_CANCEL_REASON_LENGTH = 500

TOOL_QUALIFIED_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:v[0-9]+$")

ExecutionStatus = Literal[
    "requested",
    "planned",
    "waiting_for_approval",
    "approved",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    "retrying",
]

ExecutionStepStatus = Literal[
    "pending",
    "waiting_for_approval",
    "approved",
    "running",
    "succeeded",
    "failed",
    "skipped",
    "cancelled",
]

ExecutionRisk = Literal["low", "medium", "high", "critical"]

EXECUTION_TERMINAL_STATUSES = frozenset({"succeeded", "cancelled"})
EXECUTION_STEP_TERMINAL_STATUSES = frozenset(
    {"succeeded", "failed", "skipped", "cancelled"}
)


class ExecutionStepCategory(str, Enum):
    """Risk/category bucket for approval policy evaluation."""

    READ_ONLY_LOW_RISK = "read_only_low_risk"
    READ_ONLY_HIGH_COST = "read_only_high_cost"
    WRITE_LOW_RISK = "write_low_risk"
    WRITE_HIGH_RISK = "write_high_risk"
    EXTERNAL_SIDE_EFFECT = "external_side_effect"
    FINANCIAL_ACTION = "financial_action"
    COMMUNICATION_TO_CUSTOMER = "communication_to_customer"


class RetryPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_attempts: int = Field(default=1, ge=1, le=5)
    backoff_ms: int = Field(default=0, ge=0, le=60000)


class ExecutionStep(BaseModel):
    """One planned tool invocation. Data only — execution requires ToolExecutor."""

    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1, max_length=MAX_STEP_ID_LENGTH)
    sequence: int = Field(ge=1, le=100)
    tool_name: str = Field(min_length=1, max_length=128)
    tool_version: str = Field(min_length=1, max_length=32)
    purpose: str = Field(min_length=1, max_length=MAX_STEP_PURPOSE_LENGTH)
    input: dict[str, Any] = Field(default_factory=dict)
    expected_output: str | None = Field(default=None, max_length=2000)
    risk_level: ExecutionRisk
    step_category: ExecutionStepCategory
    approval_required: bool = True
    timeout_ms: int | None = Field(default=None, ge=100, le=120000)
    retry_policy: RetryPolicy | None = None

    @property
    def tool_qualified_name(self) -> str:
        return f"{self.tool_name}:{self.tool_version}"

    @field_validator("step_id", "tool_name", "tool_version", "purpose")
    @classmethod
    def strip_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class ExecutionPlan(BaseModel):
    """Structured execution plan produced by a planner. Never executed directly."""

    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=1, max_length=MAX_EXECUTION_GOAL_LENGTH)
    rationale: str = Field(min_length=1, max_length=MAX_EXECUTION_RATIONALE_LENGTH)
    risk_level: ExecutionRisk
    steps: list[ExecutionStep] = Field(min_length=1, max_length=50)

    @field_validator("goal", "rationale")
    @classmethod
    def strip_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @model_validator(mode="after")
    def validate_step_uniqueness(self) -> ExecutionPlan:
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("step_id values must be unique within a plan")
        sequences = [step.sequence for step in self.steps]
        if len(sequences) != len(set(sequences)):
            raise ValueError("sequence values must be unique within a plan")
        return self


class ExecutionIdentity(BaseModel):
    """Stable execution identity scoped to authenticated tenant context."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: uuid.UUID
    company_id: uuid.UUID
    objective_id: uuid.UUID | None = None
    objective_task_id: uuid.UUID | None = None
    agent_type: str = Field(min_length=1, max_length=64)
    requested_by: uuid.UUID
    trace_id: str = Field(min_length=1, max_length=128)
    created_at: datetime


class ExecutionRequest(BaseModel):
    """Execution request contract. Status transitions are server-controlled."""

    model_config = ConfigDict(extra="forbid")

    identity: ExecutionIdentity
    status: ExecutionStatus
    plan: ExecutionPlan | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancel_reason: str | None = Field(default=None, max_length=MAX_CANCEL_REASON_LENGTH)
    failure_reason: str | None = Field(
        default=None,
        max_length=MAX_EXECUTION_ERROR_MESSAGE_LENGTH,
    )


class ExecutionAttempt(BaseModel):
    """Record of one step attempt."""

    model_config = ConfigDict(extra="forbid")

    attempt_id: uuid.UUID
    execution_id: uuid.UUID
    step_id: str
    attempt_number: int = Field(ge=1, le=10)
    status: ExecutionStepStatus
    started_at: datetime
    completed_at: datetime | None = None
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = Field(
        default=None,
        max_length=MAX_EXECUTION_ERROR_MESSAGE_LENGTH,
    )
    trace_id: str


class ExecutionStepResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    sequence: int
    status: ExecutionStepStatus
    tool_qualified_name: str
    output_summary: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    attempts: list[ExecutionAttempt] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: uuid.UUID
    company_id: uuid.UUID
    status: ExecutionStatus
    step_results: list[ExecutionStepResult] = Field(default_factory=list)
    completed_at: datetime | None = None
    failure_reason: str | None = None


class ExecutionPolicy(BaseModel):
    """Runtime policy limits for future execution runners."""

    model_config = ConfigDict(extra="forbid")

    max_steps_per_plan: int = Field(ge=1, le=50)
    max_tool_calls_per_step: int = Field(ge=1, le=20)
    max_retries_per_step: int = Field(ge=0, le=5)
    max_total_duration_ms: int = Field(ge=1000, le=600000)


class ApprovalRequirement(BaseModel):
    """Result of approval policy evaluation for a step or plan."""

    model_config = ConfigDict(extra="forbid")

    approval_required: bool
    step_category: ExecutionStepCategory
    risk_level: ExecutionRisk
    rationale: str
    auto_execution_eligible: bool = False


class ExecutionCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=MAX_CANCEL_REASON_LENGTH)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()
