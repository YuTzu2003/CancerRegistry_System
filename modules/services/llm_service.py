"""Global LLM provider settings and shared chat-completion calls."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Sequence

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    api_key: str | None
    base_url: str | None
    timeout_seconds: float


def get_llm_settings() -> LLMSettings:
    """Read the application-wide LLM settings from the environment."""
    provider = os.environ.get("LLM_PROVIDER", "ollama").strip().lower()
    is_openai = provider == "openai"
    model = (os.environ.get("OPENAI_MODEL") if is_openai else os.environ.get("LLM_MODEL")) or ""
    api_key = os.environ.get("OPENAI_API_KEY") if is_openai else os.environ.get("LLM_API_KEY")
    base_url = None if is_openai else os.environ.get("LLM_BASE_URL")
    try:
        timeout_seconds = float(os.environ.get("LLM_TIMEOUT_SECONDS", "180"))
    except ValueError as exc:
        raise ValueError("LLM_TIMEOUT_SECONDS must be a number") from exc
    if not model.strip():
        raise ValueError("LLM model is not configured")
    if timeout_seconds <= 0:
        raise ValueError("LLM_TIMEOUT_SECONDS must be greater than zero")
    return LLMSettings(provider, model.strip(), api_key, base_url, timeout_seconds)


def get_llm_client(settings: LLMSettings | None = None):
    """Create an OpenAI-compatible client for the configured provider."""
    settings = settings or get_llm_settings()
    if settings.provider == "openai":
        return OpenAI(api_key=settings.api_key), settings.model
    return OpenAI(base_url=settings.base_url, api_key=settings.api_key), settings.model


def request_llm_chat(messages: Sequence[Mapping[str, str]], *, temperature: float) -> str:
    """Run one configured chat completion and return its text content."""
    settings = get_llm_settings()
    client, model = get_llm_client(settings)
    response = client.chat.completions.create(
        model=model,
        messages=list(messages),
        temperature=temperature,
        timeout=settings.timeout_seconds,
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("LLM response is empty")
    return content
