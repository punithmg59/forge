"""Evidence model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Evidence(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Evidence entity."""

    __tablename__ = "evidence"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    source_type: Mapped[str] = mapped_column(nullable=False)
    source_reference: Mapped[str | None] = mapped_column(nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    observed_at: Mapped[str | None] = mapped_column(nullable=True)

    # Constraints
    __table_args__ = (
        Index("ix_evidence_company_id", "company_id"),
        Index("ix_evidence_company_id_created_at", "company_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Evidence id={self.id} company_id={self.company_id} type={self.type}>"
