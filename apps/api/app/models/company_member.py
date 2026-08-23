"""Company Member model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class CompanyMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Company Member entity."""

    __tablename__ = "company_members"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint("company_id", "user_id", name="uq_company_members_company_user"),
        Index("ix_company_members_company_id", "company_id"),
        Index("ix_company_members_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<CompanyMember id={self.id} "
            f"company_id={self.company_id} "
            f"user_id={self.user_id} role={self.role}>"
        )
