"""Unit tests for objective priority and lifecycle helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.models.objective import Objective
from app.services.objective_service import (
    STATUS_ACTIVE,
    STATUS_COMPLETED,
    ObjectiveError,
    priority_rank,
    select_current_objective,
    validate_lifecycle_transition,
)


def _objective(*, title: str, priority: str, status: str = STATUS_ACTIVE) -> Objective:
    now = datetime.now(UTC)
    return Objective(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        title=title,
        status=status,
        priority=priority,
        created_at=now,
        updated_at=now,
    )


def test_priority_rank_supports_numeric_and_legacy_labels() -> None:
    assert priority_rank("500") == 500
    assert priority_rank("high") == 300
    assert priority_rank("low") == 100


def test_select_current_objective_uses_priority_then_created_at() -> None:
    older = _objective(title="older", priority="100")
    newer = _objective(title="newer", priority="100")
    higher = _objective(title="higher", priority="250")
    current = select_current_objective([older, newer, higher])
    assert current is not None
    assert current.title == "higher"


def test_select_current_objective_returns_none_without_active() -> None:
    completed = _objective(title="done", priority="100", status=STATUS_COMPLETED)
    assert select_current_objective([completed]) is None


def test_validate_lifecycle_transition_rejects_completed_to_active() -> None:
    try:
        validate_lifecycle_transition(STATUS_COMPLETED, STATUS_ACTIVE)
    except ObjectiveError as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("expected ObjectiveError")
