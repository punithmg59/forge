from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ObjectiveTaskPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    objective_id: uuid.UUID
    title: str
    description: str | None
    capability: str
    status: str
    priority: str
    requires_approval: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_task(cls, task: object) -> ObjectiveTaskPublic:
        return cls(
            id=task.id,  # type: ignore[attr-defined]
            company_id=task.company_id,  # type: ignore[attr-defined]
            objective_id=task.objective_id,  # type: ignore[attr-defined]
            title=task.title,  # type: ignore[attr-defined]
            description=task.description,  # type: ignore[attr-defined]
            capability=task.capability,  # type: ignore[attr-defined]
            status=task.status,  # type: ignore[attr-defined]
            priority=task.priority,  # type: ignore[attr-defined]
            requires_approval=task.requires_approval,  # type: ignore[attr-defined]
            created_at=task.created_at,  # type: ignore[attr-defined]
            updated_at=task.updated_at,  # type: ignore[attr-defined]
        )


class ObjectiveTaskListResponse(BaseModel):
    tasks: list[ObjectiveTaskPublic]
