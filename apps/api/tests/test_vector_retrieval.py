"""Focused tests for Task 5.4 vector memory retrieval. Embeddings are mocked."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.company import Company
from app.models.company_member import CompanyMember
from app.models.memory import EMBEDDING_DIMENSION, Memory
from app.models.user import User
from app.services.llm import (
    CompletionRequest,
    CompletionResult,
    EmbeddingRequest,
    EmbeddingResult,
    LLMProvider,
    ProviderUnavailableError,
)
from app.services.retrieval import (
    RetrievalAccessError,
    RetrievalScope,
    SqlVectorRetriever,
    VectorHit,
    VectorRetrievalError,
)


def _vector(*hot: tuple[int, float]) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSION
    for index, weight in hot:
        values[index] = weight
    return values


class _FakeEmbedProvider(LLMProvider):
    name = "fake-embed"

    def __init__(
        self,
        embedding: list[float] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.embedding = embedding if embedding is not None else _vector((0, 1.0))
        self.error = error
        self.requests: list[EmbeddingRequest] = []

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        raise AssertionError("Vector retrieval must not call complete()")

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return EmbeddingResult(
            embedding=self.embedding,
            model="configured-embed-model",
            dimensions=len(self.embedding),
        )


async def _user(session: AsyncSession) -> User:
    user = User(email=f"vector-{uuid.uuid4()}@example.com", name="Vector User")
    session.add(user)
    await session.flush()
    return user


async def _company(session: AsyncSession, *, name: str, user: User) -> Company:
    company = Company(
        name=name,
        slug=f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}",
        stage="mvp",
    )
    session.add(company)
    await session.flush()
    session.add(CompanyMember(company_id=company.id, user_id=user.id, role="founder"))
    await session.flush()
    return company


def _scope(company: Company, user: User) -> RetrievalScope:
    return RetrievalScope(company_id=company.id, user_id=user.id, role="founder")


def _memory(
    company: Company,
    *,
    content: str,
    embedding: list[float] | None,
    source_reference: str = "notes",
) -> Memory:
    return Memory(
        company_id=company.id,
        memory_type="semantic",
        content=content,
        embedding=embedding,
        source_type="founder_input",
        source_reference=source_reference,
    )


@pytest.mark.asyncio
async def test_relevant_memory_can_be_retrieved(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    query = _vector((0, 1.0))
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="Vector Alpha", user=user)
        relevant = _memory(
            company,
            content="Technical founders prefer CLI tools",
            embedding=_vector((0, 1.0)),
            source_reference="interview-1",
        )
        session.add(relevant)
        session.add(
            _memory(
                company,
                content="Unrelated office snack preferences",
                embedding=_vector((1, 1.0)),
            )
        )
        await session.commit()
        hits = await SqlVectorRetriever(session, _FakeEmbedProvider(query)).retrieve(
            _scope(company, user),
            query_text="CLI tools for founders",
        )

    assert hits
    assert isinstance(hits[0], VectorHit)
    assert hits[0].content == "Technical founders prefer CLI tools"
    assert hits[0].memory_id == str(relevant.id)
    assert hits[0].source_type == "founder_input"
    assert hits[0].source_reference == "interview-1"
    assert hits[0].memory_type == "semantic"
    assert hits[0].created_at is not None
    assert "embedding" not in hits[0].model_dump()


@pytest.mark.asyncio
async def test_results_are_limited_to_requested_company(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    shared = _vector((0, 1.0))
    async with async_session_factory() as session:
        user_a = await _user(session)
        user_b = await _user(session)
        company_a = await _company(session, name="Tenant Vec A", user=user_a)
        company_b = await _company(session, name="Tenant Vec B", user=user_b)
        session.add(_memory(company_a, content="A memory", embedding=shared))
        session.add(_memory(company_b, content="B secret memory", embedding=shared))
        await session.commit()
        hits = await SqlVectorRetriever(session).retrieve(
            _scope(company_a, user_a),
            embedding=shared,
        )

    contents = [hit.content for hit in hits]
    assert "A memory" in contents
    assert "B secret memory" not in contents
    assert all(isinstance(hit, VectorHit) for hit in hits)


@pytest.mark.asyncio
async def test_cross_company_memory_cannot_appear(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    shared = _vector((2, 1.0))
    async with async_session_factory() as session:
        user_a = await _user(session)
        user_b = await _user(session)
        await _company(session, name="Owner Vec A", user=user_a)
        company_b = await _company(session, name="Owner Vec B", user=user_b)
        session.add(_memory(company_b, content="private-b", embedding=shared))
        await session.commit()
        forged = RetrievalScope(
            company_id=company_b.id,
            user_id=user_a.id,
            role="founder",
        )
        with pytest.raises(RetrievalAccessError):
            await SqlVectorRetriever(session).retrieve(forged, embedding=shared)


@pytest.mark.asyncio
async def test_results_are_ordered_by_similarity(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    query = _vector((0, 1.0))
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="Order Co", user=user)
        session.add(_memory(company, content="far", embedding=_vector((5, 1.0))))
        session.add(_memory(company, content="near", embedding=_vector((0, 0.95), (1, 0.05))))
        session.add(_memory(company, content="closest", embedding=_vector((0, 1.0))))
        await session.commit()
        hits = await SqlVectorRetriever(session).retrieve(
            _scope(company, user),
            embedding=query,
        )

    assert [hit.content for hit in hits] == ["closest", "near", "far"]
    scores = [hit.score for hit in hits]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_top_k_is_respected(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    query = _vector((0, 1.0))
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="TopK Co", user=user)
        for index in range(5):
            session.add(
                _memory(
                    company,
                    content=f"memory-{index}",
                    embedding=_vector((0, 1.0 - index * 0.05)),
                )
            )
        await session.commit()
        hits = await SqlVectorRetriever(session).retrieve(
            _scope(company, user),
            embedding=query,
            limit=2,
        )

    assert len(hits) == 2


@pytest.mark.asyncio
async def test_empty_brain_returns_empty_list(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="Empty Vec", user=user)
        await session.commit()
        hits = await SqlVectorRetriever(session).retrieve(
            _scope(company, user),
            embedding=_vector((0, 1.0)),
        )

    assert hits == []


@pytest.mark.asyncio
async def test_empty_query_returns_empty_list(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="Blank Query", user=user)
        await session.commit()
        hits = await SqlVectorRetriever(session, _FakeEmbedProvider()).retrieve(
            _scope(company, user),
            query_text="   ",
        )

    assert hits == []


@pytest.mark.asyncio
async def test_embedding_provider_is_called_through_abstraction(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = _FakeEmbedProvider(_vector((0, 1.0)))
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="Provider Co", user=user)
        session.add(
            _memory(company, content="CLI memory", embedding=_vector((0, 1.0)))
        )
        await session.commit()
        with patch(
            "app.services.retrieval.sql_vector.get_llm_provider",
            return_value=provider,
        ) as factory:
            hits = await SqlVectorRetriever(session).retrieve(
                _scope(company, user),
                query_text="CLI tools",
            )

    factory.assert_called()
    assert len(provider.requests) == 1
    assert provider.requests[0].input == "CLI tools"
    assert provider.requests[0].model is None
    assert hits[0].content == "CLI memory"


@pytest.mark.asyncio
async def test_provider_failure_is_handled(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = _FakeEmbedProvider(error=ProviderUnavailableError("down"))
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="Fail Co", user=user)
        await session.commit()
        with pytest.raises(VectorRetrievalError, match="Embedding provider failed"):
            await SqlVectorRetriever(session, provider).retrieve(
                _scope(company, user),
                query_text="anything",
            )


@pytest.mark.asyncio
async def test_invalid_embedding_dimension_is_handled(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="Dim Co", user=user)
        await session.commit()
        with pytest.raises(VectorRetrievalError, match="dimension"):
            await SqlVectorRetriever(session).retrieve(
                _scope(company, user),
                embedding=[0.1, 0.2, 0.3],
            )


@pytest.mark.asyncio
async def test_provenance_is_preserved(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    embedding = _vector((3, 1.0))
    async with async_session_factory() as session:
        user = await _user(session)
        company = await _company(session, name="Provenance Co", user=user)
        session.add(
            _memory(
                company,
                content="Interview note",
                embedding=embedding,
                source_reference="intercom:123",
            )
        )
        await session.commit()
        hits = await SqlVectorRetriever(session).retrieve(
            _scope(company, user),
            embedding=embedding,
        )

    assert hits[0].source_type == "founder_input"
    assert hits[0].source_reference == "intercom:123"
    assert hits[0].memory_type == "semantic"
    dumped = hits[0].model_dump()
    assert set(dumped) == {
        "content",
        "score",
        "source_type",
        "source_reference",
        "memory_id",
        "memory_type",
        "created_at",
    }
