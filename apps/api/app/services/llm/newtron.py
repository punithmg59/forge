"""Newtron adapter (OpenAI-compatible NVIDIA NIM API)."""

from __future__ import annotations

from typing import Any, Literal

import httpx

from app.core.config import Settings
from app.services.llm.base import LLMProvider
from app.services.llm.errors import (
    ProviderAuthError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnexpectedError,
)
from app.services.llm.types import (
    CompletionRequest,
    CompletionResult,
    EmbeddingRequest,
    EmbeddingResult,
)

DEFAULT_NEWTRON_BASE_URL = "https://integrate.api.nvidia.com/v1"
_RETRYABLE_STATUS_CODES = frozenset({408, 502, 503, 504})


class NewtronProvider(LLMProvider):
    """Current Forge development LLM. Talks to an OpenAI-compatible HTTP API."""

    name = "newtron"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        embedding_model: str,
        timeout_seconds: float,
        base_url: str = DEFAULT_NEWTRON_BASE_URL,
    ) -> None:
        self._api_key = api_key.strip()
        self._model = model
        self._embedding_model = embedding_model
        self._timeout_seconds = timeout_seconds
        self._base_url = base_url.rstrip("/")
        self._http_client: httpx.AsyncClient | None = None

    async def aclose(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def _http(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient()
        return self._http_client

    @classmethod
    def from_settings(cls, config: Settings) -> NewtronProvider:
        return cls(
            api_key=config.newtron_api_key,
            model=config.llm_model,
            embedding_model=config.llm_embedding_model,
            timeout_seconds=config.llm_timeout_seconds,
            base_url=config.newtron_base_url,
        )

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        self._require_api_key()
        model = request.model or self._model
        timeout = request.timeout if request.timeout is not None else self._timeout_seconds
        payload: dict[str, Any] = {
            "model": model,
            "messages": [message.model_dump() for message in request.messages],
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}

        body = await self._post_json(
            f"{self._base_url}/chat/completions",
            payload=payload,
            timeout=timeout,
        )
        try:
            choice = body["choices"][0]
            text = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
            used_model = body.get("model") or model
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderInvalidResponseError(
                "LLM returned an invalid completion payload"
            ) from exc
        if not isinstance(text, str):
            raise ProviderInvalidResponseError("LLM returned an invalid completion payload")
        return CompletionResult(text=text, model=str(used_model), finish_reason=finish_reason)

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self._require_api_key()
        model = request.model or self._embedding_model
        timeout = request.timeout if request.timeout is not None else self._timeout_seconds
        payload = {"model": model, "input": request.input}
        input_type = request.input_type or self._default_embedding_input_type(model)
        if input_type is not None:
            payload["input_type"] = input_type
        body = await self._post_json(
            f"{self._base_url}/embeddings",
            payload=payload,
            timeout=timeout,
        )
        try:
            embedding = body["data"][0]["embedding"]
            used_model = body.get("model") or model
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderInvalidResponseError(
                "LLM returned an invalid embedding payload"
            ) from exc
        if not isinstance(embedding, list) or not all(
            isinstance(value, (int, float)) for value in embedding
        ):
            raise ProviderInvalidResponseError("LLM returned an invalid embedding payload")
        vector = [float(value) for value in embedding]
        return EmbeddingResult(embedding=vector, model=str(used_model), dimensions=len(vector))

    def _require_api_key(self) -> None:
        if not self._api_key:
            raise ProviderAuthError("LLM API key is not configured")

    @staticmethod
    def _default_embedding_input_type(model: str) -> Literal["query", "passage"] | None:
        lowered = model.lower()
        if "embedqa" in lowered or "e5" in lowered or "nemotron-3-embed" in lowered:
            return "query"
        return None

    async def _post_json(
        self,
        url: str,
        *,
        payload: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        last_response: httpx.Response | None = None
        for attempt in range(2):
            try:
                response = await self._http().post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
            except httpx.TimeoutException as exc:
                if attempt == 0:
                    continue
                raise ProviderTimeoutError("LLM request timed out") from exc
            except httpx.HTTPError as exc:
                if attempt == 0:
                    continue
                raise ProviderUnavailableError("LLM provider unavailable") from exc

            last_response = response
            if response.status_code not in _RETRYABLE_STATUS_CODES or attempt == 1:
                return self._parse_response(response)

        assert last_response is not None
        return self._parse_response(last_response)

    def _parse_response(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code in {401, 403}:
            raise ProviderAuthError("LLM authentication failed")
        if response.status_code == 429:
            raise ProviderRateLimitError("LLM rate limit exceeded")
        if response.status_code == 408:
            raise ProviderTimeoutError("LLM request timed out")
        if response.status_code >= 500:
            raise ProviderUnavailableError("LLM provider unavailable")
        if response.status_code >= 400:
            raise ProviderUnexpectedError("LLM provider error")

        try:
            body = response.json()
        except ValueError as exc:
            raise ProviderInvalidResponseError("LLM returned an invalid response body") from exc
        if not isinstance(body, dict):
            raise ProviderInvalidResponseError("LLM returned an invalid response body")
        return body
