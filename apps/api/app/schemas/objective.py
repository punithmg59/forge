from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.objective_service import (
    MAX_OBJECTIVE_PRIORITY,
    MAX_OBJECTIVE_TITLE_LENGTH,
    MIN_OBJECTIVE_PRIORITY,
    normalize_priority,
    validate_status,
)

MAX_OBJECTIVE_DESCRIPTION_LENGTH = 4000
MAX_TARGET_VALUE_LENGTH = 500
MAX_TARGET_UNIT_LENGTH = 100
MAX_DEADLINE_LENGTH = 100


class ObjectiveCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=MAX_OBJECTIVE_TITLE_LENGTH)
    description: str | None = Field(default=None, max_length=MAX_OBJECTIVE_DESCRIPTION_LENGTH)
    priority: int = Field(default=100, ge=MIN_OBJECTIVE_PRIORITY, le=MAX_OBJECTIVE_PRIORITY)
    target_value: str | None = Field(default=None, max_length=MAX_TARGET_VALUE_LENGTH)
    target_unit: str | None = Field(default=None, max_length=MAX_TARGET_UNIT_LENGTH)
    deadline: str | None = Field(default=None, max_length=MAX_DEADLINE_LENGTH)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Title is required")
        return stripped


class ObjectiveUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=MAX_OBJECTIVE_TITLE_LENGTH)
    description: str | None = Field(default=None, max_length=MAX_OBJECTIVE_DESCRIPTION_LENGTH)
    status: str | None = None
    priority: int | None = Field(default=None, ge=MIN_OBJECTIVE_PRIORITY, le=MAX_OBJECTIVE_PRIORITY)
    target_value: str | None = Field(default=None, max_length=MAX_TARGET_VALUE_LENGTH)
    target_unit: str | None = Field(default=None, max_length=MAX_TARGET_UNIT_LENGTH)
    deadline: str | None = Field(default=None, max_length=MAX_DEADLINE_LENGTH)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("Title cannot be blank")
        return stripped

    @field_validator("status")
    @classmethod
    def status_is_valid(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_status(value)


class ObjectivePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    description: str | None
    status: str
    priority: int
    target_value: str | None
    target_unit: str | None
    deadline: str | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_objective(cls, objective: object) -> ObjectivePublic:
        return cls(
            id=objective.id,  # type: ignore[attr-defined]
            company_id=objective.company_id,  # type: ignore[attr-defined]
            title=objective.title,  # type: ignore[attr-defined]
            description=objective.description,  # type: ignore[attr-defined]
            status=objective.status,  # type: ignore[attr-defined]
            priority=normalize_priority(objective.priority),  # type: ignore[attr-defined]
            target_value=objective.target_value,  # type: ignore[attr-defined]
            target_unit=objective.target_unit,  # type: ignore[attr-defined]
            deadline=objective.deadline,  # type: ignore[attr-defined]
            created_by=objective.created_by,  # type: ignore[attr-defined]
            created_at=objective.created_at,  # type: ignore[attr-defined]
            updated_at=objective.updated_at,  # type: ignore[attr-defined]
        )


class ObjectiveListResponse(BaseModel):
    objectives: list[ObjectivePublic]
    current_objective: ObjectivePublic | None
