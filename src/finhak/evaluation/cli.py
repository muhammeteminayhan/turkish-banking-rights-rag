"""Retrieval evaluation on golden questions: Recall@k and MRR for each search config.

    python eval/run_retrieval.py --golden eval/drafts/batch1.jsonl
    python eval/run_retrieval.py --golden eval/golden.jsonl --configs fts,vector,full

Writes eval/results/<date>_<time>_retrieval_<golden name>/ with metrics.json, report.md and
per_question.jsonl. Numbers from draft (unapproved) questions are marked as drafts.
Exit codes: 0 success, 1 failure.
"""

import argparse
import hashlib
import json
import logging
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg

from finhak.config import database_url
from finhak.evaluation.golden import GoldenError, GoldenQuestion, load_golden, unknown_chunk_ids
from finhak.evaluation.retrieval import QuestionScore, Summary, madde_key, score_question, summarize
from finhak.fsutil import atomic_write_text
from finhak.index.db import Connection, connect
from finhak.index.embed import ModelLoadError, make_embedder
from finhak.index.indexer import IndexMismatch, check_index
from finhak.retrieval.hybrid import CONFIGS, Retriever
from finhak.retrieval.pg import open_retriever
from finhak.retrieval.rerank import CrossEncoderReranker

logger = logging.getLogger("finhak.eval_retrieval")

EXIT_OK, EXIT_FAILED = 0, 1
DEFAULT_CONFIGS = tuple(CONFIGS)
LIMIT = 10


@dataclass(frozen=True)
class ConfigResult:
    summary: Summary
    scores: tuple[QuestionScore, ...]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--golden", type=Path, default=Path("eval/golden.jsonl"))
    parser.add_argument("--configs", default=",".join(DEFAULT_CONFIGS))
    parser.add_argument("--out-dir", type=Path, default=Path("eval/results"))
    parser.add_argument("--database-url", default=None, help="default: DATABASE_URL")
    parser.add_argument("--embedder", choices=["bge-m3", "hashing"], default="bge-m3")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    configs = [name.strip() for name in args.configs.split(",") if name.strip()]
    unknown = [name for name in configs if name not in CONFIGS]
    if unknown or not configs:
        logger.error("unknown configs %s; choose from %s", unknown, ", ".join(CONFIGS))
        return EXIT_FAILED
    try:
        questions = load_golden(args.golden)
    except GoldenError as exc:
        logger.error("%s", exc)
        return EXIT_FAILED
    try:
        conn = connect(args.database_url or database_url())
    except psycopg.Error as exc:
        logger.error("database not reachable (docker compose up -d db?): %s", exc)
        return EXIT_FAILED
    with conn:
        return _evaluate(conn, args, questions, configs)


def _evaluate(
    conn: Connection, args: argparse.Namespace, questions: list[GoldenQuestion], configs: list[str]
) -> int:
    needs_rerank = any(CONFIGS[name].rerank for name in configs)
    try:
        embedder = make_embedder(args.embedder)
        meta = check_index(conn, embedder)
        reranker = CrossEncoderReranker() if needs_rerank else None
        retriever = open_retriever(conn, embedder, reranker)
    except (ModelLoadError, IndexMismatch) as exc:
        logger.error("%s", exc)
        return EXIT_FAILED
    known = {str(chunk_id) for (chunk_id,) in conn.execute("SELECT id FROM chunks").fetchall()}
    missing = unknown_chunk_ids(questions, known)
    if missing:
        logger.error("expected chunks not in the index: %s", missing)
        return EXIT_FAILED

    results = run_configs(retriever, questions, configs)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")  # never overwrite an earlier run
    out = args.out_dir / f"{stamp}_retrieval_{args.golden.stem}"
    write_results(
        out,
        golden=args.golden,
        questions=questions,
        results=results,
        context={
            "index": meta,
            "reranker": getattr(reranker, "name", None),
            "candidates": retriever.candidates,
            "limit": LIMIT,
        },
    )
    logger.info("wrote %s", out)
    return EXIT_OK


def run_configs(
    retriever: Retriever, questions: Sequence[GoldenQuestion], configs: Sequence[str]
) -> dict[str, ConfigResult]:
    answerable = [q for q in questions if q.answerable]
    if not answerable:
        raise ValueError("no answerable questions to evaluate")
    results: dict[str, ConfigResult] = {}
    for name in configs:
        retriever.search(answerable[0].question, name, limit=LIMIT)  # warm-up, not timed
        scores = []
        for question in answerable:
            started = time.perf_counter()
            outcome = retriever.search(question.question, name, limit=LIMIT)
            latency_ms = (time.perf_counter() - started) * 1000
            ranked = [r.chunk.id for r in outcome.results]
            scores.append(score_question(question, ranked, latency_ms=round(latency_ms, 1)))
        results[name] = ConfigResult(summarize(scores), tuple(scores))
        logger.info("%s: %s", name, results[name].summary.madde)
    return results


