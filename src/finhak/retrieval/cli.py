"""Search the index from the command line.

    python scripts/search.py "Kredi kartı aidatımı geri alabilir miyim?"
    python scripts/search.py "TKHK m.22" --config full --limit 5
    python scripts/search.py "EFT ücreti" --config fts --json

Exit codes: 0 success, 1 failure (no index, database unreachable, …).
"""

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from typing import TextIO

import psycopg

from finhak.config import database_url
from finhak.index.db import connect
from finhak.index.embed import ModelLoadError, make_embedder
from finhak.index.indexer import IndexMismatch
from finhak.index.passages import heading
from finhak.retrieval.hybrid import CONFIGS, SearchOutcome
from finhak.retrieval.pg import open_retriever
from finhak.retrieval.rerank import CrossEncoderReranker

logger = logging.getLogger("finhak.search")

EXIT_OK, EXIT_FAILED = 0, 1
_PREVIEW_CHARS = 220
MAX_LIMIT = 50


def _limit(value: str) -> int:
    number = int(value)
    if not 1 <= number <= MAX_LIMIT:
        raise argparse.ArgumentTypeError(f"--limit must be 1..{MAX_LIMIT}")
    return number


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("query")
    parser.add_argument("--config", choices=list(CONFIGS), default="full")
    parser.add_argument("--limit", type=_limit, default=8)
    parser.add_argument("--database-url", default=None, help="default: DATABASE_URL")
    parser.add_argument("--embedder", choices=["bge-m3", "hashing"], default="bge-m3")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, out: TextIO = sys.stdout) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    config = CONFIGS[args.config]
    try:
        conn = connect(args.database_url or database_url())
    except psycopg.Error as exc:
        logger.error("database not reachable (docker compose up -d db?): %s", exc)
        return EXIT_FAILED
    with conn:
        uses_bm25 = any(name.startswith("bm25") for name in config.retrievers)
        try:
            embedder = make_embedder(args.embedder)
            reranker = CrossEncoderReranker() if config.rerank else None
            retriever = open_retriever(conn, embedder, reranker, with_bm25=uses_bm25)
        except (ModelLoadError, IndexMismatch) as exc:
            logger.error("%s", exc)
            return EXIT_FAILED
        outcome = retriever.search(args.query, config, limit=args.limit)
    out.write(_as_json(outcome) if args.json else _as_text(outcome))
    return EXIT_OK


def _as_text(outcome: SearchOutcome) -> str:
    lines = []
    if outcome.refs:
        lines.append("Cited: " + ", ".join(ref.label for ref in outcome.refs))
    if outcome.unmatched_refs:
        lines.append("Not in the corpus: " + ", ".join(r.label for r in outcome.unmatched_refs))
    for rank, result in enumerate(outcome.results, start=1):
        chunk = result.chunk
        text = " ".join(chunk.text.split())
        lines.append(f"{rank:>2}. [{result.via} {result.score:.4f}] {chunk.id}")
        lines.append(f"    {heading(chunk)}")
        lines.append(f"    {text[:_PREVIEW_CHARS]}{'…' if len(text) > _PREVIEW_CHARS else ''}")
    return "\n".join(lines) + "\n"


def _as_json(outcome: SearchOutcome) -> str:
    payload = {
        "refs": [ref.label for ref in outcome.refs],
        "unmatched_refs": [ref.label for ref in outcome.unmatched_refs],
        "results": [
            {"id": r.chunk.id, "via": r.via, "score": r.score, "heading": heading(r.chunk)}
            for r in outcome.results
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
