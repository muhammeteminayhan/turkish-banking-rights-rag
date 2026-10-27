"""Build the index from chunks: documents, chunks (tsvector + embedding) and metadata."""

import hashlib
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb
from pydantic import ValidationError

from finhak.index.db import Connection
from finhak.index.embed import Embedder
from finhak.index.passages import passage
from finhak.index.schema import INDEX_STATEMENTS, INDEX_TABLES, TSV_EXPRESSION, table_statements
from finhak.parsing.chunker import Chunk
from finhak.textnorm import tr_casefold

SCHEMA_VERSION = "1"
# Serialises concurrent builds; a reader stuck in a transaction fails the build instead
# of blocking it (and every search queued behind its lock) forever.
_BUILD_LOCK_KEY = 0x66696E68  # 'finh'
_LOCK_TIMEOUT = "15s"

_INSERT_DOCUMENT = """
    INSERT INTO documents
        (id, label, title, doc_type, origin, source_url, rg_date, version_date, collected_on)
    VALUES (%(id)s, %(label)s, %(title)s, %(doc_type)s, %(origin)s, %(source_url)s,
            %(rg_date)s, %(version_date)s, %(collected_on)s)
"""
_INSERT_CHUNK = f"""
    INSERT INTO chunks
        (id, doc_id, ordinal, unit, madde, madde_kind, fikra, fikra_last, data, tsv, embedding)
    VALUES (%(id)s, %(doc_id)s, %(ordinal)s, %(unit)s, %(madde)s, %(madde_kind)s, %(fikra)s,
            %(fikra_last)s, %(data)s, {TSV_EXPRESSION}, %(embedding)s)
"""


class IndexMismatch(RuntimeError):
    """The database holds no index, or one built with a different embedder."""


@dataclass(frozen=True)
class IndexStats:
    documents: int
    chunks: int
    embedder: str
    dim: int
    embed_seconds: float
    total_seconds: float


def load_chunks(path: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    with path.open(encoding="utf-8") as lines:
        for number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                chunks.append(Chunk.model_validate_json(line))
            except ValidationError as exc:
                raise ValueError(f"{path}:{number}: not a chunk: {exc}") from exc
    return chunks


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_index(
    conn: Connection, chunks: Sequence[Chunk], embedder: Embedder, *, source_sha256: str
) -> IndexStats:
    """Replace whatever index the connection's schema holds with one built from `chunks`."""
    if not chunks:
        raise ValueError("no chunks to index")
    ids = [chunk.id for chunk in chunks]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate chunk ids")
    started = time.perf_counter()
    vectors = embedder.embed([passage(chunk) for chunk in chunks])  # outside the transaction
    if vectors.shape != (len(chunks), embedder.dim):
        expected = (len(chunks), embedder.dim)
        raise ValueError(f"embedder returned shape {vectors.shape}, expected {expected}")
    embedded = time.perf_counter()

    documents = _documents(chunks)
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(f"SET LOCAL lock_timeout = '{_LOCK_TIMEOUT}'")
        cur.execute("SELECT pg_advisory_xact_lock(%s)", (_BUILD_LOCK_KEY,))
        _drop_existing(cur)
        for statement in table_statements(embedder.dim):
            cur.execute(statement)
        cur.executemany(_INSERT_DOCUMENT, documents)
        cur.executemany(
            _INSERT_CHUNK,
            [_chunk_row(n, chunk, vectors[n]) for n, chunk in enumerate(chunks)],
        )
        for statement in INDEX_STATEMENTS:
            cur.execute(statement)
        meta = {
            "schema_version": SCHEMA_VERSION,
            "embedder": embedder.name,
            "dim": str(embedder.dim),
            "chunks": str(len(chunks)),
            "source_sha256": source_sha256,
            "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        cur.executemany("INSERT INTO index_meta (key, value) VALUES (%s, %s)", list(meta.items()))
    conn.execute("ANALYZE chunks")
    return IndexStats(
        documents=len(documents),
        chunks=len(chunks),
        embedder=embedder.name,
        dim=embedder.dim,
        embed_seconds=round(embedded - started, 2),
        total_seconds=round(time.perf_counter() - started, 2),
    )


def check_index(conn: Connection, embedder: Embedder) -> dict[str, str]:
    """The index metadata, after checking that queries will be embedded the same way."""
    try:
        rows = conn.execute("SELECT key, value FROM index_meta").fetchall()
    except psycopg.errors.UndefinedTable as exc:
        raise IndexMismatch(
            "no index here; build it first (scripts/build_index.py → build_index)"
        ) from exc
    meta = {str(key): str(value) for key, value in rows}
    if meta.get("embedder") != embedder.name or meta.get("dim") != str(embedder.dim):
        raise IndexMismatch(
            f"index was built with {meta.get('embedder')} (dim {meta.get('dim')}); "
            f"queries would use {embedder.name} (dim {embedder.dim})"
        )
    return meta


def _drop_existing(cur: psycopg.Cursor[TupleRow]) -> None:
    """Drop the index tables of the schema the new ones go into, and only those.

    An unqualified DROP follows the search path: with "test, public" and no tables in
    "test" yet, it would drop public's index.
    """
    row = cur.execute("SELECT current_schema()").fetchone()
    if row is None or row[0] is None:
        raise RuntimeError("no current schema: the search_path names no existing schema")
    tables = sql.SQL(", ").join(sql.Identifier(str(row[0]), table) for table in INDEX_TABLES)
    cur.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(tables))


def _documents(chunks: Sequence[Chunk]) -> list[dict[str, Any]]:
    first: dict[str, Chunk] = {}
    for chunk in chunks:
        first.setdefault(chunk.doc_id, chunk)
    return [
        {
            "id": c.doc_id,
            "label": c.doc_label,
            "title": c.doc_title,
            "doc_type": c.doc_type,
            "origin": c.origin,
            "source_url": c.source_url,
            "rg_date": c.rg_date,
            "version_date": c.version_date,
            "collected_on": c.collected_on,
        }
        for c in first.values()
    ]


def _chunk_row(ordinal: int, chunk: Chunk, vector: Any) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "doc_id": chunk.doc_id,
        "ordinal": ordinal,
        "unit": chunk.unit,
        "madde": chunk.madde,
        "madde_kind": chunk.madde_kind,
        "fikra": chunk.fikra,
        "fikra_last": chunk.fikra_last,
        "data": Jsonb(chunk.model_dump(mode="json")),
        "fts_title": tr_casefold(chunk.madde_title or ""),
        "fts_body": tr_casefold(chunk.text),
        "fts_notes": tr_casefold(" ".join(chunk.notes)),
        "fts_label": tr_casefold(chunk.doc_label),
        "embedding": vector,
    }
