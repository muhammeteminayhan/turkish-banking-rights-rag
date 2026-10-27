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

    return choose_provider(
        environ,
        has_credentials=lambda env: credentials,
        make_anthropic=make_anthropic,  # type: ignore[arg-type]
        make_ollama=lambda env: Named("ollama", env),  # type: ignore[arg-type]
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
