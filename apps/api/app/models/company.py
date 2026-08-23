"""Company model."""

from __future__ import annotations

from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Company(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Company entity."""

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(nullable=True)
    slug: Mapped[str] = mapped_column(unique=True, nullable=True)
    mission: Mapped[str | None] = mapped_column(nullable=True)
    vision: Mapped[str | None] = mapped_column(nullable=True)
    product_description: Mapped[str | None] = mapped_column(nullable=True)
    target_customer: Mapped[str | None] = mapped_column(nullable=True)
    stage: Mapped[str | None] = mapped_column(nullable=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint("slug", name="uq_companies_slug"),
        Index("ix_companies_slug", "slug"),
    )

    def __repr__(self) -> str:
        return f"<Company id={self.id} name={self.name} slug={self.slug}>"
