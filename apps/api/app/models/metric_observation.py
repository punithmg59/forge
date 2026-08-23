"""Metric Observation model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class MetricObservation(Base, UUIDPrimaryKeyMixin):
    """Metric Observation entity."""

    __tablename__ = "metric_observations"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    metric_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("metrics.id", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[str] = mapped_column(nullable=False)
    observed_at: Mapped[str] = mapped_column(nullable=False)
    source_reference: Mapped[str | None] = mapped_column(nullable=True)

    # Constraints
    __table_args__ = (
        Index("ix_metric_observations_metric_id", "metric_id"),
        Index("ix_metric_observations_company_id", "company_id"),
    )

    def __repr__(self) -> str:
        return f"<MetricObservation id={self.id} metric_id={self.metric_id} value={self.value}>"
