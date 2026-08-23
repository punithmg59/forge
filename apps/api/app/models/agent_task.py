"""Agent Task model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class AgentTask(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Agent Task entity."""

    __tablename__ = "agent_tasks"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )
    objective_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("objective_tasks.id", ondelete="SET NULL"), nullable=True
    )
    agent_type: Mapped[str] = mapped_column(nullable=False)
    task_type: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    input: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cost: Mapped[float | None] = mapped_column(nullable=True)
    started_at: Mapped[str | None] = mapped_column(nullable=True)
    completed_at: Mapped[str | None] = mapped_column(nullable=True)

    # Constraints
    __table_args__ = (
        Index("ix_agent_tasks_company_id", "company_id"),
        Index("ix_agent_tasks_agent_run_id", "agent_run_id"),
        Index("ix_agent_tasks_company_id_status", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<AgentTask id={self.id} company_id={self.company_id} task_type={self.task_type}>"
