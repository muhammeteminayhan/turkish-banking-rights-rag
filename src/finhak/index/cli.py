"""Build the retrieval index from data/processed/chunks.jsonl.

    docker compose up -d db
    python scripts/build_index.py                     # bge-m3, on the GPU if there is one
    python scripts/build_index.py --embedder hashing  # no model; smoke tests only

The database comes from DATABASE_URL (environment or .env). The index is rebuilt from
scratch each time. Exit codes: 0 success, 1 failure.
"""

import argparse
import json
import logging
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import get_args

import psycopg

from finhak.config import database_url
from finhak.index.db import connect
from finhak.index.embed import Embedder, EmbedderKind, ModelLoadError, make_embedder
from finhak.index.indexer import build_index, file_sha256, load_chunks

logger = logging.getLogger("finhak.build_index")

EXIT_OK, EXIT_FAILED = 0, 1


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--chunks", type=Path, default=Path("data/processed/chunks.jsonl"))
    parser.add_argument("--database-url", default=None, help="default: DATABASE_URL")
    parser.add_argument("--embedder", choices=get_args(EmbedderKind), default="bge-m3")
    parser.add_argument("--device", default=None, help="cuda or cpu (default: cuda if found)")
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    embedder_factory: Callable[[argparse.Namespace], Embedder] | None = None,
) -> int:
    args = parse_args(argv)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        chunks = load_chunks(args.chunks)
        source_sha256 = file_sha256(args.chunks)
    except (OSError, ValueError) as exc:
        logger.error("cannot read chunks: %s (run scripts/parse_sources.py)", exc)
        return EXIT_FAILED

    factory = embedder_factory or _default_embedder
    try:
        embedder = factory(args)
    except ModelLoadError as exc:
        logger.error("%s", exc)
        return EXIT_FAILED
    url = args.database_url or database_url()
    try:
        conn = connect(url, create_extension=True)
    except psycopg.Error as exc:
        logger.error("database not reachable (docker compose up -d db?): %s", exc)
        return EXIT_FAILED
    with conn:
        logger.info("embedding %d chunks with %s", len(chunks), embedder.name)
        stats = build_index(conn, chunks, embedder, source_sha256=source_sha256)
    logger.info("index built: %s", json.dumps(asdict(stats)))
    return EXIT_OK


def _default_embedder(args: argparse.Namespace) -> Embedder:
    return make_embedder(args.embedder, device=args.device, show_progress=True)
