from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence
from openai import OpenAI
from modules.config import BaseConfig

_client_cache = None
_client_settings = None

@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    api_key: str | None
    base_url: str | None
    timeout_seconds: float

def get_llm_settings() -> LLMSettings:
    provider = BaseConfig.LLM_PROVIDER
    is_openai = provider == "openai"
    model = BaseConfig.OPENAI_MODEL if is_openai else BaseConfig.LLM_MODEL
    api_key = BaseConfig.OPENAI_API_KEY if is_openai else BaseConfig.LLM_API_KEY
    base_url = BaseConfig.LLM_BASE_URL
    timeout_seconds = BaseConfig.LLM_TIMEOUT_SECONDS
    if not model.strip():
        raise ValueError("LLM model is not configured")
    if timeout_seconds <= 0:
        raise ValueError("LLM_TIMEOUT_SECONDS must be greater than zero")
    return LLMSettings(provider, model.strip(), api_key, base_url, timeout_seconds)


def get_llm_client(settings: LLMSettings | None = None):
    global _client_cache, _client_settings
    settings = settings or get_llm_settings()
    if _client_cache is not None and _client_settings == settings:
        return _client_cache, settings.model
    if settings.provider == "openai" and not settings.base_url:
        _client_cache = OpenAI(api_key=settings.api_key)
    else:
        _client_cache = OpenAI(base_url=settings.base_url, api_key=settings.api_key)
    _client_settings = settings
    return _client_cache, settings.model


def check_llm_readiness() -> None:
    settings = get_llm_settings()
    client, model = get_llm_client(settings)
    available_models = {item.id for item in client.models.list().data}
    if model not in available_models:
        raise ValueError(f"Configured LLM model is unavailable: {model}")
    if settings.provider == "ollama":
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "health check"}],
            temperature=0,
            max_tokens=1,
            timeout=min(settings.timeout_seconds, 30),
        )
        if not response.choices:
            raise ValueError("Ollama readiness response has no completion choices")


def request_llm_chat(messages: Sequence[Mapping[str, str]], *, temperature: float) -> str:
    settings = get_llm_settings()
    client, model = get_llm_client(settings)
    response = client.chat.completions.create(model=model,messages=list(messages),temperature=temperature,timeout=settings.timeout_seconds,)
    content = response.choices[0].message.content
    if not content:
        raise ValueError("LLM response is empty")
    return content
