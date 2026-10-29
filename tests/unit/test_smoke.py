import itertools
import logging
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from finhak.evaluation import smoke, smoke_cli
from finhak.evaluation.golden import GoldenQuestion, load_golden
from finhak.evaluation.smoke import (
    SmokeStopped,
    load_smoke_ids,
    render_smoke,
    run_smoke,
    summarize_smoke,
)
from finhak.generation.cli import render_answer
from finhak.generation.pipeline import AnswerResult, AnswerStatus
from finhak.generation.render import DISCLAIMER, RenderedCitation
from finhak.llm.base import LLMError, LLMProvider, LLMUnavailable, Usage

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

    context = {"provider": "fake", "model": "fake-1", "sampling": {"temperature": 0.0}}
    report = render_smoke(rows, summarize_smoke(rows), context)

    assert report.startswith("# Smoke run")
    assert "sampling {'temperature': 0.0}" in report  # runs differ by it
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


def test_the_real_smoke_ids_exist_in_the_golden_set() -> None:
    ids = load_smoke_ids(ROOT / "eval" / "smoke.txt")
    known = {q.id for q in load_golden(ROOT / "eval" / "golden.jsonl")}

    assert len(ids) == 20
    assert set(ids) <= known


def test_the_golden_set_holds_only_approved_questions() -> None:
    questions = load_golden(ROOT / "eval" / "golden.jsonl")

    assert questions and all(q.status == "approved" for q in questions)
    assert len({q.id for q in questions}) == len(questions)


def test_the_smoke_command_reads_the_approved_golden_set_by_default() -> None:
    assert smoke_cli.parse_args([]).golden == Path("eval/golden.jsonl")


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


def test_the_run_stops_when_the_model_fails_on_two_questions_in_a_row() -> None:
    def ask(question: str) -> AnswerResult:  # e.g. Ollama timing out on a full GPU
        raise LLMError("Ollama did not answer within 300 s")

    with pytest.raises(SmokeStopped) as stopped:
        run_smoke(QUESTIONS, ask)

    assert [r.status for r in stopped.value.rows] == ["error", "error"]
    assert "2 questions in a row" in str(stopped.value)


def test_errors_with_answers_in_between_do_not_stop_the_run() -> None:
    def ask(question: str) -> AnswerResult:
        if question in ("Soru q1?", "Soru q3?"):
            raise LLMError("cut off")
        return ANSWERS[question]

    rows = run_smoke(QUESTIONS, ask)

    assert [r.status for r in rows] == ["error", "answered", "error", "unverified"]


def test_each_question_is_logged_as_it_finishes(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="finhak.smoke"):
        run_smoke(QUESTIONS, lambda q: ANSWERS[q])

    lines = [record.getMessage() for record in caplog.records]
    assert len(lines) == 4
    assert lines[0].startswith("1/4 q1 answered in 1 s")


def test_a_stopped_smoke_command_keeps_the_partial_report_and_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    golden = tmp_path / "g.jsonl"
    golden.write_text("".join(q.model_dump_json() + "\n" for q in QUESTIONS), encoding="utf-8")
    ids = tmp_path / "ids.txt"
    ids.write_text("q1\nq2\nq3\n", encoding="utf-8")

    def timing_out(*args: object, **kwargs: object) -> AnswerResult:
        raise LLMError("Ollama did not answer within 300 s")

    monkeypatch.setattr(smoke_cli, "connect", lambda url: nullcontext())
    monkeypatch.setattr(smoke_cli, "open_retrieval", lambda conn, config, device: object())
    monkeypatch.setenv("RETRIEVAL_DEVICE", "cpu")
    monkeypatch.setattr(smoke_cli, "answer_question", timing_out)
    fake = SimpleNamespace(name="fake", model="fake-1")
    out_dir = tmp_path / "results"

    code = smoke_cli.main(
        ["--golden", str(golden), "--ids", str(ids), "--out-dir", str(out_dir)],
        provider_factory=lambda: fake,  # type: ignore[arg-type,return-value]
    )

    assert code == smoke_cli.EXIT_FAILED
    (report,) = out_dir.glob("*_smoke/report.md")
    text = report.read_text(encoding="utf-8")
    assert "Stopped early" in text
    assert "retrieval models on cpu" in text
    assert text.count("\n| q") == 2


