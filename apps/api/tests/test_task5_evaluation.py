"""Task 5 final evaluation: pipeline correctness, security, and grounding."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.main import app
from app.models.company import Company
from app.models.company_belief import CompanyBelief
from app.models.company_fact import CompanyFact
from app.models.company_member import CompanyMember
from app.models.memory import EMBEDDING_DIMENSION, Memory
from app.models.objective import Objective
from app.models.user import User
from app.schemas.brain import (
    BrainQueryResponse,
    CompanyContext,
    ContextBelief,
    ContextCompany,
    ContextDecision,
    ContextEvidence,
    ContextExperiment,
    ContextFact,
    ContextLearning,
    ContextObjective,
    ContextSource,
    MAX_BRAIN_QUERY_LENGTH,
    RetrievalMeta,
)
from app.services.brain_context import build_company_brain_context
from app.services.brain_query import BrainQueryError, answer_brain_query
from app.services.brain_query_prompt import (
    BRAIN_QUERY_SYSTEM_PROMPT,
    build_brain_query_messages,
)
from app.services.llm import (
    CompletionRequest,
    CompletionResult,
    LLMProvider,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from app.services.llm.errors import ProviderUnavailableError
from app.services.retrieval import QueryIntent, StructuredSection, classify_query
from app.services.retrieval.assemble import assemble_context
from app.services.retrieval.classifier import QueryClassification
from app.services.retrieval.vector import VectorHit


def _client() -> TestClient:
    return TestClient(app)


def _signup(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Evaluator",
            "email": f"task5-{uuid.uuid4()}@example.com",
            "password": "valid-pass-1",
        },
    )
    assert response.status_code == 201


def _create_company(client: TestClient, name: str) -> dict:
    response = client.post(
        "/api/v1/companies",
        json={
            "name": name,
            "description": "Task 5 evaluation",
            "target_customer": "founders",
            "stage": "mvp",
        },
    )
    assert response.status_code == 201
    return response.json()


def _context_url(company_id: str) -> str:
    return f"/api/v1/companies/{company_id}/brain/context"


def _query_url(company_id: str) -> str:
    return f"/api/v1/companies/{company_id}/brain/query"


def _vector(*hot: tuple[int, float]) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSION
    for index, weight in hot:
        values[index] = weight
    return values


class _GroundedStubProvider(LLMProvider):
    """Returns answers derived from prompt context without external API calls."""

    name = "grounded-stub"

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        user = request.messages[-1].content
        if "COMPANY_BRAIN_DATA_START" not in user:
            return CompletionResult(text="unavailable", model="grounded-stub")
        if '"title": "Ship v1"' in user and "current objective" in user.lower():
            return CompletionResult(
                text="Your current objective is Ship v1.",
                model="grounded-stub",
            )
        if "biggest customer problem" in user.lower() and '"facts": []' in user:
            return CompletionResult(
                text=(
                    "Forge does not currently have enough Company Brain information "
                    "to answer that question."
                ),
                model="grounded-stub",
            )
        if "developers are our best customers" in user.lower():
            return CompletionResult(
                text=(
                    "Your current belief is that developers may be the best initial "
                    "customers. This is a belief, not a confirmed fact."
                ),
                model="grounded-stub",
            )
        if "previous experiment" in user.lower() and "Onboarding A/B improved activation" in user:
            return CompletionResult(
                text="Your previous experiment showed onboarding A/B improved activation.",
                model="grounded-stub",
            )
        return CompletionResult(
            text="I can only answer from the supplied Company Brain data.",
            model="grounded-stub",
        )

    async def embed(self, request: object) -> object:
        raise AssertionError("evaluation stub must not embed")


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("What is our current objective?", QueryIntent.OBJECTIVE),
        ("What are our current constraints?", QueryIntent.CONSTRAINTS),
        ("What do we know about our customers?", QueryIntent.FACTS),
        ("What do we believe about our customers?", QueryIntent.BELIEFS),
        ("What decisions have we made?", QueryIntent.DECISIONS),
        ("What experiments are running?", QueryIntent.EXPERIMENTS),
        ("What have we learned?", QueryIntent.LEARNINGS),
    ],
)
def test_structured_questions_classify_correctly(question: str, intent: QueryIntent) -> None:
    result = classify_query(question)
    assert result.intent is intent
    assert result.vector_needed is False


def test_broad_question_enables_vector_retrieval() -> None:
    result = classify_query("Give me a complete picture of the company.")
    assert result.intent is QueryIntent.BROAD
    assert result.vector_needed is True


def test_historical_question_enables_vector_retrieval() -> None:
    result = classify_query(
        "What did we learn from previous customer acquisition experiments?"
    )
    assert result.intent is QueryIntent.HISTORICAL
    assert result.vector_needed is True


@pytest.mark.asyncio
async def test_broad_classification_triggers_vector_retrieval_in_context_builder() -> None:
    membership = MagicMock()
    membership.company_id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.role = "founder"
    structured = AsyncMock()
    structured.retrieve = AsyncMock(return_value=CompanyContext())
    vector = AsyncMock()
    vector.retrieve = AsyncMock(return_value=[])

    await build_company_brain_context(
        MagicMock(),
        membership=membership,
        query="Give me a complete picture of the company.",
        structured_retriever_factory=lambda _db: structured,
        vector_retriever_factory=lambda _db: vector,
    )

    vector.retrieve.assert_awaited_once()


def test_sparse_brain_prompt_discourages_invention() -> None:
    context = CompanyContext(
        meta=RetrievalMeta(
            sections_empty=["facts", "beliefs", "evidence", "memories"],
        )
    )
    messages = build_brain_query_messages(
        question="What is our biggest customer problem?",
        context=context,
    )
    assert "Never invent company facts" in messages[0].content
    assert '"sections_empty"' in messages[1].content


def test_empty_brain_assembles_valid_context() -> None:
    context = assemble_context(CompanyContext(), [], None)
    assert context.facts == []
    assert context.beliefs == []
    assert context.evidence == []
    assert context.memories == []


@pytest.mark.asyncio
async def test_tenant_isolation_on_context_endpoint(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user_a = _client()
    user_b = _client()
    _signup(user_a)
    _signup(user_b)
    company_a = _create_company(user_a, "Eval A")
    company_b = _create_company(user_b, "Eval B")

    async with async_session_factory() as session:
        company_b_row = await session.get(Company, uuid.UUID(company_b["id"]))
        assert company_b_row is not None
        session.add(
            CompanyFact(
                company_id=company_b_row.id,
                key="secret-b",
                value="hidden",
                value_type="string",
                source_type="manual",
                status="active",
            )
        )
        await session.commit()

    response = user_a.post(
        _context_url(company_b["id"]),
        json={"query": "What do we know about our customers?"},
    )
    assert response.status_code == 403


@patch("app.api.routes.brain.answer_brain_query", new_callable=AsyncMock)
def test_tenant_isolation_on_query_endpoint(mock_answer: AsyncMock) -> None:
    owner = _client()
    outsider = _client()
    _signup(owner)
    _signup(outsider)
    company = _create_company(owner, "Query Tenant Co")

    response = outsider.post(
        _query_url(company["id"]),
        json={"query": "What is our objective?"},
    )
    assert response.status_code == 403
    mock_answer.assert_not_awaited()


def test_beliefs_are_not_presented_as_facts_in_grounding_prompt() -> None:
    context = CompanyContext(
        beliefs=[ContextBelief(statement="Developers may be the best initial customer")],
        facts=[ContextFact(key="users", value="10")],
    )
    user_content = build_brain_query_messages(
        question="Our belief is that developers are our best customers. What do we know?",
        context=context,
    )[1].content
    assert '"beliefs"' in user_content
    assert '"facts"' in user_content
    assert "Never turn beliefs into confirmed facts" in BRAIN_QUERY_SYSTEM_PROMPT


def test_provenance_sources_match_assembled_entities() -> None:
    fact_id = uuid.uuid4()
    belief_id = uuid.uuid4()
    structured = CompanyContext(
        facts=[ContextFact(id=fact_id, key="mrr", value="100")],
        beliefs=[ContextBelief(id=belief_id, statement="We believe in CLI")],
    )
    assembled = assemble_context(structured, [], classify_query("What do we know?"))
    entity_ids = {source.entity_id for source in assembled.sources}
    assert str(fact_id) in entity_ids
    assert str(belief_id) in entity_ids


def test_brain_query_uses_provider_abstraction_not_newtron() -> None:
    service_dir = Path(__file__).resolve().parents[1] / "app" / "services"
    brain_sources = (service_dir / "brain_query.py").read_text(encoding="utf-8")
    assert "get_llm_provider" in brain_sources
    assert "NewtronProvider" not in brain_sources


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (ProviderTimeoutError("slow"), 504),
        (ProviderAuthError("bad key"), 502),
        (ProviderRateLimitError("limit"), 429),
        (ProviderUnavailableError("down"), 502),
    ],
)
@pytest.mark.asyncio
async def test_provider_failures_map_to_brain_query_errors(
    error: Exception,
    status_code: int,
) -> None:
    membership = MagicMock()
    membership.company_id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.role = "founder"

    class _FailingProvider(LLMProvider):
        name = "failing"

        async def complete(self, request: CompletionRequest) -> CompletionResult:
            raise error

        async def embed(self, request: object) -> object:
            raise AssertionError("no embed")

    with pytest.raises(BrainQueryError) as exc:
        await answer_brain_query(
            MagicMock(),
            membership=membership,
            query="What is our objective?",
            context_builder=AsyncMock(return_value=CompanyContext()),
            provider_factory=_FailingProvider,
        )
    assert exc.value.status_code == status_code


def test_api_rejects_empty_query() -> None:
    client = _client()
    _signup(client)
    company = _create_company(client, "Validation Co")
    assert client.post(_context_url(company["id"]), json={"query": "   "}).status_code == 422
    assert client.post(_query_url(company["id"]), json={"query": "   "}).status_code == 422


def test_api_rejects_oversized_query() -> None:
    client = _client()
    _signup(client)
    company = _create_company(client, "Validation Co")
    oversized = "x" * (MAX_BRAIN_QUERY_LENGTH + 1)
    assert client.post(_context_url(company["id"]), json={"query": oversized}).status_code == 422
    assert client.post(_query_url(company["id"]), json={"query": oversized}).status_code == 422


def test_api_requires_authentication() -> None:
    client = _client()
    company_id = str(uuid.uuid4())
    assert client.post(_context_url(company_id), json={"query": "hello"}).status_code == 401
    assert client.post(_query_url(company_id), json={"query": "hello"}).status_code == 401


@pytest.mark.parametrize(
    ("question", "context", "expected_fragment"),
    [
        (
            "What is our current objective?",
            CompanyContext(objective=ContextObjective(title="Ship v1", status="active")),
            "Ship v1",
        ),
        (
            "What is our biggest customer problem?",
            CompanyContext(meta=RetrievalMeta(sections_empty=["facts", "beliefs", "evidence"])),
            "not currently have enough Company Brain information",
        ),
        (
            "Our belief is that developers are our best customers. What do we know about this?",
            CompanyContext(
                beliefs=[ContextBelief(statement="Developers may be the best initial customer")]
            ),
            "belief",
        ),
        (
            "What happened in our previous experiment?",
            CompanyContext(
                memories=[],
                learnings=[
                    ContextLearning(statement="Onboarding A/B improved activation", status="active")
                ],
            ),
            "Onboarding A/B improved activation",
        ),
    ],
)
@pytest.mark.asyncio
async def test_grounding_cases_use_supplied_context_only(
    question: str,
    context: CompanyContext,
    expected_fragment: str,
) -> None:
    membership = MagicMock()
    membership.company_id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.role = "founder"

    result = await answer_brain_query(
        MagicMock(),
        membership=membership,
        query=question,
        context_builder=AsyncMock(return_value=context),
        provider_factory=_GroundedStubProvider,
    )

    assert expected_fragment.lower() in result.answer.lower()


@pytest.mark.asyncio
async def test_end_to_end_pipeline_with_mock_llm_only(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Company -> Brain data -> /brain/query -> retrieval -> mock LLM -> grounded response."""
    client = _client()
    _signup(client)
    company = _create_company(client, "E2E Co")
    company_id = uuid.UUID(company["id"])

    async with async_session_factory() as session:
        objective = Objective(
            company_id=company_id,
            title="Ship v1",
            status="active",
            priority="high",
        )
        session.add(objective)
        session.add(
            Memory(
                company_id=company_id,
                memory_type="semantic",
                content="Founders prefer async onboarding",
                embedding=_vector((0, 1.0)),
                source_type="founder_input",
            )
        )
        await session.commit()

    with patch(
        "app.services.brain_query.get_llm_provider",
        return_value=_GroundedStubProvider(),
    ):
        response = client.post(
            _query_url(company["id"]),
            json={"query": "What is our current objective?"},
        )

    assert response.status_code == 200
    body = response.json()
    assert "Ship v1" in body["answer"]
    assert body["meta"]["query"] == "What is our current objective?"
    assert "api_key" not in response.text.lower()


