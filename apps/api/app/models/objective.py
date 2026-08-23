"""Objective model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Objective(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Objective entity."""

    __tablename__ = "objectives"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=False)
    priority: Mapped[str] = mapped_column(nullable=False)
    target_value: Mapped[str | None] = mapped_column(nullable=True)
    target_unit: Mapped[str | None] = mapped_column(nullable=True)
    deadline: Mapped[str | None] = mapped_column(nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Constraints
    __table_args__ = (
        Index("ix_objectives_company_id", "company_id"),
        Index("ix_objectives_company_id_status", "company_id", "status"),
        Index("ix_objectives_company_id_created_at", "company_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Objective id={self.id} company_id={self.company_id} title={self.title}>"
