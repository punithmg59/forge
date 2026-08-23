"""Objective Task model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class ObjectiveTask(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Objective Task entity."""

    __tablename__ = "objective_tasks"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    objective_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("objectives.id", ondelete="CASCADE"), nullable=False
    )
    hypothesis_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("hypotheses.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    capability: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    priority: Mapped[str] = mapped_column(nullable=False)
    assigned_agent: Mapped[str | None] = mapped_column(nullable=True)
    requires_approval: Mapped[bool] = mapped_column(nullable=False)
    started_at: Mapped[str | None] = mapped_column(nullable=True)
    completed_at: Mapped[str | None] = mapped_column(nullable=True)

    # Constraints
    __table_args__ = (
        Index("ix_objective_tasks_company_id", "company_id"),
        Index("ix_objective_tasks_objective_id", "objective_id"),
        Index("ix_objective_tasks_company_id_status", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<ObjectiveTask id={self.id} "
            f"company_id={self.company_id} "
            f"objective_id={self.objective_id}>"
        )
