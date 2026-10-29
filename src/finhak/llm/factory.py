"""Pick the provider from LLM_PROVIDER; fall back to Ollama, loudly, when Anthropic can't run.

Settings come from the environment, then .env (finhak.config): LLM_PROVIDER (ollama |
anthropic | gemini), ANTHROPIC_MODEL, OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_NUM_CTX (8192),
OLLAMA_THINK (on unless 0/false/no/off), GEMINI_API_KEY, GEMINI_MODEL, GEMINI_RPM.
"""

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from finhak.config import merged_env
from finhak.llm import anthropic_provider, gemini, ollama
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
        # On by default: in the M4 smoke runs 10 of 14 answers were right with thinking,
        # 4 of 12 without (docs/milestones/M4.md).
        think=_flag(env, "OLLAMA_THINK", default=True),
    )


_ON, _OFF = ("1", "true", "yes", "on"), ("0", "false", "no", "off")


def _flag(env: Mapping[str, str], name: str, default: bool) -> bool:
    value = (env.get(name) or "").strip().lower()
    if not value:
        return default
    if value not in _ON + _OFF:  # a typo must not silently pick one
        raise ValueError(f"{name} must be one of {_ON} or {_OFF}, not {value!r}")
    return value in _ON


def make_anthropic(env: Mapping[str, str]) -> LLMProvider:
    model = env.get("ANTHROPIC_MODEL") or anthropic_provider.DEFAULT_MODEL
    return anthropic_provider.AnthropicProvider(
        model=model,
        api_key=env.get("ANTHROPIC_API_KEY") or None,
        auth_token=env.get("ANTHROPIC_AUTH_TOKEN") or None,
    )


def make_gemini(env: Mapping[str, str]) -> LLMProvider:
    """Gemini's free tier (a key from a Google project without billing): costs nothing."""
    rpm = env.get("GEMINI_RPM")
    return gemini.GeminiProvider(
        api_key=env.get("GEMINI_API_KEY") or "",
        model=env.get("GEMINI_MODEL") or gemini.DEFAULT_MODEL,
        rpm=float(rpm) if rpm else gemini.DEFAULT_RPM,
    )


def choose_provider(
    environ: Mapping[str, str] | None = None,
    has_credentials: Callable[[Mapping[str, str]], bool] = (
        anthropic_provider.has_anthropic_credentials
    ),
    make_anthropic: ProviderFactory = make_anthropic,
    make_ollama: ProviderFactory = make_ollama,
    make_gemini: ProviderFactory = make_gemini,
) -> ProviderChoice:
    env = merged_env() if environ is None else environ
    wanted = (env.get("LLM_PROVIDER") or "ollama").strip().lower()
    if wanted == "ollama":
        return ProviderChoice(make_ollama(env), None)
    if wanted == "gemini":
        try:
            return ProviderChoice(make_gemini(env), None)
        except LLMUnavailable as exc:
            notice = f"LLM_PROVIDER=gemini but Gemini cannot be used ({exc}); using Ollama."
            logger.warning("%s", notice)
            return ProviderChoice(make_ollama(env), notice)
    if wanted != "anthropic":
        raise ValueError(f"LLM_PROVIDER must be ollama, anthropic or gemini, got {wanted!r}")

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
