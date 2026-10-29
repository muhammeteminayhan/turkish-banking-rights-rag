import json
from collections.abc import Sequence
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pytest

from finhak.evaluation import judge_cli
from finhak.evaluation.golden import GoldenQuestion
from finhak.evaluation.judge import (
    JudgeOut,
    Judgment,
    judge_prompt,
    judge_rows,
    rule_outcome,
    summarize_judgments,
)
from finhak.evaluation.smoke import SmokeRow
from finhak.generation.render import DISCLAIMER
from finhak.llm.base import (
    ChatMessage,
    LLMOutputError,
    LLMRateLimited,
    LLMResult,
    LLMUnavailable,
    T,
    Usage,
)

pytestmark = pytest.mark.unit


def _question(qid: str, category: str, **fields: Any) -> GoldenQuestion:
    answerable = category != "kapsam_disi"
    data: dict[str, Any] = {
        "id": qid,
        "category": category,
        "question": f"Soru {qid}?",
        "expected_chunks": ["5464:m9:f1"] if answerable else [],
        "expected_answer": "Hayır; talep etmedikçe limit artırılamaz." if answerable else "–",
        "evidence": [{"chunk": "5464:m9:f1", "quote": "talep etmedikçe kart limitlerini"}]
        if answerable
        else [],
        "confidence": "high",
        "status": "approved",
    }
    return GoldenQuestion.model_validate({**data, **fields})


def _row(qid: str, category: str, status: str, answer: str = "Banka limiti artıramaz.") -> SmokeRow:
    return SmokeRow(
        question_id=qid, category=category, question=f"Soru {qid}?", status=status, attempts=1,
        cited=("5464:m9:f1",), expected_article_cited=None, verification_errors=(),
        latency_ms=1000.0, answer=answer,
        rendered=f"{answer}\n\nKaynaklar:\n[1] 5464 md. 9/1\n    “talep etmedikçe”\n\n"
                 f"{DISCLAIMER}\n",
    )  # fmt: skip


VERDICT = {
    "analysis": "Ana sonuç aynı.",
    "missing_points": [],
    "unsupported_claims": [],
    "contradicts_expected": False,
    "premise_corrected": None,
    "verdict": "dogru",
}


