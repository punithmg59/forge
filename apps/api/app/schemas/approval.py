"""Approval workflow contracts for Head Agent recommendations and Learning proposals."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.head_agent import HeadAgentRecommendation
from app.schemas.learning import LearningProposalPublic

APPROVAL_STATUSES = frozenset({"pending", "approved", "rejected"})


class ApprovalCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_task_id: uuid.UUID | None = None
    learning_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_exactly_one_reference(self) -> ApprovalCreateRequest:
        has_agent_task = self.agent_task_id is not None
        has_learning = self.learning_id is not None
        if has_agent_task and has_learning:
            raise ValueError("Provide either agent_task_id or learning_id, not both")
        if not has_agent_task and not has_learning:
            raise ValueError("Either agent_task_id or learning_id is required")
        return self


class ApprovalPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    agent_task_id: uuid.UUID | None
    learning_id: uuid.UUID | None = None
    action_type: str
    description: str
    risk_level: str
    status: str
    requested_at: str
    resolved_at: str | None
    resolved_by: uuid.UUID | None
    objective_task_id: uuid.UUID | None = None
    recommendation: HeadAgentRecommendation | None = None
    learning_proposal: LearningProposalPublic | None = None


class ApprovalListResponse(BaseModel):
    approvals: list[ApprovalPublic]
