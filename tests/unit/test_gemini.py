import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from pydantic import BaseModel

from finhak.llm.base import (
    ChatMessage,
    LLMError,
    LLMOutputError,
    LLMRateLimited,
    LLMRefusal,
    LLMUnavailable,
)
from finhak.llm.gemini import DEFAULT_MODEL, GeminiProvider

pytestmark = pytest.mark.unit

MESSAGES = [ChatMessage("user", "soru")]


class Out(BaseModel):
    text: str


def _reply(text: str = '{"text": "merhaba"}', finish: str = "STOP", **extra: Any) -> dict[str, Any]:
    parts = [*extra.pop("before", []), {"text": text}]
    return {
        "candidates": [{"content": {"role": "model", "parts": parts}, "finishReason": finish}],
        "usageMetadata": {"promptTokenCount": 120, "candidatesTokenCount": 30,
                          "thoughtsTokenCount": 50},
        "modelVersion": DEFAULT_MODEL,
        **extra,
    }  # fmt: skip


def _error(code: int, status: str, message: str, **detail: Any) -> httpx.Response:
    details = [{"@type": "type.googleapis.com/google.rpc.RetryInfo", **detail}] if detail else []
    body = {"error": {"code": code, "status": status, "message": message, "details": details}}
    return httpx.Response(code, json=body)


class Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def _provider(
    handler: Callable[[httpx.Request], httpx.Response], clock: Clock | None = None, **kw: Any
) -> GeminiProvider:
    clock = clock or Clock()
    return GeminiProvider(api_key="test-key", transport=httpx.MockTransport(handler),
                          clock=clock, sleep=clock.sleep, **kw)  # fmt: skip


def test_the_request_sends_the_schema_and_the_key_in_a_header() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_reply())

    messages = [
        ChatMessage("user", "soru"),
        ChatMessage("assistant", "x"),
        ChatMessage("user", "y"),
    ]
    result = _provider(handler).generate("sistem", messages, Out)

    request = seen[0]
    assert request.url.path.endswith(f"/models/{DEFAULT_MODEL}:generateContent")
    assert request.headers["x-goog-api-key"] == "test-key"
    assert "test-key" not in str(request.url)  # never in a URL that may be logged
    body = json.loads(request.content)
    assert body["systemInstruction"] == {"parts": [{"text": "sistem"}]}
    assert [c["role"] for c in body["contents"]] == ["user", "model", "user"]
    config = body["generationConfig"]
    assert config["responseMimeType"] == "application/json"
    assert config["responseJsonSchema"]["properties"]["text"]["type"] == "string"
    assert result.parsed.text == "merhaba"
    assert (result.usage.input_tokens, result.usage.output_tokens) == (120, 80)  # + thoughts
    assert result.cost_usd is None  # free only if the key's project has no billing account


def test_thought_parts_are_not_part_of_the_answer() -> None:
    reply = _reply(before=[{"text": "önce düşüneyim", "thought": True}])

    result = _provider(lambda r: httpx.Response(200, json=reply)).generate("s", MESSAGES, Out)

    assert result.raw == '{"text": "merhaba"}'


def test_a_cut_off_reply_is_an_output_error_with_its_tokens() -> None:
    reply = _reply('{"text": "yar', finish="MAX_TOKENS")

    with pytest.raises(LLMOutputError) as caught:
        _provider(lambda r: httpx.Response(200, json=reply)).generate("s", MESSAGES, Out)
    assert caught.value.usage.input_tokens == 120


@pytest.mark.parametrize(
    "reply",
    [
        _reply("", finish="SAFETY"),
        {"promptFeedback": {"blockReason": "PROHIBITED_CONTENT"}, "usageMetadata": {}},
    ],
)
def test_a_blocked_reply_is_a_refusal(reply: dict[str, Any]) -> None:
    with pytest.raises(LLMRefusal):
        _provider(lambda r: httpx.Response(200, json=reply)).generate("s", MESSAGES, Out)


