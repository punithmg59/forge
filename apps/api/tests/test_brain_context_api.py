"""Focused API tests for Task 5.6 Brain context endpoint."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.brain import (
    CompanyContext,
    ContextCompany,
    ContextFact,
    RetrievalMeta,
)
from app.services.brain_context import BrainContextError, build_company_brain_context
from app.services.retrieval.classifier import QueryClassification, QueryIntent, StructuredSection
from app.services.retrieval.sql import RetrievalAccessError
from app.services.retrieval.sql_vector import VectorRetrievalError


def _client() -> TestClient:
    return TestClient(app)


def _signup(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Founder",
            "email": f"brain-{uuid.uuid4()}@example.com",
            "password": "valid-pass-1",
        },
    )
    assert response.status_code == 201


def _create_company(client: TestClient, name: str = "Brain Co") -> dict:
    response = client.post(
        "/api/v1/companies",
        json={
            "name": name,
            "description": "Brain API test",
            "target_customer": "founders",
            "stage": "mvp",
        },
    )
    assert response.status_code == 201
    return response.json()


def _context_url(company_id: str) -> str:
    return f"/api/v1/companies/{company_id}/brain/context"


def _sample_context(*, query: str = "What is our objective?") -> CompanyContext:
    return CompanyContext(
        company=ContextCompany(name="Brain Co"),
        facts=[ContextFact(key="users", value="10")],
        meta=RetrievalMeta(query=query, classification="OBJECTIVE"),
    )


def _classification(*, vector_needed: bool = False) -> QueryClassification:
    return QueryClassification(
        intent=QueryIntent.BROAD if vector_needed else QueryIntent.OBJECTIVE,
        sections=(StructuredSection.OBJECTIVE,),
        vector_needed=vector_needed,
    )


@patch("app.api.routes.brain.build_company_brain_context", new_callable=AsyncMock)
def test_valid_member_can_query_brain_context(mock_build: AsyncMock) -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    mock_build.return_value = _sample_context()

    response = client.post(
        _context_url(company["id"]),
        json={"query": "What is our current objective?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["company"]["name"] == "Brain Co"
    assert body["facts"][0]["key"] == "users"
    mock_build.assert_awaited_once()


def test_unauthenticated_request_returns_401() -> None:
    client = _client()
    response = client.post(
        _context_url(str(uuid.uuid4())),
        json={"query": "What is our objective?"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_non_member_returns_403() -> None:
    owner = _client()
    outsider = _client()
    _signup(owner)
    _signup(outsider)
    company = _create_company(owner)

    response = outsider.post(
        _context_url(company["id"]),
        json={"query": "What is our objective?"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not allowed to access this company"


@patch("app.api.routes.brain.build_company_brain_context", new_callable=AsyncMock)
def test_company_a_cannot_retrieve_company_b_data(mock_build: AsyncMock) -> None:
    user_a = _client()
    user_b = _client()
    _signup(user_a)
    _signup(user_b)
    company_a = _create_company(user_a, "Company A")
    company_b = _create_company(user_b, "Company B")
    mock_build.return_value = CompanyContext(company=ContextCompany(name="Company A"))

    response = user_a.post(
        _context_url(company_b["id"]),
        json={"query": "What is our objective?"},
    )

    assert response.status_code == 403
    mock_build.assert_not_awaited()


def test_query_validation_rejects_empty_query() -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)

    response = client.post(_context_url(company["id"]), json={"query": "   "})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_structured_retrieval_is_called() -> None:
    membership = MagicMock()
    membership.company_id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.role = "founder"
    db = MagicMock()
    structured = AsyncMock()
    structured.retrieve = AsyncMock(return_value=CompanyContext())
    vector = MagicMock()
    vector.retrieve = AsyncMock(return_value=[])

    with patch(
        "app.services.brain_context.classify_query",
        return_value=_classification(vector_needed=False),
    ):
        await build_company_brain_context(
            db,
            membership=membership,
            query="What is our objective?",
            structured_retriever_factory=lambda _db: structured,
            vector_retriever_factory=lambda _db: vector,
        )

    structured.retrieve.assert_awaited_once()
    vector.retrieve.assert_not_awaited()


@pytest.mark.asyncio
async def test_vector_retrieval_called_when_classifier_requires_it() -> None:
    membership = MagicMock()
    membership.company_id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.role = "founder"
    db = MagicMock()
    structured = AsyncMock()
    structured.retrieve = AsyncMock(return_value=CompanyContext())
    vector = AsyncMock()
    vector.retrieve = AsyncMock(return_value=[])

    with patch(
        "app.services.brain_context.classify_query",
        return_value=_classification(vector_needed=True),
    ):
        await build_company_brain_context(
            db,
            membership=membership,
            query="Give me a complete picture of the company.",
            structured_retriever_factory=lambda _db: structured,
            vector_retriever_factory=lambda _db: vector,
        )

    structured.retrieve.assert_awaited_once()
    vector.retrieve.assert_awaited_once()


@pytest.mark.asyncio
async def test_vector_retrieval_not_called_when_classifier_does_not_require_it() -> None:
    membership = MagicMock()
    membership.company_id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.role = "founder"
    db = MagicMock()
    structured = AsyncMock()
    structured.retrieve = AsyncMock(return_value=CompanyContext())
    vector = AsyncMock()
    vector.retrieve = AsyncMock(return_value=[])

    with patch(
        "app.services.brain_context.classify_query",
        return_value=_classification(vector_needed=False),
    ):
        await build_company_brain_context(
            db,
            membership=membership,
            query="What is our objective?",
            structured_retriever_factory=lambda _db: structured,
            vector_retriever_factory=lambda _db: vector,
        )

    vector.retrieve.assert_not_awaited()


@patch("app.api.routes.brain.build_company_brain_context", new_callable=AsyncMock)
def test_response_matches_company_context_schema(mock_build: AsyncMock) -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    mock_build.return_value = CompanyContext(
        company=ContextCompany(name="Brain Co"),
        objective=None,
        bottleneck=None,
        constraints=[],
        facts=[],
        beliefs=[],
        evidence=[],
        decisions=[],
        experiments=[],
        learnings=[],
        memories=[],
        sources=[],
        meta=RetrievalMeta(query="test", classification="BROAD", sections_empty=["facts"]),
    )

    response = client.post(
        _context_url(company["id"]),
        json={"query": "Give me a complete picture of the company."},
    )

    assert response.status_code == 200
    body = response.json()
    for field in (
        "company",
        "objective",
        "constraints",
        "facts",
        "beliefs",
        "evidence",
        "decisions",
        "experiments",
        "learnings",
        "memories",
        "sources",
        "meta",
    ):
        assert field in body
    assert body["meta"]["classification"] == "BROAD"
    assert "facts" in body["meta"]["sections_empty"]


@patch("app.api.routes.brain.build_company_brain_context", new_callable=AsyncMock)
def test_empty_sparse_brain_returns_valid_context(mock_build: AsyncMock) -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    mock_build.return_value = CompanyContext(
        company=ContextCompany(name="Sparse Co"),
        meta=RetrievalMeta(
            query="What should we do?",
            classification="BROAD",
            sections_empty=["facts", "beliefs", "memories"],
        ),
    )

    response = client.post(
        _context_url(company["id"]),
        json={"query": "What should we do?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["company"]["name"] == "Sparse Co"
    assert body["facts"] == []
    assert body["beliefs"] == []
    assert body["memories"] == []


@patch("app.api.routes.brain.build_company_brain_context", new_callable=AsyncMock)
def test_retrieval_failure_returns_api_error(mock_build: AsyncMock) -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    mock_build.side_effect = BrainContextError("Brain context retrieval failed", 502)

    response = client.post(
        _context_url(company["id"]),
        json={"query": "What is our objective?"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Brain context retrieval failed"
    assert "traceback" not in response.text.lower()
    assert "api_key" not in response.text.lower()


@pytest.mark.asyncio
async def test_vector_provider_failure_maps_to_api_error() -> None:
    membership = MagicMock()
    membership.company_id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.role = "founder"
    db = MagicMock()
    structured = AsyncMock()
    structured.retrieve = AsyncMock(return_value=CompanyContext())
    vector = AsyncMock()
    vector.retrieve = AsyncMock(side_effect=VectorRetrievalError("Embedding provider failed"))

    with patch(
        "app.services.brain_context.classify_query",
        return_value=_classification(vector_needed=True),
    ):
        with pytest.raises(BrainContextError) as exc:
            await build_company_brain_context(
                db,
                membership=membership,
                query="Give me a complete picture of the company.",
                structured_retriever_factory=lambda _db: structured,
                vector_retriever_factory=lambda _db: vector,
            )

    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_no_llm_answer_generation_occurs() -> None:
    membership = MagicMock()
    membership.company_id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.role = "founder"
    db = MagicMock()
    structured = AsyncMock()
    structured.retrieve = AsyncMock(return_value=CompanyContext())
    vector = AsyncMock()
    vector.retrieve = AsyncMock(return_value=[])
    provider = AsyncMock()
    provider.complete = AsyncMock()
    provider.embed = AsyncMock()

    with patch(
        "app.services.brain_context.classify_query",
        return_value=_classification(vector_needed=True),
    ):
        with patch("app.services.llm.get_llm_provider", return_value=provider):
            await build_company_brain_context(
                db,
                membership=membership,
                query="Give me a complete picture of the company.",
                structured_retriever_factory=lambda _db: structured,
                vector_retriever_factory=lambda _db: vector,
            )

    provider.complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_retrieval_access_error_maps_to_403() -> None:
    membership = MagicMock()
    membership.company_id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.role = "founder"
    db = MagicMock()
    structured = AsyncMock()
    structured.retrieve = AsyncMock(side_effect=RetrievalAccessError("denied"))

    with patch(
        "app.services.brain_context.classify_query",
        return_value=_classification(vector_needed=False),
    ):
        with pytest.raises(BrainContextError) as exc:
            await build_company_brain_context(
                db,
                membership=membership,
                query="What is our objective?",
                structured_retriever_factory=lambda _db: structured,
                vector_retriever_factory=lambda _db: MagicMock(),
            )

    assert exc.value.status_code == 403
