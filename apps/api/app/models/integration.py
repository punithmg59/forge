"""Integration model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Integration(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Integration entity."""

    __tablename__ = "integrations"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(nullable=False)
    integration_type: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    scopes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Constraints
    __table_args__ = (
        Index("ix_integrations_company_id", "company_id"),
        Index("ix_integrations_company_id_status", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Integration id={self.id} company_id={self.company_id} provider={self.provider}>"
