"""Normalized LLM completion and embedding contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ChatRole = Literal["system", "user", "assistant"]
ResponseFormat = Literal["text", "json_object"]


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: ChatRole
    content: str


class CompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(min_length=1)
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    timeout: float | None = None
    response_format: ResponseFormat = "text"


class CompletionResult(BaseModel):
    """Provider-agnostic completion output. No raw vendor payloads."""

    model_config = ConfigDict(extra="forbid")

    text: str
    model: str
    finish_reason: str | None = None


class EmbeddingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: str
    model: str | None = None
    timeout: float | None = None


class EmbeddingResult(BaseModel):
    """Provider-agnostic embedding output. No raw vendor payloads."""

    model_config = ConfigDict(extra="forbid")

    embedding: list[float]
    model: str
    dimensions: int | None = None
