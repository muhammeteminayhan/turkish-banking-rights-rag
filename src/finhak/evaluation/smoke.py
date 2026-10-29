"""The M4 smoke run: a handful of golden questions answered end to end.

It is not the M5 evaluation. It shows that the pipeline runs, how often answers pass
citation verification, and whether a verified answer cites the expected article.
"""

import logging
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import psycopg

from finhak.evaluation.golden import GoldenQuestion
from finhak.evaluation.retrieval import madde_key
from finhak.generation.cli import render_answer
from finhak.generation.pipeline import AnswerResult
from finhak.llm.base import LLMError

logger = logging.getLogger("finhak.smoke")

# When the model fails on this many questions in a row (timeouts, Ollama gone), the rest
# would fail the same way: a run on a GPU with too little free memory spent 98 minutes
# on 12 timeouts out of 20.
MAX_ERRORS_IN_A_ROW = 2


@dataclass(frozen=True)
class SmokeRow:
    question_id: str
    category: str
    question: str
    status: str
    attempts: int
    cited: tuple[str, ...]
    expected_article_cited: bool | None  # None for out-of-scope questions
    verification_errors: tuple[str, ...]
    latency_ms: float
    answer: str
    retrieved_expected: bool | None = None  # retrieval found it (else generation can't)
    top_score: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = 0.0
    rendered: str = ""  # the answer as the user sees it (citations, dates, disclaimer)


class SmokeStopped(RuntimeError):
    """The model failed on several questions in a row; `rows` holds those run so far."""

    def __init__(self, rows: list[SmokeRow], reason: str) -> None:
        super().__init__(reason)
        self.rows = rows


def load_smoke_ids(path: Path) -> list[str]:
    ids = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.split("#", 1)[0].strip()
        if value:
            ids.append(value)
    return ids


def run_smoke(
    questions: Sequence[GoldenQuestion],
    ask: Callable[[str], AnswerResult],
    max_errors_in_a_row: int = MAX_ERRORS_IN_A_ROW,
) -> list[SmokeRow]:
    """One row per question; raises SmokeStopped once the model keeps failing."""
    rows: list[SmokeRow] = []
    errors_in_a_row = 0
    for number, question in enumerate(questions, start=1):
        start = time.perf_counter()
        try:
            rows.append(_answered_row(question, ask(question.question)))
            errors_in_a_row = 0
        except LLMError as exc:  # one failing question does not lose the run
            rows.append(_error_row(question, exc, (time.perf_counter() - start) * 1000))
            errors_in_a_row += 1
        except (KeyboardInterrupt, psycopg.Error) as exc:  # keep what ran for the report
            raise SmokeStopped(
                rows, f"interrupted at question {number} ({type(exc).__name__}: {exc})"
            ) from exc
        _log_progress(number, len(questions), rows[-1])
        if errors_in_a_row >= max_errors_in_a_row and number < len(questions):
            raise SmokeStopped(
                rows,
                f"the model failed on {errors_in_a_row} questions in a row "
                f"(last: {rows[-1].verification_errors[0]})",
            )
    return rows


def _answered_row(question: GoldenQuestion, result: AnswerResult) -> SmokeRow:
    cited = tuple(c.chunk_id for c in result.citations)
    return SmokeRow(
        question_id=question.id,
        category=question.category,
        question=question.question,
        status=result.status,
        attempts=result.attempts,
        cited=cited,
        expected_article_cited=_expected_cited(question, cited),
        verification_errors=result.verification_errors,
        latency_ms=result.latency_ms,
        answer=result.answer,
        retrieved_expected=_expected_cited(question, result.retrieved),
        top_score=result.top_score,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
        cost_usd=result.cost_usd,
        rendered=render_answer(result),
    )


def _log_progress(number: int, total: int, row: SmokeRow) -> None:
    """A line per question, so a slow or stuck run shows while it is running."""
    logger.info(
        "%d/%d %s %s in %.0f s (%d→%d tokens)",
        number, total, row.question_id, row.status, row.latency_ms / 1000,
        row.input_tokens, row.output_tokens,
    )  # fmt: skip


def render_answers(rows: Sequence[SmokeRow]) -> str:
    """Every question with its full answer, for reading by hand."""
    lines = ["# Smoke answers (M4)", ""]
    for row in rows:
        lines += [
            f"## {row.question_id} · {row.category} · {row.status}",
            "",
            f"**Soru:** {row.question}",
            "",
            row.rendered.rstrip() or f"(no answer: {'; '.join(row.verification_errors)})",
            "",
        ]
    return "\n".join(lines)


