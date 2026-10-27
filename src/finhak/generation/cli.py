"""Ask a question from the command line: retrieval, the model, verified citations.

    python scripts/ask.py "Kredi kartı aidatımı geri alabilir miyim?"
    python scripts/ask.py "TKHK m.22 ne diyor?" --json

The model comes from LLM_PROVIDER (ollama by default; see finhak.llm.factory). Exit codes:
0 an answer (or an out-of-scope reply) was shown, 1 failure (no database or index, the
model is not reachable, …).
"""

import argparse
import json
import logging
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict
from typing import TextIO

import psycopg

from finhak.config import database_url
from finhak.generation.pipeline import (
    DEFAULT_CONFIG,
    DEFAULT_PASSAGES,
    AnswerResult,
    answer_question,
)
from finhak.index.db import Connection, connect
from finhak.index.embed import ModelLoadError, make_embedder
from finhak.index.indexer import IndexMismatch
from finhak.llm.base import LLMError, LLMProvider
from finhak.llm.factory import choose_provider
from finhak.retrieval.hybrid import CONFIGS, Retriever
from finhak.retrieval.pg import open_retriever
from finhak.retrieval.rerank import CrossEncoderReranker

logger = logging.getLogger("finhak.ask")

EXIT_OK, EXIT_FAILED = 0, 1


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("question")
    parser.add_argument("--config", choices=list(CONFIGS), default=DEFAULT_CONFIG)
    parser.add_argument("--passages", type=passages_arg, default=DEFAULT_PASSAGES)
    parser.add_argument("--database-url", default=None, help="default: DATABASE_URL")
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    return parser.parse_args(argv)


MAX_PASSAGES = 20


def passages_arg(value: str) -> int:
    number = int(value)
    if not 1 <= number <= MAX_PASSAGES:
        raise argparse.ArgumentTypeError(f"--passages must be 1..{MAX_PASSAGES}")
    return number


def provider_from_settings(err: TextIO) -> LLMProvider:
    """The configured provider; the fallback notice goes to stderr (stdout may be JSON)."""
    choice = choose_provider()
    if choice.notice:
        err.write(f"Not: {choice.notice}\n")
    return choice.provider


def open_retrieval(conn: Connection, config: str) -> Retriever:
    """The production retriever: bge-m3, the reranker when the config reranks, BM25 if used."""
    cfg = CONFIGS[config]
    reranker = CrossEncoderReranker() if cfg.rerank else None
    uses_bm25 = any(name.startswith("bm25") for name in cfg.retrievers)
    return open_retriever(conn, make_embedder("bge-m3"), reranker, with_bm25=uses_bm25)


def main(
    argv: Sequence[str] | None = None,
    out: TextIO = sys.stdout,
    provider_factory: Callable[[], LLMProvider] | None = None,
    err: TextIO = sys.stderr,
) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    try:
        provider = provider_factory() if provider_factory else provider_from_settings(err)
    except (ValueError, LLMError) as exc:  # e.g. LLM_PROVIDER or OLLAMA_NUM_CTX invalid
        logger.error("language model settings: %s", exc)
        return EXIT_FAILED
    try:
        conn = connect(args.database_url or database_url())
    except psycopg.Error as exc:
        logger.error("database not reachable (docker compose up -d db?): %s", exc)
        return EXIT_FAILED
    with conn:
        try:
            retriever = open_retrieval(conn, args.config)
            result = answer_question(
                args.question, retriever, provider, config=args.config, limit=args.passages
            )
        except (ModelLoadError, IndexMismatch, LLMError, psycopg.Error) as exc:
            logger.error("%s", exc)
            return EXIT_FAILED
    out.write(json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n" if args.json
              else render_answer(result))  # fmt: skip
    return EXIT_OK


def render_answer(result: AnswerResult) -> str:
    lines = [result.answer]
    lines += [f"Not: {note}" for note in result.notes]
    if result.false_premise:
        lines.append("Not: Sorudaki varsayım kaynaklarla çelişiyor.")
    if result.status == "unverified" and result.verification_errors:
        lines += ["", "Doğrulanamayan atıflar:", *(f"- {e}" for e in result.verification_errors)]
    if result.citations:
        lines += ["", "Kaynaklar:"]
        for number, citation in enumerate(result.citations, start=1):
            lines.append(f"[{number}] {citation.label}")
            lines.append(f"    “{citation.quote}”")
            lines += [f"    {note}" for note in citation.notes]
            lines.append(f"    {citation.snapshot} {citation.source_url}")
    lines += ["", result.disclaimer]
    return "\n".join(lines) + "\n"
