"""Claude through the official Anthropic SDK (written with the claude-api skill).

Structured output: `output_config.format` with the answer's JSON schema. Thinking stays on
(Claude Opus 5.5 cannot disable it); `effort` controls its depth. Server-side refusal
fallback (`fallbacks: "default"`) is on, so a declined request is re-run on Anthropic's
recommended fallback model instead of failing; the answering model is reported.

No request is made unless the caller asks for one. Costs are estimated from the per-token
prices below (USD per million tokens, from the claude-api skill, 2026-10-06).
"""

import os
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal

from finhak.llm.base import (
    ChatMessage,
    LLMError,
    LLMOutputError,
    LLMRefusal,
    LLMResult,
    LLMUnavailable,
    T,
    Usage,
    json_schema,
    parse_reply,
)

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
PRICES_PER_MTOK = {"claude-opus-5-5": (4.00, 20.00)}  # input, output
Effort = Literal["low", "medium", "high", "xhigh", "max"]


class AnthropicProvider:
    def __init__(
        self,
        client: Any | None = None,
        model: str = DEFAULT_MODEL,
        effort: Effort = "medium",
        max_tokens: int = 16000,
        timeout: float = 120.0,
        max_retries: int = 2,
        api_key: str | None = None,
        auth_token: str | None = None,
    ) -> None:
        """`api_key`/`auth_token` come from .env via the factory; the SDK itself reads only
        the process environment (and an `ant` profile)."""
        if client is None:
            try:
                import anthropic
            except ImportError as exc:
                raise LLMUnavailable(
                    "the Anthropic SDK is not installed: pip install anthropic"
                ) from exc
            credentials = {
                key: value
                for key, value in (("api_key", api_key), ("auth_token", auth_token))
                if value
            }
            client = anthropic.Anthropic(timeout=timeout, max_retries=max_retries, **credentials)
        self._client = client
        self._model = model
        self._effort = effort
        self._max_tokens = max_tokens

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model

    def generate(
        self, system: str, messages: Sequence[ChatMessage], schema: type[T]
    ) -> LLMResult[T]:
        try:
            response = self._client.beta.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                output_config={
                    "effort": self._effort,
                    "format": {"type": "json_schema", "schema": json_schema(schema)},
                },
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
        except Exception as exc:
            translated = _translate(exc)
            if translated is exc:
                raise  # not an SDK error: a bug, keep its traceback
            raise translated from exc
        usage = Usage(response.usage.input_tokens, response.usage.output_tokens)
        cost = _cost(response.model, usage)
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None)
            raise LLMRefusal(
                f"Claude declined the request (category: {category})", usage=usage, cost_usd=cost
            )
        if response.stop_reason == "max_tokens":
            raise LLMOutputError(
                f"reply cut off at max_tokens={self._max_tokens}", usage=usage, cost_usd=cost
            )
        raw = next((b.text for b in response.content if b.type == "text"), "")
        try:
            parsed = parse_reply(raw, schema)
        except LLMOutputError as exc:
            raise LLMOutputError(str(exc), usage=usage, cost_usd=cost) from exc
        return LLMResult(parsed, raw, usage, self.name, response.model, cost)


def has_anthropic_credentials(
    environ: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    run: Callable[..., Any] = subprocess.run,
) -> bool:
    """ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, or a profile from `ant auth login`."""
    env = os.environ if environ is None else environ
    if env.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    ant = which("ant")
    if ant is None:
        return False
    try:
        status = run([ant, "auth", "status"], capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return bool(status.returncode == 0)


def _cost(model: str, usage: Usage) -> float | None:
    if model not in PRICES_PER_MTOK:
        return None
    price_in, price_out = PRICES_PER_MTOK[model]
    return (usage.input_tokens * price_in + usage.output_tokens * price_out) / 1_000_000


def _translate(exc: Exception) -> Exception:
    """SDK errors become LLMError/LLMUnavailable; anything else (a bug) passes through."""
    try:
        import anthropic
    except ImportError:
        return exc
    if isinstance(exc, anthropic.APITimeoutError):  # a connection error, but not "unusable"
        return LLMError(f"Anthropic API timed out: {exc}")
    unavailable = (
        anthropic.APIConnectionError,
        anthropic.AuthenticationError,
        anthropic.PermissionDeniedError,
    )
    if isinstance(exc, unavailable):
        return LLMUnavailable(f"Anthropic API not usable: {exc}")
    if isinstance(exc, anthropic.APIError):
        return LLMError(f"Anthropic API error: {exc}")
    return exc