def _error_row(question: GoldenQuestion, exc: LLMError, latency_ms: float) -> SmokeRow:
    return SmokeRow(
        question_id=question.id,
        category=question.category,
        question=question.question,
        status="error",
        attempts=0,
        cited=(),
        expected_article_cited=False if question.answerable else None,
        verification_errors=(f"{type(exc).__name__}: {str(exc)[:200]}",),
        latency_ms=latency_ms,  # time spent before the failure (a timeout counts)
        answer="",
        input_tokens=exc.usage.input_tokens,
        output_tokens=exc.usage.output_tokens,
        cost_usd=exc.cost_usd,
    )


def summarize_smoke(rows: Sequence[SmokeRow]) -> dict[str, Any]:
    answerable = [r for r in rows if r.expected_article_cited is not None]
    out_of_scope = [r for r in rows if r.expected_article_cited is None]
    refused = [r for r in out_of_scope if r.status in ("out_of_scope", "no_sources")]
    hits = sum(1 for r in answerable if r.expected_article_cited)
    found = sum(1 for r in answerable if r.retrieved_expected)
    false_refusals = sum(1 for r in answerable if r.status in ("out_of_scope", "no_sources"))
    answered = [r for r in rows if r.status == "answered"]
    first_try = sum(1 for r in answered if r.attempts == 1)
    costs = [r.cost_usd for r in rows]
    latencies = np.array([r.latency_ms for r in rows]) if rows else np.array([0.0])
    return {
        "questions": len(rows),
        "status": dict(Counter(r.status for r in rows)),
        "verified_on_first_try": f"{first_try}/{len(answered)}",
        "expected_article_cited": f"{hits}/{len(answerable)}",
        "retrieval_had_expected": f"{found}/{len(answerable)}",
        "false_refusals": f"{false_refusals}/{len(answerable)}",
        "out_of_scope_refused": f"{len(refused)}/{len(out_of_scope)}",
        "tokens": {
            "input": sum(r.input_tokens for r in rows),
            "output": sum(r.output_tokens for r in rows),
        },
        "cost_usd": None if None in costs else round(sum(c or 0.0 for c in costs), 4),
        "latency_ms_p50": round(float(np.percentile(latencies, 50)), 1),
        "latency_ms_p95": round(float(np.percentile(latencies, 95)), 1),
    }


def render_smoke(rows: Sequence[SmokeRow], summary: dict[str, Any], context: dict[str, Any]) -> str:
    lines = [
        "# Smoke run (M4)",
        "",
        f"- Provider: `{context.get('provider')}`, model `{context.get('model')}`; "
        f"retrieval config `{context.get('config', 'full')}`, retrieval models on "
        f"{context.get('retrieval_device')}; thinking: {context.get('think')}, "
        f"num_ctx {context.get('num_ctx')}, "
        f"sampling {context.get('sampling')}.",
        f"- Questions: {summary['questions']}; status: {summary['status']}.",
        f"- Verified answers that cite an expected article: {summary['expected_article_cited']} "
        f"(retrieval had it: {summary['retrieval_had_expected']}).",
        f"- Answers verified on the first try: {summary['verified_on_first_try']}; "
        f"false refusals of answerable questions: {summary['false_refusals']}.",
        f"- Out-of-scope questions refused: {summary['out_of_scope_refused']}.",
        f"- Tokens: {summary['tokens']}; cost: {summary['cost_usd']} USD.",
        f"- Latency p50 {summary['latency_ms_p50']:.0f} ms, "
        f"p95 {summary['latency_ms_p95']:.0f} ms.",
    ]
    if context.get("stopped"):
        lines.append(
            f"- **Stopped early:** {context['stopped']}. Only the questions below ran; "
            "these numbers are not a full run."
        )
    lines += [
        "",
        "| Question | Category | Status | Attempts | Expected cited | Retrieved | Top score "
        "| Cited | Verification errors |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        marks = {None: "–", True: "yes", False: "no"}
        errors = "; ".join(row.verification_errors).replace("|", "\\|") or "–"
        cited = ", ".join(row.cited) or "–"
        score = "–" if row.top_score is None else f"{row.top_score:.3f}"
        lines.append(
            f"| {row.question_id} | {row.category} | {row.status} | {row.attempts} "
            f"| {marks[row.expected_article_cited]} | {marks[row.retrieved_expected]} | {score} "
            f"| {cited} | {errors} |"
        )
    return "\n".join(lines) + "\n"


def _expected_cited(question: GoldenQuestion, cited: Sequence[str]) -> bool | None:
    if not question.answerable:
        return None
    expected = {madde_key(chunk_id) for group in question.groups for chunk_id in group}
    return any(madde_key(chunk_id) in expected for chunk_id in cited)
