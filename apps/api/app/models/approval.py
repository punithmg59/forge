"""Approval model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Approval(Base, UUIDPrimaryKeyMixin):
    """Approval entity."""

    __tablename__ = "approvals"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="SET NULL"), nullable=True
    )
    learning_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("learnings.id", ondelete="SET NULL"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    risk_level: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    requested_at: Mapped[str] = mapped_column(nullable=False)
    resolved_at: Mapped[str | None] = mapped_column(nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    plan_fingerprint: Mapped[str | None] = mapped_column(nullable=True)
    expires_at: Mapped[str | None] = mapped_column(nullable=True)

    # Constraints
    __table_args__ = (
        Index("ix_approvals_company_id", "company_id"),
        Index("ix_approvals_agent_task_id", "agent_task_id"),
        Index("ix_approvals_learning_id", "learning_id"),
        Index("ix_approvals_company_id_status", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Approval id={self.id} company_id={self.company_id} status={self.status}>"
