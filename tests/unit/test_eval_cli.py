"""The evaluation report, from a fake retriever (no database, no models)."""

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from chunk_factory import make_chunk
from finhak.evaluation.cli import render_report, run_configs, write_results
from finhak.evaluation.golden import GoldenQuestion
from finhak.parsing.chunker import Chunk
from finhak.retrieval.direct_ref import DirectRef
from finhak.retrieval.hybrid import Retriever
from finhak.retrieval.types import Scored

pytestmark = pytest.mark.unit

CHUNKS = {
    c.id: c
    for c in (
        make_chunk("5464:m10:f1", "Kart aidatı.", madde="10"),
        make_chunk("6502:m22:f1", "Faiz.", madde="22"),
    )
}


class Lookup:
    def by_ids(self, ids: Sequence[str]) -> dict[str, Chunk]:
        return {i: CHUNKS[i] for i in ids if i in CHUNKS}

    def by_ref(self, ref: DirectRef) -> list[Chunk]:
        return [c for c in CHUNKS.values() if (c.doc_id, c.madde) == (ref.doc_id, ref.madde)]


def _search(query: str, k: int) -> list[Scored]:
    return [Scored("5464:m10:f1", 1.0), Scored("6502:m22:f1", 0.5)][:k]


def _question(
    qid: str, text: str, expected: list[str], category: str = "dogrudan"
) -> GoldenQuestion:
    return GoldenQuestion.model_validate(
        {
            "id": qid,
            "category": category,
            "question": text,
            "expected_chunks": expected,
            "expected_answer": "…",
            "evidence": [],
            "confidence": "high",
        }
    )


QUESTIONS = [
    _question("q1", "Kart aidatı?", ["5464:m10:f1"]),
    _question("q2", "TKHK m.22 faiz", ["6502:m22:f1"], category="sayisal"),
    _question("q3", "Kira?", [], category="kapsam_disi"),
]
RETRIEVER = Retriever(searchers={"fts": _search, "vector": _search}, lookup=Lookup(), reranker=None)


def test_run_configs_scores_only_answerable_questions() -> None:
    results = run_configs(RETRIEVER, QUESTIONS, ["fts", "hybrid"])

    assert set(results) == {"fts", "hybrid"}
    assert [s.question_id for s in results["fts"].scores] == ["q1", "q2"]
    assert results["fts"].summary.madde["recall@5"] == 1.0
    assert results["fts"].summary.chunk["mrr"] == pytest.approx((1 + 0.5) / 2)


def test_run_configs_needs_an_answerable_question() -> None:
    with pytest.raises(ValueError, match="answerable"):
        run_configs(RETRIEVER, QUESTIONS[2:], ["fts"])


def test_report_marks_drafts_and_splits_cited_questions(tmp_path: Path) -> None:
    golden = tmp_path / "batch.jsonl"
    golden.write_text("".join(q.model_dump_json() + "\n" for q in QUESTIONS), encoding="utf-8")
    results = run_configs(RETRIEVER, QUESTIONS, ["fts"])

    write_results(tmp_path / "out", golden, QUESTIONS, results, context={"limit": 10})

    report = (tmp_path / "out" / "report.md").read_text(encoding="utf-8")
    assert "Draft numbers" in report
    assert "cites_article (n=1)" in report
    assert "no_citation (n=1)" in report
    assert "| `fts` |" in report
    metrics = json.loads((tmp_path / "out" / "metrics.json").read_text(encoding="utf-8"))
    assert (metrics["scored"], metrics["limit"]) == (2, 10)


def test_report_lists_the_misses_of_the_last_config() -> None:
    def miss(query: str, k: int) -> list[Scored]:
        return [Scored("6502:m22:f1", 1.0)]

    retriever = Retriever(searchers={"fts": miss}, lookup=Lookup(), reranker=None)
    results = run_configs(retriever, QUESTIONS, ["fts"])
    metrics = {
        "golden": "g.jsonl",
        "questions": 3,
        "scored": 2,
        "status": {"draft": 0, "approved": 3},
    }

    report = render_report(metrics, results, QUESTIONS)

    assert "Draft numbers" not in report
    assert "| q1 | dogrudan | 5464:m10 | 6502:m22:f1 |" in report
