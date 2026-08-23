"""Unit tests for the Task 5.1 LLM provider abstraction. No live provider calls."""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.services.llm import (
    ChatMessage,
    CompletionRequest,
    CompletionResult,
    EmbeddingRequest,
    EmbeddingResult,
    LLMProvider,
    NewtronProvider,
    ProviderAuthError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnexpectedError,
    get_llm_provider,
)
from app.services.llm.newtron import DEFAULT_NEWTRON_BASE_URL
from app.services.llm_client import LLMError, complete_json

API_ROOT = Path(__file__).resolve().parents[1] / "app"


class _FakeResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeAsyncClient:
    """httpx.AsyncClient stand-in so tests never open a network connection."""

    last: dict[str, Any] = {}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _FakeAsyncClient.last["timeout"] = kwargs.get("timeout")
        _FakeAsyncClient.last["init_args"] = args
        _FakeAsyncClient.last["init_kwargs"] = kwargs

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def post(self, url: str, headers: dict[str, str] | None = None, json: Any = None) -> _FakeResponse:
        _FakeAsyncClient.last["url"] = url
        _FakeAsyncClient.last["headers"] = headers
        _FakeAsyncClient.last["json"] = json
        handler = _FakeAsyncClient.last.get("handler")
        if handler is not None:
            return handler(url, headers, json)
        return _FakeResponse(
            200,
            {
                "id": "chatcmpl-vendor-only",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "normalized-text"},
                        "finish_reason": "stop",
                    }
                ],
                "model": json["model"] if isinstance(json, dict) else "unknown",
            },
        )


class _StubProvider(LLMProvider):
    """Test-only consumer stand-in. Not a shipped OpenAI/Claude adapter."""

    name = "stub"

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        return CompletionResult(text="stub-complete", model="stub-model")

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        return EmbeddingResult(embedding=[0.25, 0.5], model="stub-embed", dimensions=2)


def _provider(**overrides: Any) -> NewtronProvider:
    values = {
        "api_key": "test-api-key",
        "model": "nvidia/nemotron-3-ultra-550b-a55b",
        "embedding_model": "nvidia/nv-embedqa-e5-v5",
        "timeout_seconds": 15.0,
        "base_url": "https://example.test/v1",
    }
    values.update(overrides)
    return NewtronProvider(**values)


