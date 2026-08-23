"""Metric model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Metric(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Metric entity."""

    __tablename__ = "metrics"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    source: Mapped[str | None] = mapped_column(nullable=True)
    unit: Mapped[str | None] = mapped_column(nullable=True)
    target_value: Mapped[str | None] = mapped_column(nullable=True)

    # Constraints
    __table_args__ = (
        Index("ix_metrics_company_id", "company_id"),
    )

    def __repr__(self) -> str:
        return f"<Metric id={self.id} company_id={self.company_id} name={self.name}>"
