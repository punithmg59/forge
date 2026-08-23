"""Newtron adapter (OpenAI-compatible NVIDIA NIM API)."""

from __future__ import annotations

from typing import Any

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
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("LLM request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("LLM provider unavailable") from exc

        return self._parse_response(response)

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
