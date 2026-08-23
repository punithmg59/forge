"""Company Brain Profile model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.company import Company


class CompanyBrainProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Company Brain Profile entity."""

    __tablename__ = "company_brain_profiles"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    strategy: Mapped[str | None] = mapped_column(nullable=True)
    non_goals: Mapped[str | None] = mapped_column(nullable=True)
    current_priorities: Mapped[str | None] = mapped_column(nullable=True)
    current_bottlenecks: Mapped[str | None] = mapped_column(nullable=True)
    working_style: Mapped[str | None] = mapped_column(nullable=True)
    version: Mapped[int] = mapped_column(default=1, nullable=False)

    # Relationships
    company: Mapped[Company] = relationship(backref="brain_profile")

    # Constraints
    __table_args__ = (
        UniqueConstraint("company_id", name="uq_company_brain_profiles_company_id"),
        Index("ix_company_brain_profiles_company_id", "company_id"),
    )

    def __repr__(self) -> str:
        return f"<CompanyBrainProfile id={self.id} company_id={self.company_id}>"
