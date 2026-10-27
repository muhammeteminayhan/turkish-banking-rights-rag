from dataclasses import replace
from pathlib import Path

import pytest

from finhak.evaluation import smoke_cli
from finhak.evaluation.golden import GoldenQuestion, load_golden
from finhak.evaluation.smoke import load_smoke_ids, render_smoke, run_smoke, summarize_smoke
from finhak.generation.cli import render_answer
from finhak.generation.pipeline import AnswerResult, AnswerStatus
from finhak.generation.render import DISCLAIMER, RenderedCitation
from finhak.llm.base import LLMProvider, LLMUnavailable, Usage

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.unit


def _question(qid: str, category: str, expected: list[str]) -> GoldenQuestion:
    return GoldenQuestion.model_validate(
        {"id": qid, "category": category, "question": f"Soru {qid}?",
         "expected_chunks": expected, "expected_answer": "…", "evidence": [],
         "confidence": "high"}
    )  # fmt: skip


def _result(status: AnswerStatus, cited: list[str], errors: tuple[str, ...] = ()) -> AnswerResult:
    citations = tuple(
        RenderedCitation(c, f"label {c}", "alıntı metni burada", "https://x", "snap", ())
        for c in cited
    )
    return AnswerResult(
        status=status, answer="cevap", citations=citations, false_premise=False,
        confidence="high", notes=(), attempts=1, verification_errors=errors,
        retrieved=tuple(cited), usage=Usage(10, 5), cost_usd=0.0, provider="fake",
        model="fake-1", latency_ms=1200.0,
    )  # fmt: skip


QUESTIONS = [
    _question("q1", "dogrudan", ["6502:m22:f1"]),
    _question("q2", "sayisal", ["tcmb-ucret-talimat:s9:bc"]),
    _question("q3", "kapsam_disi", []),
    _question("q4", "dogrudan", ["5464:m10:f1"]),
]
ANSWERS = {
    "Soru q1?": _result("answered", ["6502:m22:f2"]),  # same article, other fıkra
    "Soru q2?": _result("answered", ["6502:m1:f1"]),  # verified, but not the expected rule
    "Soru q3?": _result("out_of_scope", []),
    "Soru q4?": _result("unverified", [], errors=("Atıf 1: madde 10, 11 değil.",)),
}


def test_smoke_rows_record_status_and_whether_the_expected_article_was_cited() -> None:
    rows = run_smoke(QUESTIONS, lambda question: ANSWERS[question])

    assert [(r.question_id, r.status, r.expected_article_cited) for r in rows] == [
        ("q1", "answered", True),
        ("q2", "answered", False),
        ("q3", "out_of_scope", None),
        ("q4", "unverified", False),
    ]


def test_smoke_summary_counts_outcomes() -> None:
    summary = summarize_smoke(run_smoke(QUESTIONS, lambda q: ANSWERS[q]))

    assert summary["status"] == {"answered": 2, "out_of_scope": 1, "unverified": 1}
    assert summary["expected_article_cited"] == "1/3"
    assert summary["out_of_scope_refused"] == "1/1"
    assert summary["latency_ms_p50"] == 1200.0


def test_smoke_report_is_markdown_with_one_row_per_question() -> None:
    rows = run_smoke(QUESTIONS, lambda q: ANSWERS[q])

    report = render_smoke(rows, summarize_smoke(rows), {"provider": "fake", "model": "fake-1"})

    assert report.startswith("# Smoke run")
    assert report.count("\n| q") == 4
    assert "madde 10, 11 değil" in report


def test_smoke_ids_file_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "smoke.txt"
    path.write_text("# M4 smoke\nb1-001\n\nb1-002  # direct\n", encoding="utf-8")

    assert load_smoke_ids(path) == ["b1-001", "b1-002"]


def test_the_rendered_answer_shows_citations_snapshot_notes_and_disclaimer() -> None:
    result = _result("answered", ["5411:m2:f2"])
    citation = RenderedCitation(
        "5411:m2:f2",
        "5411 sayılı Bankacılık Kanunu md. 2/2",
        "bankaları kapsar",
        "https://www.mevzuat.gov.tr/x",
        "mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı.",
        ("Fıkra numarası kaynak metinde yazmıyor.",),
    )
    result = replace(result, citations=(citation,))

    text = render_answer(result)

    assert "[1] 5411 sayılı Bankacılık Kanunu md. 2/2" in text
    assert "“bankaları kapsar”" in text
    assert "23.10.2026" in text
    assert "Fıkra numarası kaynak metinde yazmıyor." in text
    assert text.rstrip().endswith(DISCLAIMER)


def test_a_withheld_answer_explains_why() -> None:
    text = render_answer(_result("unverified", [], errors=("Atıf 1: alıntı geçmiyor.",)))

    assert "Atıf 1: alıntı geçmiyor." in text


def test_smoke_command_stops_when_the_model_or_the_questions_are_missing(tmp_path: Path) -> None:
    golden = tmp_path / "g.jsonl"
    golden.write_text(QUESTIONS[0].model_dump_json() + "\n", encoding="utf-8")
    ids = tmp_path / "ids.txt"
    ids.write_text("q1\n", encoding="utf-8")

    def unavailable() -> LLMProvider:
        raise LLMUnavailable("Ollama not reachable")

    args = ["--golden", str(golden), "--ids", str(ids)]
    assert smoke_cli.main(args, provider_factory=unavailable) == smoke_cli.EXIT_FAILED
    ids.write_text("q1\nq9\n", encoding="utf-8")  # an id that is not in the golden file
    assert smoke_cli.main(args, provider_factory=unavailable) == smoke_cli.EXIT_FAILED


def test_the_real_smoke_ids_exist_in_the_draft_batch() -> None:
    ids = load_smoke_ids(ROOT / "eval" / "smoke.txt")
    known = {q.id for q in load_golden(ROOT / "eval" / "drafts" / "batch1.jsonl")}

    assert len(ids) == 20
    assert set(ids) <= known


def test_a_failing_question_becomes_an_error_row_not_a_lost_run() -> None:
    def ask(question: str) -> AnswerResult:
        if question == "Soru q2?":
            raise LLMUnavailable("Ollama stopped", usage=Usage(7, 0))
        return ANSWERS[question]

    rows = run_smoke(QUESTIONS, ask)
    summary = summarize_smoke(rows)

    assert [r.status for r in rows] == ["answered", "error", "out_of_scope", "unverified"]
    assert "LLMUnavailable: Ollama stopped" in rows[1].verification_errors[0]
    assert summary["status"]["error"] == 1
    assert summary["tokens"]["input"] == 10 + 7 + 10 + 10


def test_the_summary_separates_retrieval_and_generation_misses() -> None:
    summary = summarize_smoke(run_smoke(QUESTIONS, lambda q: ANSWERS[q]))

    assert summary["retrieval_had_expected"] == "1/3"  # only q1's retrieved ids hold it
    assert summary["verified_on_first_try"] == "2/2"
    assert summary["false_refusals"] == "0/3"
    assert summary["cost_usd"] == 0.0
