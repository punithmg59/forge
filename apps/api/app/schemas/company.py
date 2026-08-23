from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    target_customer: str | None = Field(default=None, max_length=2000)
    stage: str | None = Field(default=None, max_length=100)


class CompanyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    target_customer: str | None = Field(default=None, max_length=2000)
    stage: str | None = Field(default=None, max_length=100)


class CompanyPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str | None
    slug: str | None
    description: str | None = None
    target_customer: str | None = None
    stage: str | None = None
    created_at: datetime

    @classmethod
    def from_company(cls, company: object) -> CompanyPublic:
        return cls(
            id=company.id,  # type: ignore[attr-defined]
            name=company.name,  # type: ignore[attr-defined]
            slug=company.slug,  # type: ignore[attr-defined]
            description=company.product_description,  # type: ignore[attr-defined]
            target_customer=company.target_customer,  # type: ignore[attr-defined]
            stage=company.stage,  # type: ignore[attr-defined]
            created_at=company.created_at,  # type: ignore[attr-defined]
        )


class CompanyMemberPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    role: str
    email: str | None = None
    name: str | None = None
