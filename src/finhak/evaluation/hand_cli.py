"""Hand scores for an end-to-end run (M5): make the sheet, then compare it with each judge.

    python eval/hand_sheet.py make eval/results/<run>_e2e [--n 30]   # writes hand_scores.md
    python eval/hand_sheet.py score eval/results/<run>_e2e           # writes agreement.md

`make` never overwrites a sheet that already holds scores. `score` reads the sheet and, for
each judge (and rubric) in <run>/judgments.jsonl, compares the scores with that judge's
verdicts on the same answers: percent agreement and Cohen's kappa. Exit codes: 0 done,
1 failure (missing files, a sheet whose scores would be lost, unreadable scores).
"""

import argparse
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

from finhak.evaluation.golden import GoldenError, GoldenQuestion, load_golden
from finhak.evaluation.hand_scores import (
    LABELS,
    SAMPLE_SIZE,
    SCORE_LINE,
    Agreement,
    HandScores,
    agreement,
    parse_sheet,
    pick_sample,
    render_sheet,
)
from finhak.evaluation.judge import RULE, answer_sha, load_judgments, load_rows
from finhak.evaluation.smoke import SmokeRow
from finhak.fsutil import atomic_write_text

logger = logging.getLogger("finhak.hand")

EXIT_OK, EXIT_FAILED = 0, 1
SHEET, REPORT = "hand_scores.md", "agreement.md"


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("make", "score"):
        command = commands.add_parser(name)
        command.add_argument("run", type=Path, help="a results folder with rows.jsonl")
        command.add_argument("--golden", type=Path, default=Path("eval/golden.jsonl"))
        if name == "make":
            command.add_argument("--n", type=int, default=SAMPLE_SIZE)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        questions = {q.id: q for q in load_golden(args.golden)}
        rows = load_rows(args.run / "rows.jsonl")
    except (GoldenError, OSError, ValueError, TypeError) as exc:
        logger.error("%s", exc)
        return EXIT_FAILED
    if args.command == "make":
        return _make(args.run, args.n, rows, questions)
    return _score(args.run, rows)


def _make(
    run: Path, n: int, rows: Sequence[SmokeRow], questions: Mapping[str, GoldenQuestion]
) -> int:
    sheet = run / SHEET
    if sheet.exists() and parse_sheet(sheet.read_text(encoding="utf-8")).scores:
        logger.error("%s already holds scores: move it away to make a new sheet", sheet)
        return EXIT_FAILED
    sample = pick_sample(rows, questions, n=n)
    atomic_write_text(sheet, render_sheet(sample, questions, run.name))
    logger.info("wrote %s: %d answers to score", sheet, len(sample))
    return EXIT_OK


def _score(run: Path, rows: Sequence[SmokeRow]) -> int:
    try:
        text = (run / SHEET).read_text(encoding="utf-8")
        judgments = load_judgments(run / "judgments.jsonl")
    except (OSError, ValueError, TypeError) as exc:
        logger.error("%s", exc)
        return EXIT_FAILED
    hand = parse_sheet(text)
    for problem in hand.problems:
        logger.error("%s", problem)
    if hand.problems:
        return EXIT_FAILED
    current = {row.question_id: answer_sha(row) for row in rows}
    verdicts: dict[str, dict[str, str]] = {}
    for judgment in judgments:  # a later line wins
        if judgment.judged_by != RULE and current.get(judgment.question_id) == judgment.answer_sha:
            judge = f"{judgment.judged_by} (rubric {judgment.rubric_version})"
            verdicts.setdefault(judge, {})[judgment.question_id] = judgment.outcome
    results = {judge: agreement(hand.scores, v) for judge, v in sorted(verdicts.items())}
    asked = sum(line.startswith(SCORE_LINE) for line in text.splitlines())
    atomic_write_text(run / REPORT, render_agreement(run.name, hand, asked, results))
    for judge, result in results.items():
        logger.info("%s: %d/%d agree, kappa %s", judge, result.agreed, result.n, _f(result.kappa))
    return EXIT_OK


def render_agreement(
    run: str, hand: HandScores, asked: int, results: Mapping[str, Agreement]
) -> str:
    lines = [
        "# Agreement with the hand scores (M5)",
        "",
        f"- Run `{run}`: {len(hand.scores)} of {asked} answers scored by hand.",
        "- Percent agreement and Cohen's kappa on the three labels (doğru / kısmen / yanlış) and "
        "on correct-or-not (doğru vs the rest). Kappa 0.41–0.60 is usually read as moderate, "
        "0.61–0.80 as substantial (Landis & Koch). With n this small, read the counts.",
        "",
        "| Judge | n | Agree (3 labels) | κ | Agree (correct or not) | κ |",
        "|---|---|---|---|---|---|",
    ]
    for judge, r in results.items():
        lines.append(
            f"| {judge} | {r.n} | {r.agreed}/{r.n} | {_f(r.kappa)} "
            f"| {r.binary_agreed}/{r.n} | {_f(r.binary_kappa)} |"
        )
    for judge, r in results.items():
        lines += ["", f"## {judge}", "", "| Hand \\ Judge | " + " | ".join(LABELS) + " |"]
        lines.append("|---" * (len(LABELS) + 1) + "|")
        for label in LABELS:
            counts = " | ".join(str(r.confusion.get((label, other), 0)) for other in LABELS)
            lines.append(f"| {label} | {counts} |")
        if r.disagreements:
            lines += ["", "| Question | Hand | Judge | Your note |", "|---|---|---|---|"]
            for qid, mine, theirs in r.disagreements:
                note = hand.notes.get(qid, "").replace("|", "\\|") or "–"
                lines.append(f"| {qid} | {mine} | {theirs} | {note} |")
    return "\n".join(lines) + "\n"


def _f(value: float | None) -> str:
    return "–" if value is None else f"{value:.2f}"
