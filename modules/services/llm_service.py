from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence
from openai import OpenAI
from modules.config import BaseConfig

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
    base_url = None if is_openai else BaseConfig.LLM_BASE_URL
    timeout_seconds = BaseConfig.LLM_TIMEOUT_SECONDS
    if not model.strip():
        raise ValueError("LLM model is not configured")
    if timeout_seconds <= 0:
        raise ValueError("LLM_TIMEOUT_SECONDS must be greater than zero")
    return LLMSettings(provider, model.strip(), api_key, base_url, timeout_seconds)


def get_llm_client(settings: LLMSettings | None = None):
    settings = settings or get_llm_settings()
    if settings.provider == "openai":
        return OpenAI(api_key=settings.api_key), settings.model
    return OpenAI(base_url=settings.base_url, api_key=settings.api_key), settings.model


def request_llm_chat(messages: Sequence[Mapping[str, str]], *, temperature: float) -> str:
    settings = get_llm_settings()
    client, model = get_llm_client(settings)
    response = client.chat.completions.create(model=model,messages=list(messages),temperature=temperature,timeout=settings.timeout_seconds,)
    content = response.choices[0].message.content
    if not content:
        raise ValueError("LLM response is empty")
    return content