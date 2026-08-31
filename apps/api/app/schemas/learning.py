"""Learning proposal contracts. Proposals are not approved Company Brain truth."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LearningConfidence = Literal["low", "medium", "high"]
LearningExtractionDecision = Literal["learning", "no_learning"]

class ExtractedLearningPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1)
    confidence: LearningConfidence
    reason: str = Field(min_length=1)


class LearningExtractionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: LearningExtractionDecision
    learning: ExtractedLearningPayload | None = None
    reason: str | None = None
    source_evidence_ids: list[str] = Field(default_factory=list)


class LearningProposalPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    evidence_id: uuid.UUID | None
    objective_id: uuid.UUID | None
    statement: str
    evidence_summary: str | None
    confidence: float | None
    status: str
    source_evidence_ids: list[uuid.UUID] = Field(default_factory=list)


class LearningProposalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: LearningExtractionDecision
    proposal: LearningProposalPublic | None = None
    reason: str | None = None


class LearningProvenancePublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: uuid.UUID | None = None
    evidence_title: str | None = None
    evidence_content: str | None = None
    evidence_observed_at: str | None = None
    objective_task_id: uuid.UUID | None = None
    objective_task_title: str | None = None
    objective_id: uuid.UUID | None = None
    objective_title: str | None = None


class LearningPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    evidence_id: uuid.UUID | None
    objective_id: uuid.UUID | None
    statement: str
    evidence_summary: str | None
    confidence: float | None
    status: str
    created_at: datetime
    updated_at: datetime
    corrected_by: uuid.UUID | None = None
    corrected_at: datetime | None = None
    correction_reason: str | None = None
    provenance: LearningProvenancePublic | None = None
    approval_status: str | None = None


class LearningListResponse(BaseModel):
    learnings: list[LearningPublic]


class LearningCorrectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)
