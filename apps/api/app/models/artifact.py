"""Artifact model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Artifact(Base, UUIDPrimaryKeyMixin):
    """Artifact entity."""

    __tablename__ = "artifacts"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="SET NULL"), nullable=True
    )
    artifact_type: Mapped[str] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    storage_uri: Mapped[str | None] = mapped_column(nullable=True)
    mime_type: Mapped[str | None] = mapped_column(nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Constraints
    __table_args__ = (
        Index("ix_artifacts_company_id", "company_id"),
        Index("ix_artifacts_agent_task_id", "agent_task_id"),
    )

    def __repr__(self) -> str:
        return f"<Artifact id={self.id} company_id={self.company_id} type={self.artifact_type}>"
