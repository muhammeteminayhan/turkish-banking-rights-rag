"""Question → passages → model → verified, rendered answer.

The model gets one retry: the verification errors (or "invalid JSON") go back to it. An
answer whose citations or numbers still fail is withheld: the user sees UNVERIFIED_MESSAGE,
never an unchecked citation. A refusal by the model is not retried. The disclaimer is
added here, not by the model. Tokens and cost include failed attempts.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, Protocol

from finhak.generation.prompts import (
    INVALID_OUTPUT_RETRY,
    SYSTEM_PROMPT,
    build_prompt,
    retry_message,
)
from finhak.generation.render import DISCLAIMER, RenderedCitation, render_citation
from finhak.generation.schema import AnswerOut
from finhak.generation.verify import verify_answer
from finhak.llm.base import ChatMessage, LLMOutputError, LLMProvider, LLMRefusal, Usage
from finhak.parsing.chunker import Chunk
from finhak.retrieval.hybrid import SearchConfig, SearchOutcome

MAX_ATTEMPTS = 2
DEFAULT_PASSAGES = 8
DEFAULT_CONFIG = "full"

OUT_OF_SCOPE_MESSAGE = (
    "Bu soru, sistemdeki mevzuat metinlerinden cevaplanamıyor. Sistem bankacılık ve tüketici "
    "mevzuatından seçilmiş kanun, yönetmelik, tebliğ ve talimatları kapsıyor."
)
UNVERIFIED_MESSAGE = (
    "Bu soru için doğrulanabilir bir cevap üretilemedi: modelin verdiği atıflar kaynak "
    "metinlerle eşleşmedi. Soruyu farklı ifade etmeyi veya ilgili maddeyi belirtmeyi deneyin."
)
NO_SOURCES_MESSAGE = "Bu soruyla ilgili bir mevzuat metni bulunamadı."

AnswerStatus = Literal["answered", "out_of_scope", "unverified", "no_sources"]


class Searches(Protocol):
    def search(self, query: str, config: SearchConfig | str, limit: int = ...) -> SearchOutcome: ...


@dataclass(frozen=True)
class AnswerResult:
    status: AnswerStatus
    answer: str
    citations: tuple[RenderedCitation, ...]
    false_premise: bool
    confidence: str | None
    notes: tuple[str, ...]  # e.g. a cited article that is not in the corpus
    attempts: int
    verification_errors: tuple[str, ...]  # of the last failed attempt
    retrieved: tuple[str, ...]  # chunk ids shown to the model
    usage: Usage
    cost_usd: float | None
    provider: str
    model: str
    latency_ms: float
    top_score: float | None = None  # the best retrieval score (reranker scale with rerank)
    # The last answer that failed verification. For evaluation only: never rendered or
    # shown to a user (they get UNVERIFIED_MESSAGE).
    withheld_draft: str = ""
    disclaimer: str = DISCLAIMER


@dataclass
class _Attempts:
    model: str
    parsed: AnswerOut | None = None
    cited: dict[str, Chunk] = field(default_factory=dict)
    quotes: tuple[str, ...] = ()
    draft: str = ""  # the last answer that failed verification
    attempts: int = 0
    errors: tuple[str, ...] = ()
    usage: Usage = field(default_factory=Usage)
    cost: float = 0.0
    cost_known: bool = True

    def spend(self, usage: Usage, cost: float | None) -> None:
        self.usage = self.usage + usage
        self.cost_known = self.cost_known and cost is not None
        self.cost += cost or 0.0

    @property
    def cost_usd(self) -> float | None:
        return round(self.cost, 6) if self.cost_known else None


def answer_question(
    question: str,
    retriever: Searches,
    provider: LLMProvider,
    config: SearchConfig | str = DEFAULT_CONFIG,
    limit: int = DEFAULT_PASSAGES,
    clock: Callable[[], float] = time.perf_counter,
) -> AnswerResult:
    started = clock()
    outcome = retriever.search(question, config, limit=limit)
    prompt, shown = build_prompt(
        question, [r.chunk for r in outcome.results], outcome.unmatched_refs
    )
    notes = tuple(f"Sorudaki {ref.label} kaynaklarda bulunamadı." for ref in outcome.unmatched_refs)

    def result(status: AnswerStatus, answer: str, run: _Attempts) -> AnswerResult:
        parsed = run.parsed
        return AnswerResult(
            status=status,
            answer=answer,
            citations=_rendered(run) if status == "answered" else (),
            false_premise=bool(parsed and parsed.false_premise),
            confidence=parsed.confidence if parsed else None,
            notes=notes,
            attempts=run.attempts,
            verification_errors=run.errors,
            retrieved=tuple(chunk.id for chunk in shown),
            usage=run.usage,
            cost_usd=run.cost_usd,
            provider=provider.name,
            model=run.model,
            latency_ms=round((clock() - started) * 1000, 1),
            top_score=outcome.results[0].score if outcome.results else None,
            withheld_draft=run.draft if status == "unverified" else "",
        )

    if not shown:
        return result("no_sources", NO_SOURCES_MESSAGE, _Attempts(provider.model))
    run = _generate(provider, prompt, question, shown)
    if run.parsed is None:
        return result("unverified", UNVERIFIED_MESSAGE, run)
    if run.parsed.out_of_scope:
        return result("out_of_scope", OUT_OF_SCOPE_MESSAGE, run)
    return result("answered", run.parsed.answer, run)


def _generate(provider: LLMProvider, prompt: str, question: str, shown: list[Chunk]) -> _Attempts:
    run = _Attempts(provider.model)
    messages = [ChatMessage("user", prompt)]
    for attempt in range(1, MAX_ATTEMPTS + 1):
        run.attempts = attempt
        try:
            reply = provider.generate(SYSTEM_PROMPT, messages, AnswerOut)
        except LLMRefusal as exc:
            run.spend(exc.usage, exc.cost_usd)
            run.errors = (f"model cevap vermeyi reddetti: {exc}",)
            return run
        except LLMOutputError as exc:
            run.spend(exc.usage, exc.cost_usd)
            run.errors = (f"geçersiz çıktı (şemaya uymayan veya kesilmiş JSON): {str(exc)[:160]}",)
            messages = [*messages, ChatMessage("user", INVALID_OUTPUT_RETRY)]
            continue
        run.spend(reply.usage, reply.cost_usd)
        run.model = reply.model
        report = verify_answer(reply.parsed, shown, question=question)
        if report.ok:
            run.parsed = reply.parsed
            run.cited = {chunk.id: chunk for chunk in report.cited_chunks}
            run.quotes = report.quotes
            run.errors = ()
            return run
        run.errors = tuple(error.message for error in report.errors)
        run.draft = reply.parsed.answer
        messages = [
            *messages,
            ChatMessage("assistant", reply.raw),
            ChatMessage("user", retry_message(report.errors)),
        ]
    return run


def _rendered(run: _Attempts) -> tuple[RenderedCitation, ...]:
    if run.parsed is None:
        return ()
    return tuple(
        render_citation(run.cited[citation.chunk_id], quote)
        for citation, quote in zip(run.parsed.citations, run.quotes, strict=True)
    )
