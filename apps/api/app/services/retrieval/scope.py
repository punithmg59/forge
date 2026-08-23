"""Tenant scope for future retrieval. Never pass a raw company_id alone."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from app.models.company_member import CompanyMember


class RetrievalScope(BaseModel):
    """Authorized company context derived from existing membership checks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    company_id: uuid.UUID
    user_id: uuid.UUID
    role: str

    @classmethod
    def from_membership(cls, membership: CompanyMember) -> RetrievalScope:
        """Build scope from Task 3/4 CompanyMember (require_company_access)."""
        return cls(
            company_id=membership.company_id,
            user_id=membership.user_id,
            role=membership.role,
        )
