"""Experiment model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Experiment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Experiment entity."""

    __tablename__ = "experiments"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    objective_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("objectives.id", ondelete="CASCADE"), nullable=False
    )
    hypothesis_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("hypotheses.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    method: Mapped[str | None] = mapped_column(nullable=True)
    primary_metric: Mapped[str | None] = mapped_column(nullable=True)
    target_value: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=False)
    started_at: Mapped[str | None] = mapped_column(nullable=True)
    ended_at: Mapped[str | None] = mapped_column(nullable=True)

    # Constraints
    __table_args__ = (
        Index("ix_experiments_company_id", "company_id"),
        Index("ix_experiments_objective_id", "objective_id"),
        Index("ix_experiments_company_id_status", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Experiment id={self.id} company_id={self.company_id} name={self.name}>"
