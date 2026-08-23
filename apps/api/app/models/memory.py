"""Memory model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import Vector

if TYPE_CHECKING:
    pass


# Embedding dimension configuration
EMBEDDING_DIMENSION = 1024


class Memory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Memory entity."""

    __tablename__ = "memories"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    memory_type: Mapped[str] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    embedding: Mapped[Vector] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=True)
    source_type: Mapped[str] = mapped_column(nullable=False)
    source_reference: Mapped[str | None] = mapped_column(nullable=True)
    importance: Mapped[float | None] = mapped_column(nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)

    # Constraints
    __table_args__ = (
        Index("ix_memories_company_id", "company_id"),
        Index("ix_memories_company_id_created_at", "company_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Memory id={self.id} company_id={self.company_id} type={self.memory_type}>"
