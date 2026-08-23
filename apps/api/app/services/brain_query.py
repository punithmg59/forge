"""Grounded Brain query orchestration. Uses context retrieval + LLM provider."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_member import CompanyMember
from app.schemas.brain import BrainQueryResponse, CompanyContext
from app.services.brain_context import build_company_brain_context
from app.services.brain_query_prompt import build_brain_query_completion_request
from app.services.llm import (
    LLMProvider,
    ProviderAuthError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnexpectedError,
    get_llm_provider,
)

T = TypeVar("T", bound=LLMProvider)


class BrainQueryError(Exception):
    def __init__(self, detail: str, status_code: int = 500) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


async def answer_brain_query(
    db: AsyncSession,
    *,
    membership: CompanyMember,
    query: str,
    context_builder: Callable[..., Awaitable[CompanyContext]] = build_company_brain_context,
    provider_factory: Callable[[], T] | None = None,
) -> BrainQueryResponse:
    """Retrieve CompanyContext, complete via LLMProvider, and return a grounded answer."""
    context = await context_builder(db, membership=membership, query=query)
    provider = (provider_factory or get_llm_provider)()
    request = build_brain_query_completion_request(question=query, context=context)

    try:
        result = await provider.complete(request)
    except ProviderAuthError as exc:
        raise BrainQueryError("LLM provider is not configured", 502) from exc
    except ProviderTimeoutError as exc:
        raise BrainQueryError("LLM request timed out", 504) from exc
    except ProviderRateLimitError as exc:
        raise BrainQueryError("LLM rate limit exceeded", 429) from exc
    except ProviderUnavailableError as exc:
        raise BrainQueryError("LLM provider unavailable", 502) from exc
    except ProviderInvalidResponseError as exc:
        raise BrainQueryError("LLM returned an invalid response", 502) from exc
    except ProviderUnexpectedError as exc:
        raise BrainQueryError("LLM provider error", 502) from exc
    except ProviderError as exc:
        raise BrainQueryError("LLM provider error", 502) from exc

    return BrainQueryResponse.from_context(
        answer=result.text,
        context=context,
        model=result.model,
        question=query,
    )
