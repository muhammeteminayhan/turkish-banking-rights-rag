"""Ollama over a mocked HTTP transport; Anthropic with an injected fake client. No network."""

import json
import sys
import types
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, ConfigDict

from finhak.llm.anthropic_provider import (
    FALLBACK_BETA,
    AnthropicProvider,
    has_anthropic_credentials,
)
from finhak.llm.base import (
    ChatMessage,
    LLMError,
    LLMOutputError,
    LLMRefusal,
    LLMUnavailable,
    json_schema,
)
from finhak.llm.ollama import OllamaProvider

pytestmark = pytest.mark.unit


class Inner(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int


class Out(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    items: list[Inner]


GOOD = json.dumps({"text": "merhaba", "items": [{"value": 1}]})
MESSAGES = [ChatMessage("user", "Soru?")]


def test_json_schema_inlines_definitions_and_forbids_extra_keys() -> None:
    schema = json_schema(Out)

    assert "$defs" not in schema
    assert "$ref" not in json.dumps(schema)
    assert schema["additionalProperties"] is False
    assert schema["properties"]["items"]["items"]["additionalProperties"] is False
    assert set(schema["required"]) == {"text", "items"}


# --- Ollama ------------------------------------------------------------------------


def _ollama(handler: Any) -> tuple[OllamaProvider, list[dict[str, Any]]]:
    seen: list[dict[str, Any]] = []

    def record(request: httpx.Request) -> httpx.Response:
        if request.content:
            seen.append(json.loads(request.content))
        response: httpx.Response = handler(request)
        return response

    provider = OllamaProvider(model="qwen3:8b", transport=httpx.MockTransport(record))
    return provider, seen


def _chat_reply(content: str, **extra: Any) -> httpx.Response:
    body = {"message": {"role": "assistant", "content": content}, "prompt_eval_count": 120,
            "eval_count": 30, "done_reason": "stop", **extra}  # fmt: skip
    return httpx.Response(200, json=body)


def test_ollama_sends_schema_no_thinking_and_parses_the_reply() -> None:
    provider, seen = _ollama(lambda request: _chat_reply(GOOD))

    result = provider.generate("Sistem.", MESSAGES, Out)

    assert result.parsed == Out(text="merhaba", items=[Inner(value=1)])
    assert (result.usage.input_tokens, result.usage.output_tokens) == (120, 30)
    assert (result.provider, result.model, result.cost_usd) == ("ollama", "qwen3:8b", 0.0)
    (body,) = seen
    assert body["think"] is False
    assert body["stream"] is False
    assert body["format"] == json_schema(Out)
    # Qwen3's recommended non-thinking sampling (greedy decoding loops), seeded
    assert body["options"]["temperature"] == 0.7
    assert (body["options"]["top_p"], body["options"]["top_k"]) == (0.8, 20)
    assert body["options"]["seed"] == 42
    assert body["messages"] == [
        {"role": "system", "content": "Sistem."},
        {"role": "user", "content": "Soru?"},
    ]


def test_ollama_unreachable_is_reported_as_unavailable() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    provider, _ = _ollama(refuse)

    with pytest.raises(LLMUnavailable, match="ollama serve"):
        provider.generate("s", MESSAGES, Out)


def test_ollama_missing_model_is_reported_as_unavailable() -> None:
    provider, _ = _ollama(lambda r: httpx.Response(404, json={"error": "model not found"}))

    with pytest.raises(LLMUnavailable, match="ollama pull qwen3:8b"):
        provider.generate("s", MESSAGES, Out)


@pytest.mark.parametrize(
    "reply",
    [
        _chat_reply("{not json"),
        _chat_reply(json.dumps({"text": "x"})),  # misses a required field
        _chat_reply(GOOD, done_reason="length"),  # cut off
    ],
)
def test_ollama_bad_output_is_an_output_error(reply: httpx.Response) -> None:
    provider, _ = _ollama(lambda request: reply)

    with pytest.raises(LLMOutputError):
        provider.generate("s", MESSAGES, Out)


def test_ollama_lists_the_pulled_models() -> None:
    tags = {"models": [{"name": "qwen3:8b"}, {"name": "llama3:8b"}]}
    provider, _ = _ollama(lambda request: httpx.Response(200, json=tags))

    assert provider.available_models() == ["qwen3:8b", "llama3:8b"]


# --- Anthropic -----------------------------------------------------------------------


class FakeMessages:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _response(
    text: str = GOOD, stop_reason: str = "end_turn", model: str = "claude-opus-5-5"
) -> Any:
    return types.SimpleNamespace(
        content=[types.SimpleNamespace(type="thinking", thinking=""),
                 types.SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        stop_details=types.SimpleNamespace(category="cyber", explanation="declined"),
        usage=types.SimpleNamespace(input_tokens=1_000_000, output_tokens=100_000),
        model=model,
    )  # fmt: skip


def _anthropic(response: Any) -> tuple[AnthropicProvider, FakeMessages]:
    messages = FakeMessages(response)
    client = types.SimpleNamespace(beta=types.SimpleNamespace(messages=messages))
    return AnthropicProvider(client=client), messages


def test_anthropic_requests_structured_output_with_refusal_fallback() -> None:
    provider, messages = _anthropic(_response())

    result = provider.generate("Sistem.", MESSAGES, Out)

    assert result.parsed.items == [Inner(value=1)]
    (call,) = messages.calls
    assert call["model"] == "claude-opus-5-5"
    assert call["system"] == "Sistem."
    assert call["messages"] == [{"role": "user", "content": "Soru?"}]
    assert call["output_config"]["format"] == {"type": "json_schema", "schema": json_schema(Out)}
    assert call["output_config"]["effort"] == "medium"
    assert call["betas"] == [FALLBACK_BETA]
    assert call["fallbacks"] == "default"
    assert "thinking" not in call and "temperature" not in call


def test_anthropic_cost_uses_the_model_that_answered() -> None:
    provider, _ = _anthropic(_response())

    assert provider.generate("s", MESSAGES, Out).cost_usd == pytest.approx(4.0 + 2.0)

    provider, _ = _anthropic(_response(model="claude-opus-4-8"))  # a fallback model
    assert provider.generate("s", MESSAGES, Out).cost_usd is None


def test_anthropic_refusal_and_truncation_are_errors() -> None:
    provider, _ = _anthropic(_response(stop_reason="refusal"))
    with pytest.raises(LLMRefusal, match="cyber"):
        provider.generate("s", MESSAGES, Out)

    provider, _ = _anthropic(_response(stop_reason="max_tokens"))
    with pytest.raises(LLMOutputError, match="max_tokens"):
        provider.generate("s", MESSAGES, Out)


def test_anthropic_sdk_errors_are_translated(monkeypatch: pytest.MonkeyPatch) -> None:
    sdk = types.ModuleType("anthropic")

    class APIError(Exception):
        pass

    class APIConnectionError(APIError):
        pass

    class AuthenticationError(APIError):
        pass

    class PermissionDeniedError(APIError):
        pass

    class APITimeoutError(APIConnectionError):  # as in the SDK: a kind of connection error
        pass

    sdk.APIError = APIError  # type: ignore[attr-defined]
    sdk.APIConnectionError = APIConnectionError  # type: ignore[attr-defined]
    sdk.AuthenticationError = AuthenticationError  # type: ignore[attr-defined]
    sdk.PermissionDeniedError = PermissionDeniedError  # type: ignore[attr-defined]
    sdk.APITimeoutError = APITimeoutError  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", sdk)

    provider, _ = _anthropic(APIConnectionError("no network"))
    with pytest.raises(LLMUnavailable):
        provider.generate("s", MESSAGES, Out)
    for error, text in ((APIError("overloaded"), "overloaded"), (APITimeoutError("t"), "timed")):
        provider, _ = _anthropic(error)
        with pytest.raises(LLMError, match=text) as caught:
            provider.generate("s", MESSAGES, Out)
        assert not isinstance(caught.value, LLMUnavailable)
    provider, _ = _anthropic(KeyError("a bug"))  # not an SDK error: not translated
    with pytest.raises(KeyError):
        provider.generate("s", MESSAGES, Out)


def test_unusable_replies_still_report_their_tokens_and_cost() -> None:
    provider, _ = _anthropic(_response(stop_reason="max_tokens"))
    with pytest.raises(LLMOutputError) as cut:
        provider.generate("s", MESSAGES, Out)
    assert cut.value.usage.output_tokens == 100_000
    assert cut.value.cost_usd == pytest.approx(6.0)

    provider, _ = _anthropic(_response(text="{not json"))
    with pytest.raises(LLMOutputError) as invalid:
        provider.generate("s", MESSAGES, Out)
    assert invalid.value.usage.input_tokens == 1_000_000


def test_ollama_reports_a_full_context_and_caps_the_reply_length() -> None:
    from finhak.llm.ollama import DEFAULT_NUM_CTX, MAX_OUTPUT

    full = _chat_reply(GOOD, prompt_eval_count=DEFAULT_NUM_CTX - 10, eval_count=10)
    provider, seen = _ollama(lambda request: full)

    with pytest.raises(LLMOutputError, match="num_ctx") as caught:
        provider.generate("s", MESSAGES, Out)
    assert caught.value.usage.input_tokens == DEFAULT_NUM_CTX - 10
    assert seen[0]["options"]["num_predict"] == MAX_OUTPUT


def test_ollama_timeout_is_not_reported_as_not_running() -> None:
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    provider, _ = _ollama(slow)

    with pytest.raises(LLMError, match="did not answer") as caught:
        provider.generate("s", MESSAGES, Out)
    assert not isinstance(caught.value, LLMUnavailable)


def test_the_factory_passes_env_file_credentials_to_the_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from finhak.llm.factory import make_anthropic

    seen: dict[str, Any] = {}
    sdk = types.ModuleType("anthropic")

    def client(**kwargs: Any) -> Any:
        seen.update(kwargs)
        return types.SimpleNamespace(beta=None)

    sdk.Anthropic = client  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", sdk)

    make_anthropic({"ANTHROPIC_API_KEY": "sk-from-dotenv"})

    assert seen["api_key"] == "sk-from-dotenv"
    assert "auth_token" not in seen


def test_anthropic_without_the_sdk_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "anthropic", None)

    with pytest.raises(LLMUnavailable, match="pip install"):
        AnthropicProvider()


@pytest.mark.parametrize(
    ("environ", "ant", "expected"),
    [
        ({"ANTHROPIC_API_KEY": "sk-test"}, None, True),
        ({"ANTHROPIC_AUTH_TOKEN": "tok"}, None, True),
        ({"ANTHROPIC_API_KEY": ""}, None, False),  # empty does not count
        ({}, 0, True),  # `ant auth status` reports a profile
        ({}, 1, False),
    ],
)
def test_credentials_come_from_the_environment_or_an_ant_profile(
    environ: dict[str, str], ant: int | None, expected: bool
) -> None:
    def which(name: str) -> str | None:
        return None if ant is None else "/usr/bin/ant"

    def run(args: list[str], **kwargs: Any) -> Any:
        assert args == ["/usr/bin/ant", "auth", "status"]
        return types.SimpleNamespace(returncode=ant)

    assert has_anthropic_credentials(environ, which=which, run=run) is expected


def test_ollama_thinking_mode_uses_its_own_sampling_and_a_larger_output_budget() -> None:
    reply = _chat_reply(GOOD, message={"role": "assistant", "content": GOOD, "thinking": "…"})
    seen: list[dict[str, Any]] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return reply

    provider = OllamaProvider(think=True, transport=httpx.MockTransport(record))

    result = provider.generate("s", MESSAGES, Out)

    assert result.parsed.text == "merhaba"
    body = seen[0]
    assert body["think"] is True
    assert body["options"]["temperature"] == 0.6
    assert body["options"]["top_p"] == 0.95
    assert body["options"]["num_predict"] > 1024
    assert provider.think is True
    sent = {k: body["options"][k] for k in ("temperature", "top_p", "top_k", "min_p", "seed")}
    assert provider.sampling == sent  # what the eval reports record
