"""The M4 smoke run: a handful of golden questions answered end to end.

It is not the M5 evaluation. It shows that the pipeline runs, how often answers pass
citation verification, and whether a verified answer cites the expected article.
"""

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from finhak.evaluation.golden import GoldenQuestion
from finhak.evaluation.retrieval import madde_key
from finhak.generation.pipeline import AnswerResult
from finhak.llm.base import LLMError


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


def load_smoke_ids(path: Path) -> list[str]:
    ids = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.split("#", 1)[0].strip()
        if value:
            ids.append(value)
    return ids


def run_smoke(
    questions: Sequence[GoldenQuestion], ask: Callable[[str], AnswerResult]
) -> list[SmokeRow]:
    rows = []
    for question in questions:
        try:
            result = ask(question.question)
        except LLMError as exc:  # one failing question does not lose the run
            rows.append(_error_row(question, exc))
            continue
        cited = tuple(c.chunk_id for c in result.citations)
        rows.append(
            SmokeRow(
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
            )
        )
    return rows


def _error_row(question: GoldenQuestion, exc: LLMError) -> SmokeRow:
    return SmokeRow(
        question_id=question.id,
        category=question.category,
        question=question.question,
        status="error",
        attempts=0,
        cited=(),
        expected_article_cited=False if question.answerable else None,
        verification_errors=(f"{type(exc).__name__}: {str(exc)[:200]}",),
        latency_ms=0.0,
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
        f"retrieval config `{context.get('config', 'full')}`.",
        f"- Questions: {summary['questions']}; status: {summary['status']}.",
        f"- Verified answers that cite an expected article: {summary['expected_article_cited']} "
        f"(retrieval had it: {summary['retrieval_had_expected']}).",
        f"- Answers verified on the first try: {summary['verified_on_first_try']}; "
        f"false refusals of answerable questions: {summary['false_refusals']}.",
        f"- Out-of-scope questions refused: {summary['out_of_scope_refused']}.",
        f"- Tokens: {summary['tokens']}; cost: {summary['cost_usd']} USD.",
        f"- Latency p50 {summary['latency_ms_p50']:.0f} ms, "
        f"p95 {summary['latency_ms_p95']:.0f} ms.",
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
