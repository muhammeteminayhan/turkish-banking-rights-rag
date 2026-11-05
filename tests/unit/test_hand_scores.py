import json
from dataclasses import asdict
from pathlib import Path

import pytest
from test_judge import _question, _row

from finhak.evaluation import hand_cli
from finhak.evaluation.golden import GoldenQuestion
from finhak.evaluation.hand_scores import (
    agreement,
    cohen_kappa,
    parse_sheet,
    pick_sample,
    render_sheet,
)
from finhak.evaluation.judge import Judgment, answer_sha, golden_sha
from finhak.evaluation.smoke import SmokeRow
from finhak.generation.render import DISCLAIMER

pytestmark = pytest.mark.unit

CATEGORIES = ["dogrudan"] * 6 + ["sayisal"] * 3 + ["yanlis_onerme"] * 3


def _set() -> tuple[list[SmokeRow], dict[str, GoldenQuestion]]:
    questions = [_question(f"q{i:02d}", cat) for i, cat in enumerate(CATEGORIES)]
    questions.append(_question("q99", "kapsam_disi"))
    rows = [_row(q.id, q.category, "answered") for q in questions]
    rows.append(_row("q50", "dogrudan", "unverified"))
    questions.append(_question("q50", "dogrudan"))
    return rows, {q.id: q for q in questions}


def test_the_sample_is_stratified_by_category_and_fixed() -> None:
    rows, questions = _set()

    sample = pick_sample(rows, questions, n=4)

    assert [r.question_id for r in sample] == [
        r.question_id for r in pick_sample(rows, questions, n=4)
    ]
    categories = [questions[r.question_id].category for r in sample]
    assert categories.count("dogrudan") == 2  # 6 of 12 answers: half of the sample
    assert categories.count("sayisal") == 1 and categories.count("yanlis_onerme") == 1
    assert [r.question_id for r in sample] == sorted(r.question_id for r in sample)


def test_only_answers_a_judge_model_scores_are_sampled() -> None:
    rows, questions = _set()

    sample = pick_sample(rows, questions, n=100)

    ids = {r.question_id for r in sample}
    assert len(ids) == 12
    assert "q99" not in ids  # out of scope: scored by rule
    assert "q50" not in ids  # withheld: the user never saw it


def test_the_sheet_shows_what_the_judge_sees_but_no_verdict() -> None:
    rows, questions = _set()
    sample = pick_sample(rows, questions, n=3)

    sheet = render_sheet(sample, questions, "run-1")

    assert sheet.count("**Puanın:**") == 3
    assert f"Soru {sample[0].question_id}?" in sheet
    assert "Hayır; talep etmedikçe limit artırılamaz." in sheet  # the expected answer
    assert "talep etmedikçe kart limitlerini" in sheet  # its evidence
    assert "> Banka limiti artıramaz." in sheet  # the shown answer, quoted
    assert DISCLAIMER not in sheet
    assert "gemini" not in sheet and "judge-1" not in sheet


def test_scores_are_read_with_short_forms_and_turkish_letters() -> None:
    sheet = "\n".join([
        "## q01 · doğrudan bilgi", "**Puanın:** Doğru", "**Not:** tamam",
        "## q02 · sayısal", "**Puanın:** k",
        "## q03 · sayısal", "**Puanın:** YANLIŞ",
        "## q04 · sayısal", "**Puanın:** ",
        "## q05 · sayısal", "**Puanın:** belki",
    ])  # fmt: skip

    scores = parse_sheet(sheet)

    assert scores.scores == {"q01": "dogru", "q02": "kismen", "q03": "yanlis"}
    assert scores.notes == {"q01": "tamam"}
    assert scores.problems == ["q05: 'belki' is not doğru, kısmen or yanlış (d / k / y)"]


def test_cohen_kappa_matches_a_worked_example() -> None:
    pairs = [("dogru", "dogru"), ("dogru", "kismen"), ("kismen", "kismen"), ("yanlis", "yanlis")]

    assert cohen_kappa(pairs) == pytest.approx(0.6364, abs=1e-4)  # (0.75 - 0.3125) / 0.6875
    assert cohen_kappa([("dogru", "dogru")] * 3) == 1.0
    assert cohen_kappa([]) is None


def test_agreement_on_three_labels_and_on_correct_or_not() -> None:
    human = {"q1": "dogru", "q2": "kismen", "q3": "yanlis", "q4": "dogru"}
    judge = {"q1": "dogru", "q2": "yanlis", "q3": "yanlis", "q5": "dogru"}

    result = agreement(human, judge)

    assert result.n == 3  # only answers both scored
    assert result.agreed == 2
    assert result.binary_agreed == 3  # q2: both say "not correct"
    assert result.disagreements == [("q2", "kismen", "yanlis")]


def _judgment(row: SmokeRow, question: GoldenQuestion, outcome: str, judge: str) -> Judgment:
    return Judgment(question_id=row.question_id, category=question.category, status=row.status,
                    outcome=outcome, judged_by=judge, rubric_version="v",  # type: ignore[arg-type]
                    answer_sha=answer_sha(row), golden_sha=golden_sha(question))  # fmt: skip


def test_the_command_makes_the_sheet_then_scores_each_judge(tmp_path: Path) -> None:
    rows, questions = _set()
    run = tmp_path / "run"
    run.mkdir()
    (run / "rows.jsonl").write_text(
        "".join(json.dumps(asdict(r), ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )
    golden = tmp_path / "golden.jsonl"
    golden.write_text("".join(q.model_dump_json() + "\n" for q in questions.values()),
                      encoding="utf-8")  # fmt: skip
    judged = [_judgment(r, questions[r.question_id], "dogru", "gemini/x") for r in rows[:12]]
    (run / "judgments.jsonl").write_text(
        "".join(json.dumps(asdict(j), ensure_ascii=False) + "\n" for j in judged), encoding="utf-8"
    )
    common = ["--golden", str(golden)]

    assert hand_cli.main(["make", str(run), "--n", "4", *common]) == hand_cli.EXIT_OK
    sheet = run / "hand_scores.md"
    text = sheet.read_text(encoding="utf-8")
    assert text.count("**Puanın:**") == 4

    filled = text.replace("**Puanın:** \n", "**Puanın:** d\n", 3)  # three scored, one left
    sheet.write_text(filled, encoding="utf-8")
    assert hand_cli.main(["make", str(run), *common]) == hand_cli.EXIT_FAILED  # keeps scores
    assert hand_cli.main(["score", str(run), *common]) == hand_cli.EXIT_OK

    report = (run / "agreement.md").read_text(encoding="utf-8")
    assert "gemini/x" in report
    assert "3 of 4 answers scored by hand" in report
    assert "3/3" in report  # the judge said dogru for all three