def _config(**overrides: Any) -> SimpleNamespace:
    values = {
        "llm_provider": "newtron",
        "llm_model": "configured-complete-model",
        "llm_embedding_model": "configured-embed-model",
        "llm_timeout_seconds": 9.0,
        "newtron_api_key": "config-api-key",
        "newtron_base_url": "https://example.test/v1",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


async def _complete_via_interface(provider: LLMProvider) -> str:
    result = await provider.complete(
        CompletionRequest(messages=[ChatMessage(role="user", content="hello")])
    )
    return result.text


def test_provider_instantiated_from_configuration() -> None:
    provider = get_llm_provider(_config())  # type: ignore[arg-type]
    assert isinstance(provider, LLMProvider)
    assert isinstance(provider, NewtronProvider)
    assert provider.name == "newtron"


def test_newtron_selected_when_configured() -> None:
    provider = get_llm_provider(_config(llm_provider="Newtron"))  # type: ignore[arg-type]
    assert type(provider) is NewtronProvider


def test_model_configuration_is_used_by_adapter() -> None:
    provider = NewtronProvider.from_settings(_config())  # type: ignore[arg-type]
    assert provider._model == "configured-complete-model"
    assert provider._embedding_model == "configured-embed-model"


def test_api_key_comes_from_configuration() -> None:
    provider = NewtronProvider.from_settings(_config(newtron_api_key="from-settings"))  # type: ignore[arg-type]
    assert provider._api_key == "from-settings"


def test_settings_default_api_key_is_empty() -> None:
    field = Settings.model_fields["newtron_api_key"]
    assert field.default == ""


def test_no_api_key_hardcoded_in_provider_code() -> None:
    llm_dir = API_ROOT / "services" / "llm"
    sources = [llm_dir.joinpath(name).read_text(encoding="utf-8") for name in [
        "newtron.py",
        "factory.py",
        "base.py",
        "types.py",
        "errors.py",
        "__init__.py",
    ]]
    sources.append((API_ROOT / "core" / "config.py").read_text(encoding="utf-8"))
    blob = "\n".join(sources)
    assert "nvapi-" not in blob
    assert re.search(r"sk-[A-Za-z0-9]{8,}", blob) is None
    assert "YOUR_NVIDIA_API_KEY" not in blob


@pytest.mark.asyncio
async def test_completion_response_is_normalized() -> None:
    provider = _provider()
    with patch("app.services.llm.newtron.httpx.AsyncClient", _FakeAsyncClient):
        result = await provider.complete(
            CompletionRequest(messages=[ChatMessage(role="user", content="hi")])
        )
    assert type(result) is CompletionResult
    assert result.text == "normalized-text"
    assert result.model == "nvidia/nemotron-3-ultra-550b-a55b"
    assert result.finish_reason == "stop"
    assert result.model_dump() == {
        "text": "normalized-text",
        "model": "nvidia/nemotron-3-ultra-550b-a55b",
        "finish_reason": "stop",
    }


@pytest.mark.asyncio
async def test_configured_model_sent_in_completion_payload() -> None:
    provider = _provider(model="must-use-this-model")
    with patch("app.services.llm.newtron.httpx.AsyncClient", _FakeAsyncClient):
        await provider.complete(
            CompletionRequest(messages=[ChatMessage(role="user", content="hi")])
        )
    assert _FakeAsyncClient.last["json"]["model"] == "must-use-this-model"
    assert _FakeAsyncClient.last["url"] == "https://example.test/v1/chat/completions"


@pytest.mark.asyncio
async def test_authorization_header_uses_configured_key() -> None:
    provider = _provider(api_key="header-secret")
    with patch("app.services.llm.newtron.httpx.AsyncClient", _FakeAsyncClient):
        await provider.complete(
            CompletionRequest(messages=[ChatMessage(role="user", content="hi")])
        )
    assert _FakeAsyncClient.last["headers"]["Authorization"] == "Bearer header-secret"


@pytest.mark.asyncio
async def test_embedding_response_is_normalized() -> None:
    def handler(_url: str, _headers: dict[str, str] | None, payload: Any) -> _FakeResponse:
        return _FakeResponse(
            200,
            {
                "object": "list",
                "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2, 1]}],
                "model": payload["model"],
            },
        )

    _FakeAsyncClient.last["handler"] = handler
    provider = _provider(embedding_model="must-embed-model")
    try:
        with patch("app.services.llm.newtron.httpx.AsyncClient", _FakeAsyncClient):
            result = await provider.embed(EmbeddingRequest(input="company brain"))
    finally:
        _FakeAsyncClient.last.pop("handler", None)

    assert type(result) is EmbeddingResult
    assert result.embedding == [0.1, 0.2, 1.0]
    assert result.model == "must-embed-model"
    assert result.dimensions == 3
    assert _FakeAsyncClient.last["url"] == "https://example.test/v1/embeddings"
    assert _FakeAsyncClient.last["json"]["model"] == "must-embed-model"
    assert _FakeAsyncClient.last["json"]["input"] == "company brain"


@pytest.mark.asyncio
async def test_asymmetric_embedding_models_send_input_type() -> None:
    def handler(_url: str, _headers: dict[str, str] | None, payload: Any) -> _FakeResponse:
        return _FakeResponse(
            200,
            {
                "object": "list",
                "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}],
                "model": payload["model"],
            },
        )

    _FakeAsyncClient.last["handler"] = handler
    provider = _provider(embedding_model="nvidia/nv-embedqa-e5-v5")
    try:
        with patch("app.services.llm.newtron.httpx.AsyncClient", _FakeAsyncClient):
            await provider.embed(EmbeddingRequest(input="search query"))
    finally:
        _FakeAsyncClient.last.pop("handler", None)

    assert _FakeAsyncClient.last["json"]["input_type"] == "query"


@pytest.mark.asyncio
async def test_timeout_becomes_normalized_error() -> None:
    class TimeoutClient(_FakeAsyncClient):
        async def post(self, url: str, headers: dict[str, str] | None = None, json: Any = None) -> _FakeResponse:
            raise httpx.TimeoutException("slow")

    provider = _provider(timeout_seconds=1.0)
    with patch("app.services.llm.newtron.httpx.AsyncClient", TimeoutClient):
        with pytest.raises(ProviderTimeoutError, match="timed out"):
            await provider.complete(
                CompletionRequest(messages=[ChatMessage(role="user", content="hi")])
            )


@pytest.mark.asyncio
async def test_connect_failure_becomes_unavailable() -> None:
    class DownClient(_FakeAsyncClient):
        async def post(self, url: str, headers: dict[str, str] | None = None, json: Any = None) -> _FakeResponse:
            raise httpx.ConnectError("offline")

    provider = _provider()
    with patch("app.services.llm.newtron.httpx.AsyncClient", DownClient):
        with pytest.raises(ProviderUnavailableError, match="unavailable"):
            await provider.embed(EmbeddingRequest(input="x"))


@pytest.mark.asyncio
async def test_authentication_failure_becomes_normalized_error() -> None:
    def handler(*_args: Any) -> _FakeResponse:
        return _FakeResponse(401, {"error": {"message": "bad key"}})

    _FakeAsyncClient.last["handler"] = handler
    provider = _provider()
    try:
        with patch("app.services.llm.newtron.httpx.AsyncClient", _FakeAsyncClient):
            with pytest.raises(ProviderAuthError, match="authentication"):
                await provider.complete(
                    CompletionRequest(messages=[ChatMessage(role="user", content="hi")])
                )
    finally:
        _FakeAsyncClient.last.pop("handler", None)


@pytest.mark.asyncio
async def test_missing_api_key_is_auth_error() -> None:
    provider = _provider(api_key="  ")
    with pytest.raises(ProviderAuthError, match="not configured"):
        await provider.complete(
            CompletionRequest(messages=[ChatMessage(role="user", content="hi")])
        )


@pytest.mark.asyncio
async def test_rate_limit_becomes_normalized_error() -> None:
    def handler(*_args: Any) -> _FakeResponse:
        return _FakeResponse(429, {"error": {"message": "slow down"}})

    _FakeAsyncClient.last["handler"] = handler
    provider = _provider()
    try:
        with patch("app.services.llm.newtron.httpx.AsyncClient", _FakeAsyncClient):
            with pytest.raises(ProviderRateLimitError, match="rate limit"):
                await provider.complete(
                    CompletionRequest(messages=[ChatMessage(role="user", content="hi")])
                )
    finally:
        _FakeAsyncClient.last.pop("handler", None)


@pytest.mark.asyncio
async def test_invalid_completion_payload_is_handled() -> None:
    def handler(*_args: Any) -> _FakeResponse:
        return _FakeResponse(200, {"id": "broken", "choices": []})

    _FakeAsyncClient.last["handler"] = handler
    provider = _provider()
    try:
        with patch("app.services.llm.newtron.httpx.AsyncClient", _FakeAsyncClient):
            with pytest.raises(ProviderInvalidResponseError):
                await provider.complete(
                    CompletionRequest(messages=[ChatMessage(role="user", content="hi")])
                )
    finally:
        _FakeAsyncClient.last.pop("handler", None)


@pytest.mark.asyncio
async def test_invalid_embedding_payload_is_handled() -> None:
    def handler(*_args: Any) -> _FakeResponse:
        return _FakeResponse(200, {"data": [{"embedding": "not-a-vector"}]})

    _FakeAsyncClient.last["handler"] = handler
    provider = _provider()
    try:
        with patch("app.services.llm.newtron.httpx.AsyncClient", _FakeAsyncClient):
            with pytest.raises(ProviderInvalidResponseError):
                await provider.embed(EmbeddingRequest(input="x"))
    finally:
        _FakeAsyncClient.last.pop("handler", None)


@pytest.mark.asyncio
async def test_non_json_body_is_invalid_response() -> None:
    def handler(*_args: Any) -> _FakeResponse:
        return _FakeResponse(200, json.JSONDecodeError("Expecting value", "", 0))

    _FakeAsyncClient.last["handler"] = handler
    provider = _provider()
    try:
        with patch("app.services.llm.newtron.httpx.AsyncClient", _FakeAsyncClient):
            with pytest.raises(ProviderInvalidResponseError):
                await provider.complete(
                    CompletionRequest(messages=[ChatMessage(role="user", content="hi")])
                )
    finally:
        _FakeAsyncClient.last.pop("handler", None)


@pytest.mark.asyncio
async def test_vendor_payload_does_not_leak_through_abstraction() -> None:
    provider = _provider()
    with patch("app.services.llm.newtron.httpx.AsyncClient", _FakeAsyncClient):
        result = await provider.complete(
            CompletionRequest(messages=[ChatMessage(role="user", content="hi")])
        )
    assert not hasattr(result, "choices")
    assert not hasattr(result, "object")
    dumped = result.model_dump()
    assert set(dumped) == {"text", "model", "finish_reason"}


@pytest.mark.asyncio
async def test_provider_can_be_swapped_without_changing_consumer() -> None:
    stub = _StubProvider()
    assert await _complete_via_interface(stub) == "stub-complete"

    with patch("app.services.llm.newtron.httpx.AsyncClient", _FakeAsyncClient):
        newtron_text = await _complete_via_interface(_provider())
    assert newtron_text == "normalized-text"


def test_future_providers_are_not_silently_invented() -> None:
    with pytest.raises(ProviderUnexpectedError, match="not implemented"):
        get_llm_provider(_config(llm_provider="openai"))  # type: ignore[arg-type]
    with pytest.raises(ProviderUnexpectedError, match="not implemented"):
        get_llm_provider(_config(llm_provider="claude"))  # type: ignore[arg-type]


def test_newtron_default_base_url_matches_existing_nvidia_endpoint() -> None:
    assert DEFAULT_NEWTRON_BASE_URL == "https://integrate.api.nvidia.com/v1"


@pytest.mark.asyncio
async def test_complete_json_maps_provider_errors() -> None:
    with patch(
        "app.services.llm_client.get_llm_provider",
        return_value=_provider(api_key=""),
    ):
        with pytest.raises(LLMError, match="not configured"):
            await complete_json(system_prompt="s", user_prompt="u")


def test_complete_and_embed_are_interface_methods() -> None:
    assert "complete" in LLMProvider.__abstractmethods__
    assert "embed" in LLMProvider.__abstractmethods__
    assert inspect.signature(NewtronProvider.complete).parameters["request"].annotation in {
        CompletionRequest,
        "CompletionRequest",
    }