def write_results(
    out: Path,
    golden: Path,
    questions: Sequence[GoldenQuestion],
    results: dict[str, ConfigResult],
    context: dict[str, Any],
) -> None:
    statuses = {s: sum(1 for q in questions if q.status == s) for s in ("draft", "approved")}
    metrics = {
        "golden": golden.as_posix(),
        "golden_sha256": hashlib.sha256(golden.read_bytes()).hexdigest(),
        "questions": len(questions),
        "scored": sum(1 for q in questions if q.answerable),
        "status": statuses,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        **context,
        "configs": {name: asdict(result.summary) for name, result in results.items()},
    }
    expected = {q.id: list(q.expected_chunks) for q in questions}
    per_question = "".join(
        json.dumps({"config": name, **asdict(s), "expected": expected[s.question_id]},
                   ensure_ascii=False) + "\n"
        for name, result in results.items()
        for s in result.scores
    )  # fmt: skip
    metrics_json = json.dumps(metrics, ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(out / "metrics.json", metrics_json)
    atomic_write_text(out / "per_question.jsonl", per_question)
    atomic_write_text(out / "report.md", render_report(metrics, results, questions))


def render_report(
    metrics: dict[str, Any], results: dict[str, ConfigResult], questions: Sequence[GoldenQuestion]
) -> str:
    index = metrics.get("index", {})
    lines = [f"# Retrieval evaluation: `{metrics['golden']}`", ""]
    if metrics["status"]["draft"]:
        lines += [
            f"> **Draft numbers.** {metrics['status']['draft']} of {metrics['questions']} "
            "questions are not approved yet.",
            "",
        ]
    lines += [
        f"- Questions: {metrics['questions']}; scored {metrics['scored']} "
        f"(out-of-scope questions have no expected chunks and are skipped).",
        f"- Index: {index.get('chunks', '?')} chunks, embedder `{index.get('embedder', '?')}`, "
        f"built {index.get('built_at', '?')}.",
        f"- Reranker: `{metrics.get('reranker')}`; candidates per retriever "
        f"{metrics.get('candidates')}; results kept {metrics.get('limit')}.",
        "",
        "## Overall",
        "",
        "| Config | Chunk R@5 | Chunk R@10 | Chunk MRR | Madde R@5 | Madde R@10 | Madde MRR "
        "| p50 ms | p95 ms |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for name, result in results.items():
        s = result.summary
        lines.append(
            f"| `{name}` | {s.chunk['recall@5']:.3f} | {s.chunk['recall@10']:.3f} "
            f"| {s.chunk['mrr']:.3f} | {s.madde['recall@5']:.3f} | {s.madde['recall@10']:.3f} "
            f"| {s.madde['mrr']:.3f} | {s.latency_ms['p50']:.0f} | {s.latency_ms['p95']:.0f} |"
        )
    categories = sorted({c for r in results.values() for c in r.summary.by_category})
    lines += [
        "",
        "## Madde Recall@5 by category",
        "",
        "| Config | " + " | ".join(f"{c} (n={_n(results, c)})" for c in categories) + " |",
        "|---|" + "---|" * len(categories),
    ]
    for name, result in results.items():
        cells = [f"{result.summary.by_category[c]['madde_recall@5']:.3f}" for c in categories]
        lines.append(f"| `{name}` | " + " | ".join(cells) + " |")
    lines += _citation_table(results)
    lines += _misses(results, questions)
    return "\n".join(lines) + "\n"


def _citation_table(results: dict[str, ConfigResult]) -> list[str]:
    """Questions that name their article are partly a lookup for the direct-ref configs."""
    first = next(iter(results.values())).summary.by_citation
    groups = [g for g in ("cites_article", "no_citation") if g in first]
    lines = [
        "",
        "## Madde Recall@5: questions that cite an article vs. the rest",
        "",
        "| Config | " + " | ".join(f"{g} (n={int(first[g]['n'])})" for g in groups) + " |",
        "|---|" + "---|" * len(groups),
    ]
    for name, result in results.items():
        cells = [f"{result.summary.by_citation[g]['madde_recall@5']:.3f}" for g in groups]
        lines.append(f"| `{name}` | " + " | ".join(cells) + " |")
    return lines


def _n(results: dict[str, ConfigResult], category: str) -> int:
    first = next(iter(results.values()))
    return int(first.summary.by_category[category]["n"])


def _misses(results: dict[str, ConfigResult], questions: Sequence[GoldenQuestion]) -> list[str]:
    name = "full" if "full" in results else list(results)[-1]
    by_id = {q.id: q for q in questions}
    misses = [s for s in results[name].scores if s.madde["recall@5"] < 1.0]
    lines = ["", f"## `{name}`: questions whose expected articles are not all in the top 5", ""]
    if not misses:
        return [*lines, "None."]
    lines += ["| Question | Category | Expected articles | Top 3 retrieved |", "|---|---|---|---|"]
    for score in misses:
        question = by_id[score.question_id]
        wanted = ", ".join(sorted({madde_key(c) for c in question.expected_chunks}))
        top = ", ".join(score.ranked[:3])
        lines.append(f"| {question.id} | {question.category} | {wanted} | {top} |")
    return lines
