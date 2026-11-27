from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import logging
import os
import random
import time
from typing import Callable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
import openai
from openai import OpenAI
from modules.config import BaseConfig

_client_cache = None
_client_settings = None

# --- Transient-failure retry (項目 11) --------------------------------------
# Bounded exponential backoff with full jitter for rate limits (429), transient
# 5xx, and connection/timeout errors, for both the OpenAI client path and the
# Azure Responses HTTP path. Honours a Retry-After header when the server sends
# one. Non-transient errors (e.g. 400/401) are raised immediately. Defaults are
# overridable by env; no external dependency (tenacity) is required.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _retry_env_int(name, default):
    value = os.getenv(name)
    try:
        return max(1, int(value)) if value and value.strip() else default
    except ValueError:
        return default


def _retry_env_float(name, default):
    value = os.getenv(name)
    try:
        return max(0.0, float(value)) if value and value.strip() else default
    except ValueError:
        return default


LLM_MAX_ATTEMPTS = _retry_env_int("LLM_MAX_ATTEMPTS", 4)      # total tries incl. first
LLM_RETRY_BASE_DELAY = _retry_env_float("LLM_RETRY_BASE_DELAY", 0.5)  # seconds
LLM_RETRY_MAX_DELAY = _retry_env_float("LLM_RETRY_MAX_DELAY", 20.0)   # seconds cap


def _status_code(error):
    code = getattr(error, "status_code", None)
    if code is None:
        code = getattr(error, "code", None)  # urllib.error.HTTPError
    return code if isinstance(code, int) else None


def _is_retryable(error):
    if isinstance(error, (openai.APIConnectionError, openai.APITimeoutError, URLError)) \
            and not isinstance(error, HTTPError):
        return True
    return _status_code(error) in _RETRYABLE_STATUS


def _retry_after_seconds(error):
    """Return the Retry-After value in seconds if the server provided one."""
    headers = getattr(getattr(error, "response", None), "headers", None)
    if headers is None:
        headers = getattr(error, "headers", None)  # urllib.error.HTTPError
    if headers is None:
        return None
    raw = headers.get("Retry-After")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        pass
    try:  # HTTP-date form, e.g. "Wed, 21 Oct 2026 07:28:00 GMT"
        when = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


def _backoff_delay(attempt):
    """Full-jitter backoff for a 1-based attempt number."""
    capped = min(LLM_RETRY_MAX_DELAY, LLM_RETRY_BASE_DELAY * (2 ** (attempt - 1)))
    return random.uniform(0, capped)


def _retry_transient(operation: Callable, *, sleep: Callable | None = None):
    sleep = sleep or time.sleep
    last_error = None
    for attempt in range(1, LLM_MAX_ATTEMPTS + 1):
        try:
            return operation()
        except Exception as error:  # noqa: BLE001 - reclassified below
            last_error = error
            if attempt >= LLM_MAX_ATTEMPTS or not _is_retryable(error):
                raise
            delay = _retry_after_seconds(error)
            if delay is None:
                delay = _backoff_delay(attempt)
            logging.warning(
                "LLM call failed (attempt %s/%s, status=%r); retrying in %.2fs",
                attempt, LLM_MAX_ATTEMPTS, _status_code(error), delay,
            )
            sleep(delay)
    raise last_error  # pragma: no cover - loop always returns or raises above
# ----------------------------------------------------------------------------

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
    # max_retries=0 disables the SDK's own retry loop so _retry_transient is the
    # single retry layer (otherwise LLM_MAX_ATTEMPTS is not the real ceiling and
    # the SDK would also retry 408/409 outside this module's policy).
    if settings.provider == "openai" and not settings.base_url:
        _client_cache = OpenAI(api_key=settings.api_key, max_retries=0)
    else:
        _client_cache = OpenAI(base_url=settings.base_url, api_key=settings.api_key, max_retries=0)
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
        response = _retry_transient(
            lambda: client.chat.completions.create(
                model=model,
                messages=list(messages),
                temperature=temperature,
                timeout=settings.timeout_seconds,
            )
        )
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
        logging.warning(
            "LLM returned empty content (attempt %s/2, finish_reason=%r)",
            attempt + 1,
            last_finish_reason,
        )
    raise ValueError(f"LLM response is empty (finish_reason={last_finish_reason!r})")


def request_azure_responses(settings: LLMSettings, messages: Sequence[Mapping[str, str]], *, temperature: float) -> str:
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
    def _send():
        with urlopen(request, timeout=settings.timeout_seconds) as response:
            return response.read().decode("utf-8")

    body = json.loads(_retry_transient(_send))
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
