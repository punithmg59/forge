"""Hypothesis model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Hypothesis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Hypothesis entity."""

    __tablename__ = "hypotheses"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    objective_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("objectives.id", ondelete="CASCADE"), nullable=False
    )
    statement: Mapped[str] = mapped_column(nullable=False)
    reasoning: Mapped[str | None] = mapped_column(nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=False)

    # Constraints
    __table_args__ = (
        Index("ix_hypotheses_company_id", "company_id"),
        Index("ix_hypotheses_objective_id", "objective_id"),
        Index("ix_hypotheses_company_id_status", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<Hypothesis id={self.id} "
            f"company_id={self.company_id} "
            f"objective_id={self.objective_id}>"
        )