def test_a_rate_limit_is_waited_out_with_the_delay_the_api_asks_for() -> None:
    replies = [_error(429, "RESOURCE_EXHAUSTED", "slow down", retryDelay="7s"),
               httpx.Response(200, json=_reply())]  # fmt: skip
    clock = Clock()

    result = _provider(lambda r: replies.pop(0), clock).generate("s", MESSAGES, Out)

    assert result.parsed.text == "merhaba"
    assert 7.0 in clock.slept


def test_a_quota_that_stays_used_up_stops_with_rate_limited() -> None:
    clock = Clock()
    provider = _provider(lambda r: _error(429, "RESOURCE_EXHAUSTED", "quota", retryDelay="1s"),
                         clock, max_retries=2)  # fmt: skip

    with pytest.raises(LLMRateLimited, match="quota"):
        provider.generate("s", MESSAGES, Out)
    assert clock.slept.count(1.0) == 2


def test_a_daily_quota_is_not_waited_for() -> None:
    clock = Clock()
    daily = _error(429, "RESOURCE_EXHAUSTED", "Quota exceeded for GenerateRequestsPerDay")

    with pytest.raises(LLMRateLimited):
        _provider(lambda r: daily, clock).generate("s", MESSAGES, Out)
    assert clock.slept == []


@pytest.mark.parametrize(
    ("code", "status", "kind", "words"),
    [
        (403, "PERMISSION_DENIED", LLMUnavailable, "GEMINI_API_KEY"),
        (400, "INVALID_ARGUMENT", LLMUnavailable, "GEMINI_API_KEY"),  # "API key not valid"
        (404, "NOT_FOUND", LLMUnavailable, "model"),
    ],
)
def test_key_and_model_problems_say_what_to_fix(
    code: int, status: str, kind: type[Exception], words: str
) -> None:
    response = _error(code, status, "API key not valid" if code == 400 else "nope")

    with pytest.raises(kind, match=words):
        _provider(lambda r: response).generate("s", MESSAGES, Out)


def test_requests_are_spaced_to_the_rate_limit() -> None:
    clock = Clock()
    provider = _provider(lambda r: httpx.Response(200, json=_reply()), clock, rpm=10)

    provider.generate("s", MESSAGES, Out)
    clock.now += 1.0
    provider.generate("s", MESSAGES, Out)

    assert clock.slept == [5.0]  # 10 per minute: 6 s apart, 1 s had passed


def test_the_key_never_appears_in_an_error() -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"Illegal header value {request.headers['x-goog-api-key']}")

    provider = GeminiProvider(api_key=" secret-key-123\r\n", transport=httpx.MockTransport(broken))

    with pytest.raises(LLMUnavailable) as caught:
        provider.generate("s", MESSAGES, Out)
    assert "secret-key-123" not in str(caught.value)


def test_the_key_is_stripped_of_whitespace() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["x-goog-api-key"])
        return httpx.Response(200, json=_reply())

    _provider(handler).generate("s", MESSAGES, Out)
    GeminiProvider(api_key=" k \n", transport=httpx.MockTransport(handler)).generate(
        "s", MESSAGES, Out
    )

    assert seen == ["test-key", "k"]


def test_a_busy_server_is_retried() -> None:
    replies = [_error(503, "UNAVAILABLE", "high demand"), httpx.Response(200, json=_reply())]

    result = _provider(lambda r: replies.pop(0)).generate("s", MESSAGES, Out)

    assert result.parsed.text == "merhaba"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="<html>proxy error</html>"),
        httpx.Response(500, json=["not", "a", "dict"]),
        httpx.Response(400, json={"error": {"code": 400, "message": "", "status": "X"}}),
    ],
)
def test_malformed_responses_are_llm_errors(response: httpx.Response) -> None:
    with pytest.raises(LLMError) as caught:
        _provider(lambda r: response, max_retries=0).generate("s", MESSAGES, Out)
    assert str(caught.value).strip()  # never an empty message


@pytest.mark.parametrize("settings", [{"rpm": 0}, {"max_retries": -1}])
def test_impossible_settings_are_rejected(settings: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        GeminiProvider(api_key="k", **settings)  # type: ignore[arg-type]