def test_the_summary_separates_retrieval_and_generation_misses() -> None:
    summary = summarize_smoke(run_smoke(QUESTIONS, lambda q: ANSWERS[q]))

    assert summary["retrieval_had_expected"] == "1/3"  # only q1's retrieved ids hold it
    assert summary["verified_on_first_try"] == "2/2"
    assert summary["false_refusals"] == "0/3"
    assert summary["cost_usd"] == 0.0


def test_the_rendered_answers_are_kept_for_reading() -> None:
    from finhak.evaluation.smoke import render_answers

    rows = run_smoke(QUESTIONS, lambda q: ANSWERS[q])

    text = render_answers(rows)

    assert DISCLAIMER in rows[0].rendered
    assert text.startswith("# Smoke answers")
    assert text.count("\n## ") == 4
    assert "## q1 · dogrudan · answered" in text
    assert "Soru q1?" in text


def test_two_errors_on_the_last_questions_end_the_run_normally() -> None:
    def ask(question: str) -> AnswerResult:
        if question in ("Soru q3?", "Soru q4?"):
            raise LLMError("cut off")
        return ANSWERS[question]

    rows = run_smoke(QUESTIONS, ask)  # every question ran: nothing was cut short

    assert [r.status for r in rows] == ["answered", "answered", "error", "error"]


def test_an_interrupted_run_keeps_the_questions_that_ran() -> None:
    def ask(question: str) -> AnswerResult:
        if question == "Soru q3?":
            raise KeyboardInterrupt  # Ctrl-C on a slow run
        return ANSWERS[question]

    with pytest.raises(SmokeStopped) as stopped:
        run_smoke(QUESTIONS, ask)

    assert [r.question_id for r in stopped.value.rows] == ["q1", "q2"]
    assert "interrupted" in str(stopped.value)


def test_an_error_row_records_how_long_the_failed_question_took(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticks = itertools.count(0.0, 300.0)  # each reading of the clock is 300 s later
    monkeypatch.setattr(smoke, "time", SimpleNamespace(perf_counter=lambda: next(ticks)))

    def ask(question: str) -> AnswerResult:
        raise LLMError("Ollama did not answer within 300 s")

    rows = run_smoke(QUESTIONS[:1], ask)

    assert rows[0].latency_ms == 300_000.0


def test_a_withheld_draft_is_kept_in_the_row_but_never_rendered() -> None:
    withheld = replace(_result("unverified", [], errors=("x",)), withheld_draft="Taslak cevap.")

    rows = run_smoke(QUESTIONS[3:], lambda q: withheld)

    assert rows[0].withheld_draft == "Taslak cevap."
    assert "Taslak cevap." not in rows[0].rendered


def test_the_all_option_answers_every_golden_question_into_an_e2e_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    golden = tmp_path / "g.jsonl"
    golden.write_text("".join(q.model_dump_json() + "\n" for q in QUESTIONS), encoding="utf-8")
    monkeypatch.setattr(smoke_cli, "connect", lambda url: nullcontext())
    monkeypatch.setattr(smoke_cli, "open_retrieval", lambda conn, config, device: object())
    monkeypatch.setattr(smoke_cli, "answer_question", lambda q, *a, **k: ANSWERS[q])
    monkeypatch.setenv("RETRIEVAL_DEVICE", "cpu")
    out_dir = tmp_path / "results"
    fake = SimpleNamespace(name="fake", model="fake-1")

    code = smoke_cli.main(
        ["--golden", str(golden), "--all", "--out-dir", str(out_dir)],
        provider_factory=lambda: fake,  # type: ignore[arg-type,return-value]
    )

    assert code == smoke_cli.EXIT_OK
    (folder,) = out_dir.glob("*_e2e")
    rows = (folder / "rows.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == len(QUESTIONS)
    assert (folder / "report.md").read_text(encoding="utf-8").startswith("# End-to-end run")
