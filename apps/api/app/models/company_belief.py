"""Company Belief model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class CompanyBelief(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Company Belief entity."""

    __tablename__ = "company_beliefs"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    statement: Mapped[str] = mapped_column(nullable=False)
    reasoning: Mapped[str | None] = mapped_column(nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=False)
    source: Mapped[str | None] = mapped_column(nullable=True)

    # Constraints
    __table_args__ = (
        Index("ix_company_beliefs_company_id", "company_id"),
        Index("ix_company_beliefs_company_id_status", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<CompanyBelief id={self.id} company_id={self.company_id} status={self.status}>"
