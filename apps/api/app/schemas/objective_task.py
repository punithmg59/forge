from __future__ import annotations

import uuid
from datetime import datetime
from numbers import Real
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.schemas.head_agent import HeadAgentRecommendation

MAX_RESULT_SUMMARY_LENGTH = 4000
MAX_RESULT_NOTES_LENGTH = 4000
MAX_BLOCKED_REASON_LENGTH = 500
MAX_TASK_TITLE_LENGTH = 200
MAX_TASK_DESCRIPTION_LENGTH = 4000

ObjectiveTaskStatus = Literal["pending", "in_progress", "blocked", "completed"]
ObjectiveTaskPriority = Literal["low", "medium", "high"]


class ObjectiveTaskStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ObjectiveTaskStatus
    blocked_reason: str | None = Field(default=None, max_length=MAX_BLOCKED_REASON_LENGTH)
    result_summary: str | None = Field(default=None, max_length=MAX_RESULT_SUMMARY_LENGTH)
    result_metrics: dict[str, float] | None = None
    result_notes: str | None = Field(default=None, max_length=MAX_RESULT_NOTES_LENGTH)

    @field_validator("blocked_reason")
    @classmethod
    def blocked_reason_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("result_summary")
    @classmethod
    def result_summary_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("result_metrics")
    @classmethod
    def result_metrics_are_numeric(
        cls,
        value: dict[str, float] | None,
    ) -> dict[str, float] | None:
        if value is None:
            return None
        normalized: dict[str, float] = {}
        for key, metric in value.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("result_metrics keys must be non-empty strings")
            if isinstance(metric, bool) or not isinstance(metric, Real):
                raise ValueError("result_metrics values must be numeric")
            normalized[key.strip()] = float(metric)
        return normalized

    @field_validator("result_notes")
    @classmethod
    def result_notes_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def completion_requires_result_summary(self) -> ObjectiveTaskStatusRequest:
        if self.status == "completed" and self.result_summary is None:
            raise ValueError("result_summary is required when status is completed")
        return self


class ObjectiveTaskCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_summary: str = Field(min_length=1, max_length=MAX_RESULT_SUMMARY_LENGTH)
    result_metrics: dict[str, float] | None = None
    result_notes: str | None = Field(default=None, max_length=MAX_RESULT_NOTES_LENGTH)

    @field_validator("result_summary")
    @classmethod
    def result_summary_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("result_summary is required")
        return stripped

    @field_validator("result_metrics")
    @classmethod
    def result_metrics_are_numeric(
        cls,
        value: dict[str, float] | None,
    ) -> dict[str, float] | None:
        if value is None:
            return None
        normalized: dict[str, float] = {}
        for key, metric in value.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("result_metrics keys must be non-empty strings")
            if isinstance(metric, bool) or not isinstance(metric, Real):
                raise ValueError("result_metrics values must be numeric")
            normalized[key.strip()] = float(metric)
        return normalized

    @field_validator("result_notes")
    @classmethod
    def result_notes_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ObjectiveTaskPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    objective_id: uuid.UUID
    title: str
    description: str | None
    capability: str
    status: str
    priority: str
    requires_approval: bool
    started_at: str | None = None
    blocked_reason: str | None = None
    result_summary: str | None = None
    result_metrics: dict[str, float] | None = None
    result_notes: str | None = None
    completed_by: uuid.UUID | None = None
    completed_at: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_task(cls, task: object) -> ObjectiveTaskPublic:
        return cls(
            id=task.id,  # type: ignore[attr-defined]
            company_id=task.company_id,  # type: ignore[attr-defined]
            objective_id=task.objective_id,  # type: ignore[attr-defined]
            title=task.title,  # type: ignore[attr-defined]
            description=task.description,  # type: ignore[attr-defined]
            capability=task.capability,  # type: ignore[attr-defined]
            status=task.status,  # type: ignore[attr-defined]
            priority=task.priority,  # type: ignore[attr-defined]
            requires_approval=task.requires_approval,  # type: ignore[attr-defined]
            started_at=task.started_at,  # type: ignore[attr-defined]
            blocked_reason=task.blocked_reason,  # type: ignore[attr-defined]
            result_summary=task.result_summary,  # type: ignore[attr-defined]
            result_metrics=task.result_metrics,  # type: ignore[attr-defined]
            result_notes=task.result_notes,  # type: ignore[attr-defined]
            completed_by=task.completed_by,  # type: ignore[attr-defined]
            completed_at=task.completed_at,  # type: ignore[attr-defined]
            created_at=task.created_at,  # type: ignore[attr-defined]
            updated_at=task.updated_at,  # type: ignore[attr-defined]
        )


class ObjectiveTaskListResponse(BaseModel):
    tasks: list[ObjectiveTaskPublic]


class ObjectiveTaskObjectiveSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: str


class ObjectiveTaskResultPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    metrics: dict[str, float] | None = None
    notes: str | None = None
    completed_by: uuid.UUID | None = None
    completed_at: str | None = None


class ObjectiveTaskProvenancePublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_task_id: uuid.UUID | None = None
    agent_run_id: uuid.UUID | None = None
    approval_id: uuid.UUID | None = None
    objective_id: uuid.UUID | None = None


class ObjectiveTaskEvidencePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    title: str
    content: str
    source_type: str
    source_reference: str | None
    observed_at: str | None
    created_at: datetime


class ObjectiveTaskLearningPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    statement: str
    evidence_summary: str | None
    confidence: float | None
    status: str
    evidence_id: uuid.UUID | None
    objective_id: uuid.UUID | None


class ObjectiveTaskApprovalContextPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    description: str
    action_type: str
    requested_at: str
    resolved_at: str | None = None


class ObjectiveTaskUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=MAX_TASK_TITLE_LENGTH)
    description: str | None = Field(default=None, max_length=MAX_TASK_DESCRIPTION_LENGTH)
    priority: ObjectiveTaskPriority | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("Title cannot be blank")
        return stripped

    @field_validator("description")
    @classmethod
    def description_optional(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        return stripped or None


class ObjectiveTaskDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    objective_id: uuid.UUID
    title: str
    description: str | None
    capability: str
    status: str
    priority: str
    requires_approval: bool
    started_at: str | None = None
    blocked_reason: str | None = None
    result_summary: str | None = None
    result_metrics: dict[str, float] | None = None
    result_notes: str | None = None
    completed_by: uuid.UUID | None = None
    completed_at: str | None = None
    created_at: datetime
    updated_at: datetime
    objective: ObjectiveTaskObjectiveSummary | None = None
    result: ObjectiveTaskResultPublic | None = None
    provenance: ObjectiveTaskProvenancePublic | None = None
    evidence: list[ObjectiveTaskEvidencePublic] = Field(default_factory=list)
    learnings: list[ObjectiveTaskLearningPublic] = Field(default_factory=list)
    recommendation: HeadAgentRecommendation | None = None
    recommendation_question: str | None = None
    approval_context: ObjectiveTaskApprovalContextPublic | None = None

    @classmethod
    def from_detail(cls, detail: object) -> ObjectiveTaskDetailResponse:
        task = detail.task  # type: ignore[attr-defined]
        objective = detail.objective  # type: ignore[attr-defined]
        evidence = detail.evidence  # type: ignore[attr-defined]
        learnings = detail.learnings  # type: ignore[attr-defined]
        agent_task = detail.agent_task  # type: ignore[attr-defined]
        approval = detail.approval  # type: ignore[attr-defined]

        recommendation: HeadAgentRecommendation | None = None
        recommendation_question: str | None = None
        if agent_task is not None:
            if isinstance(agent_task.output, dict):
                try:
                    recommendation = HeadAgentRecommendation.model_validate(agent_task.output)
                except ValidationError:
                    recommendation = None
            if isinstance(agent_task.input, dict):
                question = agent_task.input.get("question")
                if isinstance(question, str) and question.strip():
                    recommendation_question = question.strip()

        approval_context: ObjectiveTaskApprovalContextPublic | None = None
        if approval is not None:
            approval_context = ObjectiveTaskApprovalContextPublic(
                status=approval.status,
                description=approval.description,
                action_type=approval.action_type,
                requested_at=approval.requested_at,
                resolved_at=approval.resolved_at,
            )

        result: ObjectiveTaskResultPublic | None = None
        if task.status == "completed" and task.result_summary is not None:
            result = ObjectiveTaskResultPublic(
                summary=task.result_summary,
                metrics=task.result_metrics,
                notes=task.result_notes,
                completed_by=task.completed_by,
                completed_at=task.completed_at,
            )

        provenance = ObjectiveTaskProvenancePublic(
            agent_task_id=agent_task.id if agent_task is not None else None,
            agent_run_id=agent_task.agent_run_id if agent_task is not None else None,
            approval_id=approval.id if approval is not None else None,
            objective_id=task.objective_id,
        )

        return cls(
            id=task.id,
            company_id=task.company_id,
            objective_id=task.objective_id,
            title=task.title,
            description=task.description,
            capability=task.capability,
            status=task.status,
            priority=task.priority,
            requires_approval=task.requires_approval,
            started_at=task.started_at,
            blocked_reason=task.blocked_reason,
            result_summary=task.result_summary,
            result_metrics=task.result_metrics,
            result_notes=task.result_notes,
            completed_by=task.completed_by,
            completed_at=task.completed_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
            objective=(
                ObjectiveTaskObjectiveSummary(
                    id=objective.id,
                    title=objective.title,
                    status=objective.status,
                )
                if objective is not None
                else None
            ),
            result=result,
            provenance=provenance,
            evidence=(
                [
                    ObjectiveTaskEvidencePublic(
                        id=evidence.id,
                        type=evidence.type,
                        title=evidence.title,
                        content=evidence.content,
                        source_type=evidence.source_type,
                        source_reference=evidence.source_reference,
                        observed_at=evidence.observed_at,
                        created_at=evidence.created_at,
                    )
                ]
                if evidence is not None
                else []
            ),
            learnings=[
                ObjectiveTaskLearningPublic(
                    id=learning.id,
                    statement=learning.statement,
                    evidence_summary=learning.evidence_summary,
                    confidence=learning.confidence,
                    status=learning.status,
                    evidence_id=learning.evidence_id,
                    objective_id=learning.objective_id,
                )
                for learning in learnings
            ],
            recommendation=recommendation,
            recommendation_question=recommendation_question,
            approval_context=approval_context,
        )