def test_no_hard_coded_secrets_in_task5_modules() -> None:
    app_dir = Path(__file__).resolve().parents[1] / "app"
    patterns = ("nvapi-", "sk-proj-", "sk-ant-")
    checked = [
        app_dir / "services" / "brain_context.py",
        app_dir / "services" / "brain_query.py",
        app_dir / "services" / "brain_query_prompt.py",
        app_dir / "services" / "retrieval" / "sql.py",
        app_dir / "services" / "retrieval" / "sql_vector.py",
        app_dir / "services" / "retrieval" / "assemble.py",
        app_dir / "services" / "retrieval" / "classifier.py",
        app_dir / "api" / "routes" / "brain.py",
    ]
    blob = "\n".join(path.read_text(encoding="utf-8") for path in checked)
    for pattern in patterns:
        assert pattern not in blob


@pytest.mark.asyncio
async def test_context_builder_passes_membership_scope_to_retriever() -> None:
    membership = MagicMock()
    membership.company_id = uuid.uuid4()
    membership.user_id = uuid.uuid4()
    membership.role = "founder"
    structured = MagicMock()
    structured.retrieve = AsyncMock(return_value=CompanyContext())

    await build_company_brain_context(
        MagicMock(),
        membership=membership,
        query="What is our objective?",
        structured_retriever_factory=lambda _db: structured,
        vector_retriever_factory=lambda _db: MagicMock(),
    )

    scope = structured.retrieve.await_args.args[0]
    assert scope.company_id == membership.company_id
    assert scope.user_id == membership.user_id
