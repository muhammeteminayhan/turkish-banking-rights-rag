"""Google's Gemini API (generateContent, JSON-schema output) over HTTPS, for its free tier.

An optional judge or comparison model that costs nothing as long as the API key belongs to a
Google project without a billing account; with billing linked the same calls are paid. On
the free tier Google may use the content to improve its products (pricing page, 2026-10-29):
the corpus is public law and the questions are made up. The per-minute and per-day limits
are shown in AI Studio, not in the docs; a used-up quota raises LLMRateLimited so a run can
stop and continue later.

The request shape follows the API reference; it was not tried against the live API when
written (no key yet), so the first real call is its check.
"""

import re
import time
from collections.abc import Callable, Sequence
from typing import Any

import httpx

from finhak.llm.base import (
    ChatMessage,
    LLMError,
    LLMOutputError,
    LLMRateLimited,
    LLMRefusal,
    LLMResult,
    LLMUnavailable,
    T,
    Usage,
    json_schema,
    parse_reply,
)

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-3.8-flash"  # on the free tier per the pricing page (2026-10-29)
DEFAULT_RPM = 5.0  # well under the free tier's per-minute limits
MAX_OUTPUT_TOKENS = 8192
MAX_RETRIES = 3  # waits on 429/5xx before giving up
MAX_RETRY_DELAY = 120.0  # seconds
_FINISHED = ("STOP", "FINISH_REASON_UNSPECIFIED")
_ROLES = {"user": "user", "assistant": "model"}
_DELAY = re.compile(r"^(\d+(?:\.\d+)?)s$")


class GeminiProvider:
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        rpm: float = DEFAULT_RPM,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 300.0,
        max_retries: int = MAX_RETRIES,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        api_key = api_key.strip()  # a stray CR would make httpx echo the key in an error
        if not api_key:
            raise LLMUnavailable("GEMINI_API_KEY is not set (a free-tier key from AI Studio)")
        if rpm <= 0 or max_retries < 0:
            raise ValueError(f"need rpm > 0 and max_retries >= 0, got {rpm}, {max_retries}")
        self._model = model
        self.min_interval = 60.0 / rpm  # seconds between two requests
        self._max_retries = max_retries
        self._timeout = timeout
        self._clock, self._sleep = clock, sleep
        self._next_at = 0.0
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={"x-goog-api-key": api_key},  # a header, never the URL (logs)
        )

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model

    def generate(
        self, system: str, messages: Sequence[ChatMessage], schema: type[T]
    ) -> LLMResult[T]:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [
                {"role": _ROLES[m.role], "parts": [{"text": m.content}]} for m in messages
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": json_schema(schema),
                "maxOutputTokens": MAX_OUTPUT_TOKENS,
            },
        }
        data = self._post(f"/models/{self._model}:generateContent", body)
        meta = data.get("usageMetadata") or {}
        usage = Usage(
            int(meta.get("promptTokenCount", 0)),
            int(meta.get("candidatesTokenCount", 0)) + int(meta.get("thoughtsTokenCount", 0)),
        )
        raw = _answer_text(data, usage)
        try:
            parsed = parse_reply(raw, schema)
        except LLMOutputError as exc:
            raise LLMOutputError(str(exc), usage=usage, cost_usd=None) from exc
        model = str(data.get("modelVersion") or self._model)
        return LLMResult(parsed, raw, usage, self.name, model, None)  # cost: depends on billing

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(self._max_retries + 1):
            self._pace()
            try:
                response = self._client.post(path, json=body)
            except httpx.TimeoutException as exc:
                raise LLMError(f"Gemini did not answer within {self._timeout:.0f} s") from exc
            except httpx.TransportError as exc:  # its text may hold the request headers
                raise LLMUnavailable(f"Gemini API not reachable ({type(exc).__name__})") from exc
            if response.status_code == 200:
                try:
                    data = response.json()
                except ValueError as exc:
                    raise LLMError("Gemini returned a body that is not JSON") from exc
                if not isinstance(data, dict):
                    raise LLMError("Gemini returned an unexpected body")
                return data
            error = _error(response)
            retryable = response.status_code == 429 or response.status_code >= 500
            if not retryable:
                raise self._fatal(response.status_code, error)
            if response.status_code == 429 and "PerDay" in response.text:
                raise LLMRateLimited(f"Gemini daily quota used up: {error['message']}")
            if attempt == self._max_retries:
                break
            self._sleep(min(_retry_delay(error) or 2.0 * 2**attempt, MAX_RETRY_DELAY))
        if response.status_code == 429:
            raise LLMRateLimited(f"Gemini rate limit or quota: {error['message']}")
        raise LLMError(f"Gemini returned {response.status_code}: {error['message']}")

    def _pace(self) -> None:
        wait = self._next_at - self._clock()
        if wait > 0:
            self._sleep(wait)
        self._next_at = self._clock() + self.min_interval

    def _fatal(self, status: int, error: dict[str, Any]) -> LLMError:
        message = str(error["message"])
        if status in (401, 403) or (status == 400 and "API key" in message):
            return LLMUnavailable(
                f"Gemini rejected the key ({message}): check GEMINI_API_KEY and that its "
                "project may use the Gemini API"
            )
        if status == 404:
            return LLMUnavailable(f"Gemini has no model {self._model!r} ({message})")
        return LLMError(f"Gemini rejected the request ({status}): {message}")


def _answer_text(data: dict[str, Any], usage: Usage) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        reason = (data.get("promptFeedback") or {}).get("blockReason", "no answer")
        raise LLMRefusal(f"Gemini returned no answer ({reason})", usage=usage, cost_usd=None)
    candidate = candidates[0]
    finish = str(candidate.get("finishReason", "STOP"))
    if finish == "MAX_TOKENS":
        raise LLMOutputError(
            f"reply cut off at {MAX_OUTPUT_TOKENS} tokens", usage=usage, cost_usd=None
        )
    if finish not in _FINISHED:  # SAFETY, RECITATION, PROHIBITED_CONTENT, ...
        raise LLMRefusal(f"Gemini stopped the answer ({finish})", usage=usage, cost_usd=None)
    parts = (candidate.get("content") or {}).get("parts") or []
    return "".join(str(p.get("text", "")) for p in parts if not p.get("thought"))


def _error(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        body = None
    error = body.get("error") if isinstance(body, dict) else None
    error = error if isinstance(error, dict) else {}
    return {**error, "message": str(error.get("message") or response.text[:300] or "no message")}


def _retry_delay(error: dict[str, Any]) -> float | None:
    """The delay a google.rpc.RetryInfo detail asks for ("7s"), if there is one."""
    details = error.get("details")
    for detail in details if isinstance(details, list) else []:
        if not isinstance(detail, dict):
            continue
        match = _DELAY.match(str(detail.get("retryDelay", "")))
        if match:
            return float(match.group(1))
    return None
