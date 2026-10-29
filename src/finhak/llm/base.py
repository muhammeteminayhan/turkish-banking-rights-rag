"""The interface every language model provider implements, and its errors."""

import json
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Generic, Literal, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

Role = Literal["user", "assistant"]
T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            self.input_tokens + other.input_tokens, self.output_tokens + other.output_tokens
        )


class LLMError(RuntimeError):
    """The provider failed to produce an answer. A reply that arrived but was unusable
    still cost tokens: `usage` and `cost_usd` say how many (None: price unknown)."""

    def __init__(
        self, message: str, usage: Usage | None = None, cost_usd: float | None = 0.0
    ) -> None:
        super().__init__(message)
        self.usage = usage or Usage()
        self.cost_usd = cost_usd


class LLMUnavailable(LLMError):
    """The provider cannot be used: not reachable, not installed or no credentials."""


class LLMRateLimited(LLMError):
    """A quota or rate limit was still hit after waiting: try again later (a free tier's
    daily cap, for example)."""


class LLMOutputError(LLMError):
    """The reply is not valid JSON for the schema, was cut off, or filled the context."""


class LLMRefusal(LLMError):
    """The model declined the request."""


@dataclass(frozen=True)
class LLMResult(Generic[T]):
    parsed: T
    raw: str  # the JSON text as returned, sent back on a retry
    usage: Usage
    provider: str
    model: str  # the model that answered (may be a fallback model)
    cost_usd: float | None  # None when the price of `model` is not known


class LLMProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def model(self) -> str: ...

    def generate(
        self, system: str, messages: Sequence[ChatMessage], schema: type[T]
    ) -> LLMResult[T]: ...


def json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """The model's JSON schema as one self-contained object ($defs inlined).

    Models should set extra="forbid" and give every field without a default, so that each
    object has additionalProperties false and lists all properties as required.
    """
    schema = model.model_json_schema()
    definitions = schema.pop("$defs", {})

    def inline(node: Any) -> Any:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                return inline(deepcopy(definitions[ref.removeprefix("#/$defs/")]))
            return {key: inline(value) for key, value in node.items()}
        if isinstance(node, list):
            return [inline(item) for item in node]
        return node

    result: dict[str, Any] = inline(schema)
    return result


def parse_reply(raw: str, schema: type[T]) -> T:
    try:
        return schema.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise LLMOutputError(f"reply does not match {schema.__name__}: {exc}") from exc
