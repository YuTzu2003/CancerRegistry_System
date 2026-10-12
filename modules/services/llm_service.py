from __future__ import annotations
from dataclasses import dataclass
import json
import logging
from typing import Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
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
    azure_api_key: str | None
    azure_responses_url: str | None
    azure_api_version: str | None
    timeout_seconds: float

def get_llm_settings() -> LLMSettings:
    provider = BaseConfig.LLM_PROVIDER
    is_openai = provider == "openai"
    model = BaseConfig.MODEL
    api_key = BaseConfig.OPENAI_API_KEY if is_openai else BaseConfig.LLM_API_KEY
    base_url = BaseConfig.LLM_BASE_URL
    azure_api_key = BaseConfig.AZURE_OPENAI_API_KEY
    azure_responses_url = BaseConfig.AZURE_OPENAI_RESPONSES_URL or None
    azure_api_version = BaseConfig.AZURE_OPENAI_API_VERSION or None
    timeout_seconds = BaseConfig.LLM_TIMEOUT_SECONDS
    if not model.strip():
        raise ValueError("LLM model is not configured")
    if timeout_seconds <= 0:
        raise ValueError("LLM_TIMEOUT_SECONDS must be greater than zero")
    if provider == "azure" and not azure_responses_url:
        raise ValueError("AZURE_OPENAI_RESPONSES_URL must be configured for Azure LLM provider")
    if provider == "azure" and not azure_api_key:
        raise ValueError("AZURE_OPENAI_API_KEY must be configured for Azure LLM provider")
    return LLMSettings(provider,model.strip(),api_key,base_url,azure_api_key,azure_responses_url,azure_api_version,timeout_seconds,)

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
    if settings.provider == "azure":
        request_llm_chat([{"role": "user", "content": "health check"}], temperature=0)
        return
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
    if settings.provider == "azure":
        return request_azure_responses(settings, messages, temperature=temperature)
    client, model = get_llm_client(settings)
    last_finish_reason = None
    for attempt in range(2):
        response = client.chat.completions.create(model=model,messages=list(messages),temperature=temperature,timeout=settings.timeout_seconds,)
        choices = getattr(response, "choices", None) or []
        if choices:
            last_finish_reason = getattr(choices[0], "finish_reason", None)
            content = getattr(getattr(choices[0], "message", None), "content", None)
            if isinstance(content, str) and content.strip():
                return content
            if isinstance(content, list):
                parts = []
                for item in content:
                    text = item.get("text") if isinstance(item, Mapping) else getattr(item, "text", None)
                    if text:
                        parts.append(str(text))
                if "".join(parts).strip():
                    return "".join(parts)
        logging.warning("LLM returned empty content (attempt %s/2, finish_reason=%r)",attempt + 1, last_finish_reason,)
    raise ValueError(f"LLM response is empty (finish_reason={last_finish_reason!r})")

def request_azure_responses(settings: LLMSettings,messages: Sequence[Mapping[str, str]],*,temperature: float,) -> str:
    payload = {
        "model": settings.model,
        "input": [
            {
                "role": message["role"],
                "content": [{"type": "input_text", "text": message["content"]}],
            }
            for message in messages
        ],
        "temperature": temperature,
        "stream": False,
    }
    url = urlsplit(settings.azure_responses_url or "")
    query = dict(parse_qsl(url.query))
    if settings.azure_api_version:
        query["api-version"] = settings.azure_api_version
    request_url = urlunsplit((url.scheme, url.netloc, url.path, urlencode(query), url.fragment))
    request = Request(
        request_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "api-key": settings.azure_api_key or "",
        },
        method="POST",
    )
    with urlopen(request, timeout=settings.timeout_seconds) as response:
        body = json.loads(response.read().decode("utf-8"))
    content = body.get("output_text")
    if not content:
        content = "".join(
            item.get("text", "")
            for output in body.get("output", [])
            if output.get("type") == "message"
            for item in output.get("content", [])
            if item.get("type") == "output_text"
        )
    if not content:
        raise ValueError("Azure Responses API response is empty")
    return content
