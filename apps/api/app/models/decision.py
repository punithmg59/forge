"""Decision model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Decision(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Decision entity."""

    __tablename__ = "decisions"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    objective_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("objectives.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(nullable=False)
    decision: Mapped[str] = mapped_column(nullable=False)
    rationale: Mapped[str] = mapped_column(nullable=False)
    expected_outcome: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=False)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Constraints
    __table_args__ = (
        Index("ix_decisions_company_id", "company_id"),
        Index("ix_decisions_objective_id", "objective_id"),
        Index("ix_decisions_company_id_status", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Decision id={self.id} company_id={self.company_id} title={self.title}>"
