"""Company Constraint model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class CompanyConstraint(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Company Constraint entity."""

    __tablename__ = "company_constraints"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    value: Mapped[str | None] = mapped_column(nullable=True)
    severity: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)

    # Constraints
    __table_args__ = (
        Index("ix_company_constraints_company_id", "company_id"),
        Index("ix_company_constraints_company_id_status", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<CompanyConstraint id={self.id} company_id={self.company_id} type={self.type}>"
