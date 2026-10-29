"""Pick the provider from LLM_PROVIDER; fall back to Ollama, loudly, when Anthropic can't run.

Settings come from the environment, then .env (finhak.config): LLM_PROVIDER (ollama |
anthropic), ANTHROPIC_MODEL, OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_NUM_CTX, OLLAMA_THINK.
"""

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from finhak.config import merged_env
from finhak.llm import anthropic_provider, ollama
from finhak.llm.base import LLMProvider, LLMUnavailable

logger = logging.getLogger("finhak.llm")

ProviderFactory = Callable[[Mapping[str, str]], LLMProvider]


@dataclass(frozen=True)
class ProviderChoice:
    provider: LLMProvider
    notice: str | None  # why the requested provider is not the one in use, if it is not


def make_ollama(env: Mapping[str, str]) -> LLMProvider:
    return ollama.OllamaProvider(
        base_url=env.get("OLLAMA_BASE_URL") or ollama.DEFAULT_BASE_URL,
        model=env.get("OLLAMA_MODEL") or ollama.DEFAULT_MODEL,
        num_ctx=int(env.get("OLLAMA_NUM_CTX") or ollama.DEFAULT_NUM_CTX),
        think=_flag(env, "OLLAMA_THINK"),
    )


_ON, _OFF = ("1", "true", "yes", "on"), ("", "0", "false", "no", "off")


def _flag(env: Mapping[str, str], name: str) -> bool:
    value = (env.get(name) or "").strip().lower()
    if value not in _ON + _OFF:  # a typo must not silently mean "off"
        raise ValueError(f"{name} must be one of {_ON} or {_OFF[1:]}, not {value!r}")
    return value in _ON


def make_anthropic(env: Mapping[str, str]) -> LLMProvider:
    model = env.get("ANTHROPIC_MODEL") or anthropic_provider.DEFAULT_MODEL
    return anthropic_provider.AnthropicProvider(
        model=model,
        api_key=env.get("ANTHROPIC_API_KEY") or None,
        auth_token=env.get("ANTHROPIC_AUTH_TOKEN") or None,
    )


def choose_provider(
    environ: Mapping[str, str] | None = None,
    has_credentials: Callable[[Mapping[str, str]], bool] = (
        anthropic_provider.has_anthropic_credentials
    ),
    make_anthropic: ProviderFactory = make_anthropic,
    make_ollama: ProviderFactory = make_ollama,
) -> ProviderChoice:
    env = merged_env() if environ is None else environ
    wanted = (env.get("LLM_PROVIDER") or "ollama").strip().lower()
    if wanted == "ollama":
        return ProviderChoice(make_ollama(env), None)
    if wanted != "anthropic":
        raise ValueError(f"LLM_PROVIDER must be ollama or anthropic, got {wanted!r}")

    if not has_credentials(env):
        notice = (
            "LLM_PROVIDER=anthropic but no Anthropic credentials were found "
            "(ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or `ant auth login`); using Ollama."
        )
    else:
        try:
            return ProviderChoice(make_anthropic(env), None)
        except LLMUnavailable as exc:
            notice = f"Anthropic cannot be used ({exc}; the SDK or its setup); using Ollama."
    logger.warning("%s", notice)
    return ProviderChoice(make_ollama(env), notice)