class FakeJudge:
    def __init__(self, *replies: dict[str, Any] | Exception) -> None:
        self.replies = list(replies)
        self.prompts: list[str] = []

    @property
    def name(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "judge-1"

    def generate(
        self, system: str, messages: Sequence[ChatMessage], schema: type[T]
    ) -> LLMResult[T]:
        self.prompts.append(messages[-1].content)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return LLMResult(schema.model_validate(reply), json.dumps(reply), Usage(300, 40),
                         "fake", "judge-1", 0.0)  # fmt: skip


@pytest.mark.parametrize(
    ("category", "status", "outcome"),
    [
        ("kapsam_disi", "out_of_scope", "dogru_red"),
        ("kapsam_disi", "no_sources", "dogru_red"),
        ("kapsam_disi", "answered", "yanlis"),  # it should have refused
        ("dogrudan", "out_of_scope", "yersiz_red"),
        ("dogrudan", "unverified", "geri_tutuldu"),
        ("kapsam_disi", "unverified", "geri_tutuldu"),
        ("dogrudan", "error", "hata"),
        ("dogrudan", "answered", None),  # the judge model decides
    ],
)
def test_outcomes_that_need_no_judge_model(category: str, status: str, outcome: str | None) -> None:
    assert rule_outcome(_question("q", category), _row("q", category, status)) == outcome


def test_only_answers_that_reached_the_user_go_to_the_judge() -> None:
    questions = {q.id: q for q in [_question("q1", "dogrudan"), _question("q2", "kapsam_disi")]}
    rows = [_row("q1", "dogrudan", "answered"), _row("q2", "kapsam_disi", "out_of_scope")]
    judge = FakeJudge(VERDICT)

    judgments = list(judge_rows(rows, questions, judge))

    assert [(j.question_id, j.outcome, j.judged_by) for j in judgments] == [
        ("q2", "dogru_red", "rule"),  # rule-scored rows first: a quota stop keeps them
        ("q1", "dogru", "fake/judge-1"),
    ]
    assert len(judge.prompts) == 1
    assert (judgments[1].input_tokens, judgments[1].output_tokens) == (300, 40)


def test_the_prompt_gives_the_expected_answer_its_evidence_and_the_shown_answer() -> None:
    question = _question("q1", "yanlis_onerme", comment="İki metin çelişiyor; ikisini göster.")
    judge = FakeJudge({**VERDICT, "premise_corrected": True})

    list(judge_rows([_row("q1", "yanlis_onerme", "answered")], {"q1": question}, judge))

    prompt = judge.prompts[0]
    assert "Soru q1?" in prompt
    assert "Hayır; talep etmedikçe limit artırılamaz." in prompt
    assert "talep etmedikçe kart limitlerini" in prompt  # the evidence quote
    assert "Banka limiti artıramaz." in prompt  # the model's answer
    assert "varsayımı yanlış" in prompt  # what a false-premise answer must do
    assert "İki metin çelişiyor" in prompt
    assert DISCLAIMER not in prompt
    assert prompt == judge_prompt(question, _row("q1", "yanlis_onerme", "answered"))


def test_judged_answers_are_skipped_on_a_rerun_unless_the_answer_changed() -> None:
    questions = {"q1": _question("q1", "dogrudan")}
    first = list(judge_rows([_row("q1", "dogrudan", "answered")], questions, FakeJudge(VERDICT)))
    done = {j.key for j in first}
    judge = FakeJudge(VERDICT)

    again = list(judge_rows([_row("q1", "dogrudan", "answered")], questions, judge, done))
    changed = list(
        judge_rows([_row("q1", "dogrudan", "answered", "Başka.")], questions, judge, done)
    )

    assert again == [] and len(changed) == 1


def test_a_judge_that_fails_on_one_answer_does_not_stop_the_others() -> None:
    questions = {q: _question(q, "dogrudan") for q in ("q1", "q2")}
    rows = [_row("q1", "dogrudan", "answered"), _row("q2", "dogrudan", "answered")]
    judge = FakeJudge(LLMOutputError("bad json"), LLMOutputError("bad json"), VERDICT)

    judgments = list(judge_rows(rows, questions, judge))

    assert [j.question_id for j in judgments] == ["q2"]  # q1 stays unjudged for a rerun


def test_a_used_up_quota_stops_the_judging() -> None:
    judge = FakeJudge(LLMRateLimited("daily quota"))

    with pytest.raises(LLMRateLimited):
        list(
            judge_rows(
                [_row("q1", "dogrudan", "answered")], {"q1": _question("q1", "dogrudan")}, judge
            )
        )


def test_the_summary_gives_accuracy_refusals_and_premise_corrections() -> None:
    base = Judgment(question_id="q", category="dogrudan", status="answered", outcome="dogru",
                    judged_by="rule", rubric_version="v", answer_sha="x")  # fmt: skip
    judgments = [
        base,
        replace(base, question_id="q2", outcome="kismen"),
        replace(base, question_id="q3", outcome="geri_tutuldu", status="unverified"),
        replace(base, question_id="q4", category="yanlis_onerme", premise_corrected=True),
        # a judge may fill premise_corrected for other categories: it must not count
        replace(base, question_id="q7", premise_corrected=False),
        replace(base, question_id="q5", category="kapsam_disi", outcome="dogru_red"),
        replace(base, question_id="q6", category="kapsam_disi", outcome="yanlis"),
    ]

    summary = summarize_judgments(judgments)

    assert summary["answerable"] == 5
    assert summary["correct"] == "3/5"  # dogru only
    assert summary["correct_or_partial"] == "4/5"
    assert summary["withheld"] == "1/5"
    assert summary["out_of_scope_refused"] == "1/2"
    assert summary["premise_corrected"] == "1/1"
    assert summary["by_category"]["kapsam_disi"] == {"dogru_red": 1, "yanlis": 1}


def test_the_judge_command_writes_judgments_and_resumes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run = tmp_path / "2026-10-29_e2e"
    run.mkdir()
    rows = [_row("q1", "dogrudan", "answered"), _row("q2", "kapsam_disi", "out_of_scope")]
    (run / "rows.jsonl").write_text(
        "".join(json.dumps(asdict(r), ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )
    golden = tmp_path / "golden.jsonl"
    golden.write_text(
        "".join(q.model_dump_json() + "\n" for q in [_question("q1", "dogrudan"),
                                                   _question("q2", "kapsam_disi")]),
        encoding="utf-8",
    )  # fmt: skip
    judge = FakeJudge(VERDICT)
    args = [str(run), "--golden", str(golden)]

    assert judge_cli.main(args, provider_factory=lambda: judge) == judge_cli.EXIT_OK
    assert judge_cli.main(args, provider_factory=lambda: judge) == judge_cli.EXIT_OK

    lines = (run / "judgments.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2  # the rerun judged nothing again
    report = (run / "judge_report.md").read_text(encoding="utf-8")
    assert "fake/judge-1" in report and "1/1" in report


def test_the_judge_command_keeps_what_it_judged_when_the_quota_runs_out(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    rows = [_row("q1", "dogrudan", "answered"), _row("q2", "dogrudan", "answered")]
    (run / "rows.jsonl").write_text(
        "".join(json.dumps(asdict(r), ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )
    golden = tmp_path / "golden.jsonl"
    golden.write_text(
        "".join(_question(q, "dogrudan").model_dump_json() + "\n" for q in ("q1", "q2")),
        encoding="utf-8",
    )
    judge = FakeJudge(VERDICT, LLMRateLimited("daily quota"))

    code = judge_cli.main([str(run), "--golden", str(golden)], provider_factory=lambda: judge)

    assert code == judge_cli.EXIT_INCOMPLETE
    assert len((run / "judgments.jsonl").read_text(encoding="utf-8").splitlines()) == 1
    assert "Not finished" in (run / "judge_report.md").read_text(encoding="utf-8")

    again = FakeJudge(VERDICT)  # the next day: only q2 is left
    code = judge_cli.main([str(run), "--golden", str(golden)], provider_factory=lambda: again)

    assert code == judge_cli.EXIT_OK
    assert len(again.prompts) == 1
    assert "Not finished" not in (run / "judge_report.md").read_text(encoding="utf-8")


def test_judge_out_asks_for_the_analysis_before_the_verdict() -> None:
    assert next(iter(JudgeOut.model_fields)) == "analysis"
    assert list(JudgeOut.model_fields)[-1] == "verdict"


def test_a_judge_that_cannot_be_reached_stops_the_judging() -> None:
    judge = FakeJudge(LLMUnavailable("Ollama not reachable"))
    rows = [_row("q1", "dogrudan", "answered")]

    with pytest.raises(LLMUnavailable):
        list(judge_rows(rows, {"q1": _question("q1", "dogrudan")}, judge))


def test_an_answer_is_judged_again_when_its_golden_entry_changes() -> None:
    row = _row("q1", "dogrudan", "answered")
    first = list(judge_rows([row], {"q1": _question("q1", "dogrudan")}, FakeJudge(VERDICT)))
    edited = {"q1": _question("q1", "dogrudan", expected_answer="Hayır, artırılamaz.")}
    judge = FakeJudge(VERDICT)

    again = list(judge_rows([row], edited, judge, {j.key for j in first}))

    assert len(again) == 1 and len(judge.prompts) == 1


def test_false_premise_questions_left_unanswered_count_as_not_corrected() -> None:
    base = Judgment(question_id="q1", category="yanlis_onerme", status="answered",
                    outcome="dogru", judged_by="j", rubric_version="v", answer_sha="x",
                    premise_corrected=True)  # fmt: skip
    withheld = replace(base, question_id="q2", outcome="geri_tutuldu", premise_corrected=None)

    assert summarize_judgments([base, withheld])["premise_corrected"] == "1/2"


def _write_run(tmp_path: Path, rows: list[SmokeRow], questions: list[GoldenQuestion]) -> list[str]:
    run = tmp_path / "run"
    run.mkdir()
    (run / "rows.jsonl").write_text(
        "".join(json.dumps(asdict(r), ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )
    golden = tmp_path / "golden.jsonl"
    golden.write_text("".join(q.model_dump_json() + "\n" for q in questions), encoding="utf-8")
    return [str(run), "--golden", str(golden)]


def test_a_dead_judge_fails_the_command_but_keeps_the_rule_scores(tmp_path: Path) -> None:
    rows = [_row("q1", "dogrudan", "answered"), _row("q2", "kapsam_disi", "out_of_scope")]
    args = _write_run(tmp_path, rows, [_question("q1", "dogrudan"), _question("q2", "kapsam_disi")])
    judge = FakeJudge(LLMUnavailable("Ollama not reachable"))

    code = judge_cli.main(args, provider_factory=lambda: judge)

    assert code == judge_cli.EXIT_FAILED
    lines = (tmp_path / "run" / "judgments.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["question_id"] for line in lines] == ["q2"]
    assert "Not finished" in (tmp_path / "run" / "judge_report.md").read_text(encoding="utf-8")


def test_answers_the_judge_could_not_score_make_the_command_incomplete(tmp_path: Path) -> None:
    args = _write_run(tmp_path, [_row("q1", "dogrudan", "answered")], [_question("q1", "dogrudan")])
    judge = FakeJudge(LLMOutputError("bad json"), LLMOutputError("bad json"))

    code = judge_cli.main(args, provider_factory=lambda: judge)

    assert code == judge_cli.EXIT_INCOMPLETE
    report = (tmp_path / "run" / "judge_report.md").read_text(encoding="utf-8")
    assert "1 of 1 answers not scored" in report


@pytest.mark.parametrize(
    ("flags", "outcome"),
    [
        ({"unsupported_claims": ["konut finansmanı hariç"]}, "kismen"),
        ({"contradicts_expected": True}, "kismen"),
        ({}, "dogru"),
    ],
)
def test_a_correct_verdict_with_an_unsupported_claim_is_partly_correct(
    flags: dict[str, Any], outcome: str
) -> None:
    # Gemini Flash-Lite listed "konut finansmanı hariç" (b1-060) as unsupported, then called
    # the answer correct: the rubric's own definition makes it "kismen".
    judge = FakeJudge({**VERDICT, **flags})

    (judgment,) = judge_rows([_row("q1", "dogrudan", "answered")],
                             {"q1": _question("q1", "dogrudan")}, judge)  # fmt: skip

    assert (judgment.outcome, judgment.judge_verdict) == (outcome, "dogru")
