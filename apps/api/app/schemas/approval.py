"""Approval workflow contracts for Head Agent recommendations."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.head_agent import HeadAgentRecommendation

APPROVAL_STATUSES = frozenset({"pending", "approved", "rejected"})


class ApprovalCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_task_id: uuid.UUID


class ApprovalPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    agent_task_id: uuid.UUID | None
    action_type: str
    description: str
    risk_level: str
    status: str
    requested_at: str
    resolved_at: str | None
    resolved_by: uuid.UUID | None
    objective_task_id: uuid.UUID | None = None
    recommendation: HeadAgentRecommendation | None = None


class ApprovalListResponse(BaseModel):
    approvals: list[ApprovalPublic]
