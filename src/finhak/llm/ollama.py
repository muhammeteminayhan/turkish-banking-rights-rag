"""Ollama's local /api/chat with a JSON-schema `format` (structured output)."""

from collections.abc import Sequence
from typing import Any

import httpx

from finhak.llm.base import (
    ChatMessage,
    LLMError,
    LLMResult,
    LLMUnavailable,
    T,
    Usage,
    json_schema,
    parse_reply,
)
from finhak.llm.base import LLMOutputError as _OutputError

DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3:8b"
# 8 passages plus the instructions fit in 8k tokens; a larger window costs VRAM that the
# embedder and the reranker share on an 8 GB GPU.
DEFAULT_NUM_CTX = 8192
MAX_OUTPUT = 1024  # tokens; an answer with a few quotes needs a few hundred
FULL_CONTEXT = 0.95  # share of num_ctx at which the prompt may have been cut


class OllamaProvider:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: float = 300.0,
        num_ctx: int = DEFAULT_NUM_CTX,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._num_ctx = num_ctx
        self._timeout = timeout
        self._client = httpx.Client(base_url=self._base_url, timeout=timeout, transport=transport)

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    def generate(
        self, system: str, messages: Sequence[ChatMessage], schema: type[T]
    ) -> LLMResult[T]:
        body = {
            "model": self._model,
            "stream": False,
            "think": False,  # Qwen3 would otherwise reason before the JSON
            "format": json_schema(schema),
            # num_predict: a greedy (temperature 0) loop would otherwise run to the end of
            # the context window.
            "options": {"temperature": 0, "num_ctx": self._num_ctx, "num_predict": MAX_OUTPUT},
            "messages": [
                {"role": "system", "content": system},
                *({"role": m.role, "content": m.content} for m in messages),
            ],
        }
        data = self._post("/api/chat", body)
        usage = Usage(int(data.get("prompt_eval_count", 0)), int(data.get("eval_count", 0)))
        if data.get("done_reason") == "length":
            raise _OutputError(f"reply cut off at {MAX_OUTPUT} tokens", usage=usage)
        # Ollama silently drops the start of a prompt that does not fit; a context this full
        # means the model may not have seen every passage or rule.
        if usage.input_tokens + usage.output_tokens >= FULL_CONTEXT * self._num_ctx:
            raise _OutputError(
                f"prompt and reply used {usage.input_tokens + usage.output_tokens} of "
                f"num_ctx={self._num_ctx} tokens; the prompt may have been cut",
                usage=usage,
            )
        raw = str(data.get("message", {}).get("content", ""))
        try:
            parsed = parse_reply(raw, schema)
        except _OutputError as exc:
            raise _OutputError(str(exc), usage=usage) from exc
        return LLMResult(parsed, raw, usage, self.name, self._model, 0.0)

    def available_models(self) -> list[str]:
        try:
            response = self._client.get("/api/tags")
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMError(f"Ollama did not answer within {self._timeout:.0f} s") from exc
        except httpx.TransportError as exc:
            raise self._unreachable(exc) from exc
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"Ollama returned {exc.response.status_code} for /api/tags") from exc
        return [str(m["name"]) for m in response.json().get("models", [])]

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.post(path, json=body)
        except httpx.TimeoutException as exc:  # a TransportError, but not "not running"
            raise LLMError(f"Ollama did not answer within {self._timeout:.0f} s") from exc
        except httpx.TransportError as exc:
            raise self._unreachable(exc) from exc
        if response.status_code == 404:
            raise LLMUnavailable(
                f"Ollama has no model {self._model!r}: run `ollama pull {self._model}`"
            )
        if response.status_code != 200:
            raise LLMError(f"Ollama returned {response.status_code}: {response.text[:300]}")
        data: dict[str, Any] = response.json()
        return data

    def _unreachable(self, exc: Exception) -> LLMUnavailable:
        return LLMUnavailable(
            f"Ollama not reachable at {self._base_url} ({exc}); is it installed and "
            "running (`ollama serve`)?"
        )
