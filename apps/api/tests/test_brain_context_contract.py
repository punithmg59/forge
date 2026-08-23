"""Company Context and retrieval contracts. No retrieval execution."""

from __future__ import annotations

import inspect
import uuid

import pytest
from pydantic import ValidationError

from app.models.company_member import CompanyMember
from app.schemas.brain import (
    CompanyContext,
    ContextBelief,
    ContextFact,
)
from app.services.retrieval import (
    RetrievalScope,
    StructuredRetriever,
    VectorRetriever,
)


def test_empty_brain_is_representable() -> None:
    context = CompanyContext()
    assert context.company is None
    assert context.objective is None
    assert context.bottleneck is None
    assert context.constraints == []
    assert context.facts == []
    assert context.beliefs == []
    assert context.decisions == []
    assert context.experiments == []
    assert context.learnings == []
    assert context.memories == []
    assert context.sources == []
    assert context.meta is None


def test_facts_and_beliefs_are_separate_fields() -> None:
    fields = CompanyContext.model_fields
    assert "facts" in fields
    assert "beliefs" in fields
    assert "knowledge" not in fields
    context = CompanyContext(
        facts=[ContextFact(key="mrr", value="12000")],
        beliefs=[ContextBelief(statement="Founders want faster onboarding")],
    )
    assert context.facts[0].value == "12000"
    assert context.beliefs[0].statement == "Founders want faster onboarding"
    assert context.facts[0].model_dump() != context.beliefs[0].model_dump()


def test_merged_knowledge_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CompanyContext.model_validate({"knowledge": [{"text": "merged"}]})


def test_null_and_sparse_sections_are_valid() -> None:
    context = CompanyContext.model_validate(
        {
            "company": None,
            "objective": None,
            "bottleneck": None,
            "constraints": [],
            "facts": None,
            "beliefs": [],
        }
    )
    assert context.facts == []
    assert context.beliefs == []


def test_retrieval_requires_membership_scope_not_raw_company_id() -> None:
    structured = inspect.signature(StructuredRetriever.retrieve)
    vector = inspect.signature(VectorRetriever.retrieve)
    assert list(structured.parameters)[1] == "scope"
    assert list(vector.parameters)[1] == "scope"
    assert "company_id" not in structured.parameters
    assert "company_id" not in vector.parameters


def test_retrieval_scope_comes_from_existing_membership() -> None:
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    membership = CompanyMember(company_id=company_id, user_id=user_id, role="owner")
    scope = RetrievalScope.from_membership(membership)
    assert scope.company_id == company_id
    assert scope.user_id == user_id
    assert scope.role == "owner"


def test_retriever_contracts_are_not_implemented() -> None:
    with pytest.raises(TypeError):
        StructuredRetriever()  # type: ignore[abstract]
    with pytest.raises(TypeError):
        VectorRetriever()  # type: ignore[abstract]
