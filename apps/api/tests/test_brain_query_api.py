"""Focused API tests for Task 5.7 grounded Brain query."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.brain import (
    BrainQueryResponse,
    CompanyContext,
    ContextBelief,
    ContextCompany,
    ContextFact,
    ContextSource,
    RetrievalMeta,
)
from app.services.brain_context import BrainContextError
from app.services.brain_query import BrainQueryError, answer_brain_query
from app.services.brain_query_prompt import build_brain_query_messages
from app.services.llm import (
    CompletionRequest,
    CompletionResult,
    LLMProvider,
    ProviderTimeoutError,
)
from app.services.llm.errors import ProviderUnavailableError


def _client() -> TestClient:
    return TestClient(app)


def _signup(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Founder",
            "email": f"brain-query-{uuid.uuid4()}@example.com",
            "password": "valid-pass-1",
        },
    )
    assert response.status_code == 201


def _create_company(client: TestClient, name: str = "Query Co") -> dict:
    response = client.post(
        "/api/v1/companies",
        json={
            "name": name,
            "description": "Brain query test",
            "target_customer": "founders",
            "stage": "mvp",
        },
    )
    assert response.status_code == 201
    return response.json()


def _query_url(company_id: str) -> str:
    return f"/api/v1/companies/{company_id}/brain/query"


def _context(*, sparse: bool = False) -> CompanyContext:
    if sparse:
        return CompanyContext(
            company=ContextCompany(name="Sparse Co"),
            meta=RetrievalMeta(
                query="What is our biggest customer problem?",
                classification="BROAD",
                sections_empty=["facts", "beliefs", "evidence", "memories"],
            ),
        )
    return CompanyContext(
        company=ContextCompany(name="Query Co"),
        facts=[ContextFact(key="users", value="10")],
        beliefs=[ContextBelief(statement="Technical founders may be the best initial customer")],
        sources=[
            ContextSource(entity_type="fact", entity_id="fact-1", source_type="manual"),
            ContextSource(entity_type="belief", entity_id="belief-1", source_type="founder_input"),
        ],
        meta=RetrievalMeta(query="What is blocking us?", classification="COMPANY_STATE"),
    )


class _StubProvider(LLMProvider):
    name = "stub"

    def __init__(self, *, answer: str = "Grounded answer", error: Exception | None = None) -> None:
        self.answer = answer
        self.error = error
        self.requests: list[CompletionRequest] = []

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return CompletionResult(text=self.answer, model="stub-model", finish_reason="stop")

    async def embed(self, request: object) -> object:
        raise AssertionError("Brain query must not call embed()")


@patch("app.api.routes.brain.answer_brain_query", new_callable=AsyncMock)
def test_valid_company_member_can_query_brain(mock_answer: AsyncMock) -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    mock_answer.return_value = BrainQueryResponse.from_context(
        answer="Your current bottleneck is bandwidth.",
        context=_context(),
        model="stub-model",
        question="What is blocking us?",
    )

    response = client.post(
        _query_url(company["id"]),
        json={"query": "What is blocking us?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Your current bottleneck is bandwidth."
    assert body["meta"]["source_count"] == 2
    mock_answer.assert_awaited_once()


def test_unauthenticated_request_returns_401() -> None:
    client = _client()
    response = client.post(
        _query_url(str(uuid.uuid4())),
        json={"query": "What is blocking us?"},
    )
    assert response.status_code == 401


def test_non_member_returns_403() -> None:
    owner = _client()
    outsider = _client()
    _signup(owner)
    _signup(outsider)
    company = _create_company(owner)

    response = outsider.post(
        _query_url(company["id"]),
        json={"query": "What is blocking us?"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_company_context_is_built_before_llm_call() -> None:
    membership = MagicMock()
    membership.company_id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.role = "founder"
    db = MagicMock()
    context_builder = AsyncMock(return_value=_context())
    provider = _StubProvider()

    await answer_brain_query(
        db,
        membership=membership,
        query="What is blocking us?",
        context_builder=context_builder,
        provider_factory=lambda: provider,
    )

    context_builder.assert_awaited_once()
    assert provider.requests


@pytest.mark.asyncio
async def test_llm_provider_abstraction_is_used() -> None:
    membership = MagicMock()
    membership.company_id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.role = "founder"
    provider = _StubProvider(answer="ok")

    await answer_brain_query(
        MagicMock(),
        membership=membership,
        query="What is blocking us?",
        context_builder=AsyncMock(return_value=_context()),
        provider_factory=lambda: provider,
    )

    assert provider.requests[0].temperature == 0
    assert provider.requests[0].messages[0].role == "system"


def test_newtron_not_imported_by_brain_query_service() -> None:
    service_dir = Path(__file__).resolve().parents[1] / "app" / "services"
    sources = "\n".join(
        (service_dir / name).read_text(encoding="utf-8")
        for name in ("brain_query.py", "brain_query_prompt.py")
    )
    assert "NewtronProvider" not in sources
    assert "newtron.py" not in sources
    assert "from app.services.llm.newtron" not in sources


def test_question_and_context_reach_prompt() -> None:
    question = "What is blocking us?"
    context = _context()
    messages = build_brain_query_messages(question=question, context=context)

    user_content = messages[1].content
    assert "FOUNDER_QUESTION_START" in user_content
    assert question in user_content
    assert "COMPANY_BRAIN_DATA_START" in user_content
    assert '"name": "Query Co"' in user_content
    assert '"key": "users"' in user_content


def test_facts_and_beliefs_remain_distinguishable_in_prompt() -> None:
    messages = build_brain_query_messages(
        question="What do we know?",
        context=_context(),
    )
    user_content = messages[1].content
    assert '"facts"' in user_content
    assert '"beliefs"' in user_content
    assert '"users"' in user_content
    assert "Technical founders may be the best initial customer" in user_content
    assert '"knowledge"' not in user_content


def test_sparse_brain_prompt_includes_empty_sections_metadata() -> None:
    messages = build_brain_query_messages(
        question="What is our biggest customer problem?",
        context=_context(sparse=True),
    )
    user_content = messages[1].content
    assert '"sections_empty"' in user_content
    assert '"facts"' in user_content
    assert "Never invent company facts" in messages[0].content


@pytest.mark.asyncio
async def test_provider_timeout_is_handled() -> None:
    membership = MagicMock()
    membership.company_id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.role = "founder"
    provider = _StubProvider(error=ProviderTimeoutError("slow"))

    with pytest.raises(BrainQueryError) as exc:
        await answer_brain_query(
            MagicMock(),
            membership=membership,
            query="What is blocking us?",
            context_builder=AsyncMock(return_value=_context()),
            provider_factory=lambda: provider,
        )

    assert exc.value.status_code == 504


@pytest.mark.asyncio
async def test_provider_failure_is_handled() -> None:
    membership = MagicMock()
    membership.company_id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.role = "founder"
    provider = _StubProvider(error=ProviderUnavailableError("down"))

    with pytest.raises(BrainQueryError) as exc:
        await answer_brain_query(
            MagicMock(),
            membership=membership,
            query="What is blocking us?",
            context_builder=AsyncMock(return_value=_context()),
            provider_factory=lambda: provider,
        )

    assert exc.value.status_code == 502


@patch("app.api.routes.brain.answer_brain_query", new_callable=AsyncMock)
def test_sources_are_returned_correctly(mock_answer: AsyncMock) -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    mock_answer.return_value = BrainQueryResponse.from_context(
        answer="Based on your Brain.",
        context=_context(),
        model="stub-model",
        question="What is blocking us?",
    )

    response = client.post(
        _query_url(company["id"]),
        json={"query": "What is blocking us?"},
    )

    body = response.json()
    assert len(body["sources"]) == 2
    assert body["sources"][0]["entity_type"] == "fact"
    assert body["meta"]["source_count"] == 2


@pytest.mark.asyncio
async def test_future_provider_can_be_substituted() -> None:
    class FutureProvider(LLMProvider):
        name = "future"

        async def complete(self, request: CompletionRequest) -> CompletionResult:
            return CompletionResult(text="future answer", model="future-model")

        async def embed(self, request: object) -> object:
            raise AssertionError("no embed")

    membership = MagicMock()
    membership.company_id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.role = "founder"

    result = await answer_brain_query(
        MagicMock(),
        membership=membership,
        query="What is blocking us?",
        context_builder=AsyncMock(return_value=_context()),
        provider_factory=FutureProvider,
    )

    assert result.answer == "future answer"
    assert result.meta.model == "future-model"


@patch("app.api.routes.brain.answer_brain_query", new_callable=AsyncMock)
def test_context_retrieval_failure_returns_api_error(mock_answer: AsyncMock) -> None:
    client = _client()
    _signup(client)
    company = _create_company(client)
    mock_answer.side_effect = BrainContextError("Brain context retrieval failed", 502)

    response = client.post(
        _query_url(company["id"]),
        json={"query": "What is blocking us?"},
    )

    assert response.status_code == 502
    assert "api_key" not in response.text.lower()


@pytest.mark.asyncio
async def test_no_real_external_llm_call_in_service_path() -> None:
    membership = MagicMock()
    membership.company_id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.role = "founder"
    provider = _StubProvider()

    with patch("app.services.llm.get_llm_provider") as factory:
        await answer_brain_query(
            MagicMock(),
            membership=membership,
            query="What is blocking us?",
            context_builder=AsyncMock(return_value=_context()),
            provider_factory=lambda: provider,
        )
        factory.assert_not_called()
