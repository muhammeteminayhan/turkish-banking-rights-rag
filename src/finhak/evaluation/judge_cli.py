"""Score an end-to-end run with a judge model (M5), for free: a local Ollama model or a free
API tier.

    python eval/judge.py eval/results/<run>_e2e                       # Ollama, OLLAMA_MODEL
    python eval/judge.py eval/results/<run>_e2e --model aya-expanse:8b
    python eval/judge.py eval/results/<run>_e2e --judge gemini        # GEMINI_API_KEY

Refusals, withheld answers and errors are scored by rule, the other answers by the judge
against the approved expected answer and its evidence. Each judgment is appended to
<run>/judgments.jsonl as soon as it is made, so a run stopped by a daily quota continues
where it stopped. Writes <run>/judge_report.md. Exit codes: 0 every answer scored,
1 failure (also: the judge could not be used midway), 3 incomplete (the quota ran out or
some answers got no valid verdict; run the command again later).
"""

import argparse
import json
import logging
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from finhak.config import merged_env
from finhak.evaluation.golden import GoldenError, GoldenQuestion, load_golden
from finhak.evaluation.judge import (
    RUBRIC_VERSION,
    Judgment,
    judge_rows,
    judgment_key,
    load_judgments,
    load_rows,
    summarize_judgments,
)
from finhak.evaluation.smoke import SmokeRow
from finhak.fsutil import atomic_write_text
from finhak.llm import factory
from finhak.llm.base import LLMError, LLMProvider, LLMRateLimited, LLMUnavailable

logger = logging.getLogger("finhak.judge")

EXIT_OK, EXIT_FAILED, EXIT_INCOMPLETE = 0, 1, 3
_OUTCOMES = ("dogru", "kismen", "yanlis", "dogru_red", "yersiz_red", "geri_tutuldu", "hata")


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("run", type=Path, help="a results folder with rows.jsonl")
    parser.add_argument("--golden", type=Path, default=Path("eval/golden.jsonl"))
    parser.add_argument("--judge", choices=("ollama", "gemini"), default="ollama")
    parser.add_argument("--model", default=None, help="default: OLLAMA_MODEL or GEMINI_MODEL")
    return parser.parse_args(argv)


def make_judge(kind: str, model: str | None) -> LLMProvider:
    env = merged_env()
    if kind == "gemini":
        return factory.make_gemini({**env, **({"GEMINI_MODEL": model} if model else {})})
    return factory.make_ollama({**env, **({"OLLAMA_MODEL": model} if model else {})})


def main(
    argv: Sequence[str] | None = None,
    provider_factory: Callable[[], LLMProvider] | None = None,
) -> int:
    args = parse_args(argv)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    judgments_path = args.run / "judgments.jsonl"
    try:
        questions = {q.id: q for q in load_golden(args.golden)}
        rows = load_rows(args.run / "rows.jsonl")
        earlier = load_judgments(judgments_path)
    except (GoldenError, OSError, ValueError, TypeError) as exc:
        logger.error("%s", exc)
        return EXIT_FAILED
    unknown = sorted({row.question_id for row in rows} - set(questions))
    if unknown:
        logger.error("questions of %s not in %s: %s", args.run, args.golden, unknown)
        return EXIT_FAILED
    try:
        provider = provider_factory() if provider_factory else make_judge(args.judge, args.model)
    except (LLMError, ValueError) as exc:
        logger.error("the judge model is not usable: %s", exc)
        return EXIT_FAILED

    new, stopped, dead = _judge(rows, questions, provider, earlier, judgments_path)
    by_key = {judgment.key: judgment for judgment in [*earlier, *new]}
    current = [
        by_key[key]
        for row in rows
        if (key := judgment_key(questions[row.question_id], row, provider)) in by_key
    ]
    unscored = len(rows) - len(current)
    if unscored and not stopped:
        stopped = f"{unscored} of {len(rows)} answers not scored (no valid verdict)"
    judge_name = f"{provider.name}/{provider.model}"
    report = render_judge_report(args.run.name, judge_name, current, len(rows), stopped)
    atomic_write_text(args.run / "judge_report.md", report)
    logger.info("judge: %s", summarize_judgments(current))
    if stopped:
        logger.error("not finished: %s. Run the same command later to continue.", stopped)
        return EXIT_FAILED if dead else EXIT_INCOMPLETE
    return EXIT_OK


def _judge(
    rows: Sequence[SmokeRow],
    questions: dict[str, GoldenQuestion],
    provider: LLMProvider,
    earlier: Sequence[Judgment],
    path: Path,
) -> tuple[list[Judgment], str, bool]:
    """New judgments, written as they come; why it stopped early, if it did; and whether the
    judge could not be used."""
    new: list[Judgment] = []
    with path.open("a", encoding="utf-8", newline="\n") as sink:
        try:
            for judgment in judge_rows(rows, questions, provider, {j.key for j in earlier}):
                sink.write(json.dumps(asdict(judgment), ensure_ascii=False) + "\n")
                sink.flush()
                new.append(judgment)
                logger.info(
                    "%s %s (%s)", judgment.question_id, judgment.outcome, judgment.judged_by
                )
        except LLMRateLimited as exc:
            return new, f"quota: {exc}", False
        except LLMUnavailable as exc:
            return new, f"the judge cannot be used: {exc}", True
    return new, "", False


def render_judge_report(
    run: str, judge: str, judgments: Sequence[Judgment], rows: int, stopped: str
) -> str:
    s: dict[str, Any] = summarize_judgments(judgments)
    lines = [
        "# Judge report (M5)",
        "",
        f"- Run `{run}`; judge `{judge}`, rubric {RUBRIC_VERSION}; "
        f"{len(judgments)} of {rows} answers scored.",
        f"- Answerable questions: {s['answerable']}. Correct {s['correct']}; correct or partly "
        f'correct {s["correct_or_partial"]}; wrong {s["wrong"]}; withheld ("doğrulanamadı") '
        f"{s['withheld']}; refused although answerable {s['false_refusals']}.",
        f"- Out-of-scope questions refused: {s['out_of_scope_refused']}. "
        f"False premises corrected: {s['premise_corrected']}.",
        "- Refusals, withheld answers and errors are scored by rule. A judge that is also the "
        "answering model scores its own answers.",
    ]
    if stopped:
        lines.append(f"- **Not finished:** {stopped}. Run the same command again to continue.")
    lines += [
        "",
        "| Category | " + " | ".join(_OUTCOMES) + " |",
        "|---" * (len(_OUTCOMES) + 1) + "|",
    ]
    for category, counts in s["by_category"].items():
        lines.append(
            f"| {category} | " + " | ".join(str(counts.get(o, 0)) for o in _OUTCOMES) + " |"
        )
    lines += [
        "",
        "| Question | Category | Status | Outcome | Judged by | Missing | Unsupported |",
        "|---|---|---|---|---|---|---|",
    ]
    for j in judgments:
        missing = "; ".join(j.missing_points).replace("|", "\\|") or "–"
        unsupported = "; ".join(j.unsupported_claims).replace("|", "\\|") or "–"
        lines.append(
            f"| {j.question_id} | {j.category} | {j.status} | {j.outcome} | {j.judged_by} "
            f"| {missing} | {unsupported} |"
        )
    return "\n".join(lines) + "\n"
