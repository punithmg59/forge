"""Experiment Result model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class ExperimentResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Experiment Result entity."""

    __tablename__ = "experiment_results"

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    metric_name: Mapped[str] = mapped_column(nullable=False)
    baseline_value: Mapped[str | None] = mapped_column(nullable=True)
    result_value: Mapped[str | None] = mapped_column(nullable=True)
    unit: Mapped[str | None] = mapped_column(nullable=True)
    interpretation: Mapped[str | None] = mapped_column(nullable=True)
    success: Mapped[bool | None] = mapped_column(nullable=True)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True
    )
    recorded_at: Mapped[str] = mapped_column(nullable=False)

    # Constraints
    __table_args__ = (
        Index("ix_experiment_results_experiment_id", "experiment_id"),
        Index("ix_experiment_results_company_id", "company_id"),
    )

    def __repr__(self) -> str:
        return f"<ExperimentResult id={self.id} experiment_id={self.experiment_id}>"
