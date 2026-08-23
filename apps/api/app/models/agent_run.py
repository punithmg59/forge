"""Agent Run model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class AgentRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Agent Run entity."""

    __tablename__ = "agent_runs"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    agent_type: Mapped[str] = mapped_column(nullable=False)
    objective_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("objectives.id", ondelete="SET NULL"), nullable=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=False)
    model_provider: Mapped[str | None] = mapped_column(nullable=True)
    model_name: Mapped[str | None] = mapped_column(nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(nullable=True)
    started_at: Mapped[str | None] = mapped_column(nullable=True)
    completed_at: Mapped[str | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    trace_id: Mapped[str | None] = mapped_column(nullable=True)

    # Constraints
    __table_args__ = (
        Index("ix_agent_runs_company_id", "company_id"),
        Index("ix_agent_runs_objective_id", "objective_id"),
        Index("ix_agent_runs_company_id_status", "company_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<AgentRun id={self.id} company_id={self.company_id} agent_type={self.agent_type}>"
