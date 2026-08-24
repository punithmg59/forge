"""Objective CRUD and lifecycle management."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.objective import Objective
from app.models.user import User

STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"
STATUS_ABANDONED = "abandoned"
STATUS_SUPERSEDED = "superseded"

OBJECTIVE_STATUSES = frozenset(
    {STATUS_ACTIVE, STATUS_COMPLETED, STATUS_ABANDONED, STATUS_SUPERSEDED}
)
TERMINAL_STATUSES = frozenset({STATUS_COMPLETED, STATUS_ABANDONED, STATUS_SUPERSEDED})

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    STATUS_ACTIVE: frozenset({STATUS_COMPLETED, STATUS_ABANDONED, STATUS_SUPERSEDED}),
}

LEGACY_PRIORITY_RANKS: dict[str, int] = {
    "critical": 400,
    "high": 300,
    "medium": 200,
    "low": 100,
}

MIN_OBJECTIVE_PRIORITY = 0
MAX_OBJECTIVE_PRIORITY = 1_000_000
MAX_OBJECTIVE_TITLE_LENGTH = 500
DEFAULT_OBJECTIVE_PRIORITY = 100


class ObjectiveError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def validate_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized not in OBJECTIVE_STATUSES:
        allowed = ", ".join(sorted(OBJECTIVE_STATUSES))
        raise ValueError(f"Status must be one of: {allowed}")
    return normalized


def priority_rank(priority: str) -> int:
    """Higher rank means higher priority. Supports numeric strings and legacy labels."""
    stripped = priority.strip().lower()
    if stripped.isdigit():
        return int(stripped)
    return LEGACY_PRIORITY_RANKS.get(stripped, 0)


def normalize_priority(priority: str) -> int:
    return priority_rank(priority)


def format_priority(priority: int) -> str:
    return str(priority)


def select_current_objective(objectives: Sequence[Objective]) -> Objective | None:
    """Return the highest-priority active objective, with deterministic tie-breaking."""
    active = [objective for objective in objectives if objective.status == STATUS_ACTIVE]
    if not active:
        return None
    return max(
        active,
        key=lambda objective: (
            priority_rank(objective.priority),
            objective.created_at,
            objective.id,
        ),
    )


def sort_objectives(objectives: Sequence[Objective]) -> list[Objective]:
    return sorted(
        objectives,
        key=lambda objective: (
            -priority_rank(objective.priority),
            objective.created_at,
            objective.id,
        ),
    )


def validate_lifecycle_transition(current_status: str, next_status: str) -> None:
    if current_status == next_status:
        return
    allowed = ALLOWED_TRANSITIONS.get(current_status, frozenset())
    if next_status not in allowed:
        raise ObjectiveError(
            f"Cannot transition objective from '{current_status}' to '{next_status}'",
            400,
        )


async def create_objective(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    user: User,
    title: str,
    description: str | None,
    priority: int,
    target_value: str | None,
    target_unit: str | None,
    deadline: str | None,
) -> Objective:
    objective = Objective(
        company_id=company_id,
        title=title.strip(),
        description=description.strip() if description else None,
        status=STATUS_ACTIVE,
        priority=format_priority(priority),
        target_value=target_value.strip() if target_value else None,
        target_unit=target_unit.strip() if target_unit else None,
        deadline=deadline.strip() if deadline else None,
        created_by=user.id,
    )
    db.add(objective)
    await db.commit()
    await db.refresh(objective)
    return objective


async def list_objectives(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
) -> list[Objective]:
    result = await db.execute(
        select(Objective).where(Objective.company_id == company_id)
    )
    return sort_objectives(result.scalars().all())


async def get_objective(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    objective_id: uuid.UUID,
) -> Objective | None:
    objective = await db.get(Objective, objective_id)
    if objective is None or objective.company_id != company_id:
        return None
    return objective


async def update_objective(
    db: AsyncSession,
    objective: Objective,
    *,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: int | None = None,
    target_value: str | None = None,
    target_unit: str | None = None,
    deadline: str | None = None,
) -> Objective:
    if status is not None:
        next_status = validate_status(status)
        if objective.status in TERMINAL_STATUSES and next_status != objective.status:
            raise ObjectiveError(
                f"Cannot transition objective from '{objective.status}' to '{next_status}'",
                400,
            )
        validate_lifecycle_transition(objective.status, next_status)
        objective.status = next_status

    if title is not None:
        objective.title = title.strip()
    if description is not None:
        objective.description = description.strip() or None
    if priority is not None:
        objective.priority = format_priority(priority)
    if target_value is not None:
        objective.target_value = target_value.strip() or None
    if target_unit is not None:
        objective.target_unit = target_unit.strip() or None
    if deadline is not None:
        objective.deadline = deadline.strip() or None

    await db.commit()
    await db.refresh(objective)
    return objective


async def get_current_objective(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
) -> Objective | None:
    objectives = await list_objectives(db, company_id=company_id)
    return select_current_objective(objectives)
