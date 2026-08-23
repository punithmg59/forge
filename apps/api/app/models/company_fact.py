"""Company Fact model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class CompanyFact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Company Fact entity."""

    __tablename__ = "company_facts"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(nullable=False)
    value: Mapped[str] = mapped_column(nullable=False)
    value_type: Mapped[str] = mapped_column(nullable=False)
    source_type: Mapped[str] = mapped_column(nullable=False)
    source_reference: Mapped[str | None] = mapped_column(nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=False)
    observed_at: Mapped[str | None] = mapped_column(nullable=True)

    # Constraints
    __table_args__ = (
        Index("ix_company_facts_company_id", "company_id"),
        Index("ix_company_facts_company_id_status", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<CompanyFact id={self.id} company_id={self.company_id} key={self.key}>"
