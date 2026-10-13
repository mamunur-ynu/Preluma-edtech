"""
ai/llm_router.py — one place that knows how to talk to every LLM provider.

The original ``llm.py`` had seven near-identical ``_call_<provider>`` functions that silently
swallowed every error.  This router replaces them with a small table of :class:`ProviderSpec`
entries and a single failover loop:

* providers are tried **in order**; the first non-empty answer wins;
* every failure is *logged* (provider + reason, never the API key) and remembered in
  ``last_error`` so the UI can show what went wrong;
* the HTTP call is injected (``transport``), so tests run without network access;
* three wire formats cover all providers: OpenAI-compatible, Anthropic and Gemini.

Keys are read from environment variables (see ``config.load_streamlit_secrets_into_env``) —
this module never imports Streamlit.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

import requests

from config import get_setting, get_settings
from security.rate_limit import DatabaseRateLimiter, InProcessRateLimiter, RateLimitExceeded, shared_limits_enabled

logger = logging.getLogger("preluma.llm")

Message = Mapping[str, str]                       # {"role": "user"|"assistant", "content": "..."}
Transport = Callable[[str, dict, dict, int], dict]  # (url, headers, json_body, timeout) -> parsed JSON


@dataclass(frozen=True)
class ProviderSpec:
    name: str            # short id
    label: str           # shown to users
    key_env: str
    model_env: str
    default_model: str
    url: str
    wire: str = "openai"  # openai | anthropic | gemini
    extra_headers: Mapping[str, str] = field(default_factory=dict)

    def api_key(self) -> str:
        return os.environ.get(self.key_env, "").strip()

    def model(self) -> str:
        return os.environ.get(self.model_env, "").strip() or self.default_model


# Failover order: fast/free tiers first, paid providers as safety nets, Gemini last.
PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec("groq", "Groq", "GROQ_API_KEY", "GROQ_MODEL", "llama-3.3-70b-versatile",
                 "https://api.groq.com/openai/v1/chat/completions"),
    ProviderSpec("cerebras", "Cerebras", "CEREBRAS_API_KEY", "CEREBRAS_MODEL", "llama-3.3-70b",
                 "https://api.cerebras.ai/v1/chat/completions"),
    ProviderSpec("mistral", "Mistral", "MISTRAL_API_KEY", "MISTRAL_MODEL", "mistral-small-latest",
                 "https://api.mistral.ai/v1/chat/completions"),
    ProviderSpec("openrouter", "OpenRouter", "OPENROUTER_API_KEY", "OPENROUTER_MODEL",
                 "meta-llama/llama-3.3-70b-instruct:free",
                 "https://openrouter.ai/api/v1/chat/completions",
                 extra_headers={"HTTP-Referer": "https://prelumaedtech.streamlit.app", "X-Title": "Preluma"}),
    ProviderSpec("together", "Together AI", "TOGETHER_API_KEY", "TOGETHER_MODEL",
                 "meta-llama/Llama-3.3-70B-Instruct-Turbo", "https://api.together.xyz/v1/chat/completions"),
    ProviderSpec("openai", "OpenAI", "OPENAI_API_KEY", "OPENAI_MODEL", "gpt-4.1-mini",
                 "https://api.openai.com/v1/chat/completions"),
    ProviderSpec("anthropic", "Claude (Anthropic)", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL",
                 "claude-sonnet-4-20250514", "https://api.anthropic.com/v1/messages", wire="anthropic"),
    ProviderSpec("gemini", "Gemini", "GEMINI_API_KEY", "GEMINI_MODEL", "gemini-1.5-flash",
                 "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                 wire="gemini"),
)
_GEMINI_FALLBACK_MODELS = ("gemini-1.5-flash", "gemini-2.0-flash")


def default_transport(url: str, headers: dict, body: dict, timeout: int) -> dict:
    """POST JSON and return the decoded response (raises ``requests.HTTPError`` on 4xx/5xx)."""
    response = requests.post(url, headers=headers, json=body, timeout=timeout)
    response.raise_for_status()
    return response.json()


@dataclass
class LLMResult:
    text: str
    provider: str = ""       # label of the provider that answered ("" if none did)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.text)


class LLMRouter:
    """Sequential-failover chat completion across the configured providers."""

    def __init__(
        self,
        providers: Sequence[ProviderSpec] = PROVIDERS,
        transport: Transport = default_transport,
        timeout: int | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.providers = tuple(providers)
        self.transport = transport
        self.timeout = timeout or int(os.environ.get("PRELUMA_LLM_TIMEOUT", "20"))
        self.max_tokens = max_tokens or int(os.environ.get("PRELUMA_LLM_MAX_TOKENS", "2200"))
        self.last_error = ""
        self.last_provider = ""
        self._local_call_budget: tuple[int, InProcessRateLimiter] | None = None

    def _transport_with_budget(self, url: str, headers: dict, body: dict, timeout: int) -> dict:
        """Reserve one call before every HTTP attempt, including model fallbacks."""
        raw = get_setting("PRELUMA_PROVIDER_CALLS_PER_HOUR")
        if not raw and not get_settings().is_sqlite:
            raise RateLimitExceeded("Live provider call budget is not configured.")
        try:
            limit = int(raw) if raw else 120  # bounded local demo default
        except ValueError as exc:
            raise RateLimitExceeded("Live provider call budget is invalid.") from exc
        if limit < 1:
            raise RateLimitExceeded("Live provider calls are disabled.")
        try:
            if shared_limits_enabled():
                DatabaseRateLimiter(limit, 3600).check("provider:all")
            else:
                if self._local_call_budget is None or self._local_call_budget[0] != limit:
                    self._local_call_budget = (limit, InProcessRateLimiter(limit, 3600))
                self._local_call_budget[1].check("provider:all")
        except RateLimitExceeded as exc:
            raise RateLimitExceeded("Live provider call budget exhausted.") from exc
        except Exception as exc:
            raise RateLimitExceeded("Live provider call budget is unavailable.") from exc
        return self.transport(url, headers, body, timeout)

    # ── introspection ────────────────────────────────────────────────────────
    def available(self) -> list[ProviderSpec]:
        """Providers that have an API key configured, in failover order."""
        return [p for p in self.providers if p.api_key()]

    def available_labels(self) -> list[str]:
        return [p.label for p in self.available()]

    def active_label(self) -> str:
        labels = self.available_labels()
        return labels[0] if labels else "Curated fallback"

    def is_available(self) -> bool:
        return bool(self.available())

    # ── public API ───────────────────────────────────────────────────────────
    def complete(self, system: str, user: str, history: Sequence[Message] = ()) -> LLMResult:
        """Ask the first provider that answers.  Never raises; check ``result.ok``."""
        errors: list[str] = []
        for spec in self.available():
            try:
                text = self._call(spec, system, user, history)
            except RateLimitExceeded as exc:
                errors.append(str(exc))
                break
            except Exception as exc:  # network, HTTP, malformed JSON …
                reason = f"{spec.label}: {self._describe(exc)}"
                logger.warning("LLM provider failed — %s", reason)
                errors.append(reason)
                continue
            if text:
                self.last_provider = spec.label
                self.last_error = "; ".join(errors)
                return LLMResult(text=text, provider=spec.label, errors=errors)
            errors.append(f"{spec.label}: empty response")
        self.last_error = "; ".join(errors)
        return LLMResult(text="", provider="", errors=errors)

    # ── provider calls ───────────────────────────────────────────────────────
    def _call(self, spec: ProviderSpec, system: str, user: str, history: Sequence[Message]) -> str:
        key = spec.api_key()
        messages = [{"role": m["role"], "content": m["content"]} for m in history] + [
            {"role": "user", "content": user}
        ]
        if spec.wire == "anthropic":
            payload = self._transport_with_budget(
                spec.url,
                {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                {"model": spec.model(), "max_tokens": self.max_tokens, "system": system, "messages": messages},
                self.timeout,
            )
            for block in payload.get("content", []):
                if block.get("type") == "text":
                    return str(block["text"]).strip()
            return ""
        if spec.wire == "gemini":
            return self._call_gemini(spec, key, system, messages)
        payload = self._transport_with_budget(
            spec.url,
            {"Authorization": f"Bearer {key}", "Content-Type": "application/json", **spec.extra_headers},
            {
                "model": spec.model(),
                "max_tokens": self.max_tokens,
                "messages": [{"role": "system", "content": system}, *messages],
            },
            self.timeout,
        )
        return str(payload["choices"][0]["message"]["content"]).strip()

    def _call_gemini(self, spec: ProviderSpec, key: str, system: str, messages: list[dict]) -> str:
        contents = [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages
        ]
        errors = []
        for model in dict.fromkeys((spec.model(), *_GEMINI_FALLBACK_MODELS)):  # ordered, unique
            try:
                payload = self._transport_with_budget(
                    spec.url.format(model=model),
                    # Key goes in a header, not the URL, so it never lands in access logs.
                    {"Content-Type": "application/json", "x-goog-api-key": key},
                    {
                        "systemInstruction": {"parts": [{"text": system}]},
                        "contents": contents,
                        "generationConfig": {"maxOutputTokens": self.max_tokens, "temperature": 0.5},
                    },
                    self.timeout,
                )
                text = str(payload["candidates"][0]["content"]["parts"][0]["text"]).strip()
                if text:
                    return text
            except RateLimitExceeded:
                raise
            except Exception as exc:
                errors.append(f"{model}: {self._describe(exc)}")
        raise RuntimeError("; ".join(errors) or "no usable Gemini model")

    @staticmethod
    def _describe(exc: Exception) -> str:
        response: Any = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
        return f"HTTP {status}" if status else type(exc).__name__


_default_router: LLMRouter | None = None


def get_router() -> LLMRouter:
    """Process-wide router (providers are re-checked against the environment on each call)."""
    global _default_router
    if _default_router is None:
        _default_router = LLMRouter()
    return _default_router
