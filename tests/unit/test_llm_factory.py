from collections.abc import Mapping
from typing import Any

import pytest

from finhak.llm.base import LLMUnavailable
from finhak.llm.factory import choose_provider

pytestmark = pytest.mark.unit


class Named:
    def __init__(self, name: str, env: Mapping[str, str]) -> None:
        self.name = name
        self.env = dict(env)


def _choose(environ: dict[str, str], credentials: bool = True, sdk: bool = True) -> Any:
    def make_anthropic(env: Mapping[str, str]) -> Named:
        if not sdk:
            raise LLMUnavailable("the Anthropic SDK is not installed")
        return Named("anthropic", env)

    def make_gemini(env: Mapping[str, str]) -> Named:
        if not env.get("GEMINI_API_KEY"):
            raise LLMUnavailable("GEMINI_API_KEY is not set")
        return Named("gemini", env)

    return choose_provider(
        environ,
        has_credentials=lambda env: credentials,
        make_anthropic=make_anthropic,  # type: ignore[arg-type]
        make_ollama=lambda env: Named("ollama", env),  # type: ignore[arg-type]
        make_gemini=make_gemini,  # type: ignore[arg-type]
    )


def test_ollama_is_the_default() -> None:
    choice = _choose({})

    assert choice.provider.name == "ollama"
    assert choice.notice is None


def test_anthropic_is_used_when_asked_for_and_credentials_exist() -> None:
    choice = _choose({"LLM_PROVIDER": "Anthropic"})

    assert choice.provider.name == "anthropic"
    assert choice.notice is None


def test_missing_credentials_fall_back_to_ollama_and_say_so(
    caplog: pytest.LogCaptureFixture,
) -> None:
    choice = _choose({"LLM_PROVIDER": "anthropic"}, credentials=False)

    assert choice.provider.name == "ollama"
    assert choice.notice is not None and "Ollama" in choice.notice
    assert "credentials" in choice.notice
    assert choice.notice in caplog.text


def test_a_missing_sdk_also_falls_back() -> None:
    choice = _choose({"LLM_PROVIDER": "anthropic"}, sdk=False)

    assert choice.provider.name == "ollama"
    assert choice.notice is not None and "SDK" in choice.notice


def test_an_unknown_provider_is_an_error() -> None:
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        _choose({"LLM_PROVIDER": "openai"})


def test_settings_reach_the_provider_factories() -> None:
    choice = _choose({"OLLAMA_MODEL": "qwen3:14b", "OLLAMA_BASE_URL": "http://gpu:11434"})

    assert choice.provider.env["OLLAMA_MODEL"] == "qwen3:14b"


def test_ollama_thinks_unless_switched_off() -> None:
    from finhak.llm.factory import make_ollama

    # decided after the smoke runs: 10 of 14 answers right with thinking, 4 of 12 without
    assert make_ollama({}).think is True  # type: ignore[attr-defined]
    assert make_ollama({"OLLAMA_THINK": ""}).think is True  # type: ignore[attr-defined]
    assert make_ollama({"OLLAMA_THINK": "0"}).think is False  # type: ignore[attr-defined]
    assert make_ollama({"OLLAMA_THINK": "1"}).think is True  # type: ignore[attr-defined]


def test_the_context_window_is_8k_unless_set() -> None:
    from finhak.llm.factory import make_ollama
    from finhak.llm.ollama import DEFAULT_NUM_CTX

    assert make_ollama({}).num_ctx == DEFAULT_NUM_CTX == 8192  # type: ignore[attr-defined]
    assert make_ollama({"OLLAMA_NUM_CTX": "4096"}).num_ctx == 4096  # type: ignore[attr-defined]


def test_an_unknown_ollama_think_value_is_an_error() -> None:
    from finhak.llm.factory import make_ollama

    with pytest.raises(ValueError, match="OLLAMA_THINK"):
        make_ollama({"OLLAMA_THINK": "ture"})
    assert make_ollama({"OLLAMA_THINK": "false"}).think is False  # type: ignore[attr-defined]


def test_gemini_is_used_with_a_key_and_falls_back_to_ollama_without_one() -> None:
    with_key = _choose({"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "k"})
    without = _choose({"LLM_PROVIDER": "gemini"})

    assert (with_key.provider.name, with_key.notice) == ("gemini", None)
    assert without.provider.name == "ollama"
    assert "GEMINI_API_KEY" in without.notice


def test_make_gemini_reads_the_key_model_and_rate_from_the_settings() -> None:
    from finhak.llm.factory import make_gemini
    from finhak.llm.gemini import DEFAULT_MODEL

    provider = make_gemini({"GEMINI_API_KEY": "k", "GEMINI_RPM": "12"})

    assert provider.model == DEFAULT_MODEL
    assert provider.min_interval == 5.0  # type: ignore[attr-defined]
    with pytest.raises(LLMUnavailable, match="GEMINI_API_KEY"):
        make_gemini({})
