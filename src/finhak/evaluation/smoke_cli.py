"""Run the M4 smoke set end to end and write a report.

    python eval/smoke_ask.py                      # eval/smoke.txt ids from the draft batch
    python eval/smoke_ask.py --golden eval/golden.jsonl

Needs PostgreSQL with the index, the models and a reachable LLM (Ollama by default).
Writes eval/results/<date>_<time>_smoke/ with report.md and rows.jsonl.
Exit codes: 0 success, 1 failure (the LLM, the database or the questions missing).
"""

import argparse
import json
import logging
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import TextIO

import psycopg

from finhak.config import database_url
from finhak.evaluation.golden import GoldenError, load_golden
from finhak.evaluation.smoke import load_smoke_ids, render_smoke, run_smoke, summarize_smoke
from finhak.fsutil import atomic_write_text
from finhak.generation.cli import open_retrieval, provider_from_settings
from finhak.generation.pipeline import DEFAULT_CONFIG, answer_question
from finhak.index.db import connect
from finhak.index.embed import ModelLoadError
from finhak.index.indexer import IndexMismatch
from finhak.llm.base import LLMError, LLMProvider, LLMUnavailable
from finhak.llm.ollama import OllamaProvider
from finhak.retrieval.hybrid import CONFIGS

logger = logging.getLogger("finhak.smoke")

EXIT_OK, EXIT_FAILED = 0, 1


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--golden", type=Path, default=Path("eval/drafts/batch1.jsonl"))
    parser.add_argument("--ids", type=Path, default=Path("eval/smoke.txt"))
    parser.add_argument("--config", choices=list(CONFIGS), default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", type=Path, default=Path("eval/results"))
    parser.add_argument("--database-url", default=None, help="default: DATABASE_URL")
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    out: TextIO = sys.stdout,
    provider_factory: Callable[[], LLMProvider] | None = None,
) -> int:
    args = parse_args(argv)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        by_id = {q.id: q for q in load_golden(args.golden)}
        ids = load_smoke_ids(args.ids)
    except (GoldenError, OSError) as exc:
        logger.error("%s", exc)
        return EXIT_FAILED
    missing = [qid for qid in ids if qid not in by_id]
    if missing or not ids:
        logger.error("smoke ids not in %s: %s", args.golden, missing or "(none given)")
        return EXIT_FAILED

    try:
        provider = _provider(provider_factory, sys.stderr)
    except (LLMError, ValueError) as exc:  # unreachable, not pulled, or bad settings
        logger.error("the language model is not usable: %s", exc)
        return EXIT_FAILED
    try:
        conn = connect(args.database_url or database_url())
    except psycopg.Error as exc:
        logger.error("database not reachable (docker compose up -d db?): %s", exc)
        return EXIT_FAILED
    with conn:
        try:
            retriever = open_retrieval(conn, args.config)
            rows = run_smoke(
                [by_id[qid] for qid in ids],
                lambda q: answer_question(q, retriever, provider, config=args.config),
            )
        except (ModelLoadError, IndexMismatch, psycopg.Error) as exc:
            logger.error("%s", exc)
            return EXIT_FAILED

    summary = summarize_smoke(rows)
    context = {"provider": provider.name, "model": provider.model, "config": args.config}
    folder = args.out_dir / f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_smoke"
    atomic_write_text(folder / "report.md", render_smoke(rows, summary, context))
    atomic_write_text(
        folder / "rows.jsonl",
        "".join(json.dumps(asdict(row), ensure_ascii=False) + "\n" for row in rows),
    )
    logger.info("smoke: %s → %s", summary, folder)
    return EXIT_OK


def _provider(factory: Callable[[], LLMProvider] | None, err: TextIO) -> LLMProvider:
    if factory is not None:
        return factory()
    provider = provider_from_settings(err)
    if isinstance(provider, OllamaProvider) and provider.model not in provider.available_models():
        raise LLMUnavailable(f"Ollama is running but has no {provider.model}: ollama pull it")
    return provider
