"""Onboarding Draft model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

STATUS_DRAFT = "draft"
STATUS_STRUCTURED = "structured"
STATUS_CONFIRMED = "confirmed"


class OnboardingDraft(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Partial onboarding input stored before Company Brain confirmation."""

    __tablename__ = "onboarding_drafts"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    current_step: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confirmed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("company_id", name="uq_onboarding_drafts_company_id"),
        Index("ix_onboarding_drafts_company_id", "company_id"),
        Index("ix_onboarding_drafts_status", "status"),
        Index("ix_onboarding_drafts_created_by_user_id", "created_by_user_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<OnboardingDraft id={self.id} "
            f"company_id={self.company_id} status={self.status}>"
        )
