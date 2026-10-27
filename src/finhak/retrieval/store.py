"""Chunks read back from the index: by id, by cited article, or all of them."""

from collections.abc import Sequence
from typing import Any

from finhak.index.db import Connection
from finhak.parsing.chunker import Chunk
from finhak.retrieval.direct_ref import DirectRef

# A range article "38-39" answers a citation of 38 or 39. Talimat sections have no
# madde_kind; they answer plain "madde" citations.
_BY_REF = """
    SELECT data FROM chunks
    WHERE doc_id = %(doc_id)s
      AND (madde = %(madde)s::text OR %(madde)s::text = ANY (string_to_array(madde, '-')))
      AND (madde_kind = %(kind)s::text OR (madde_kind IS NULL AND %(kind)s::text = 'madde'))
    ORDER BY ordinal
"""


class PgChunkStore:
    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def by_ids(self, ids: Sequence[str]) -> dict[str, Chunk]:
        rows = self._conn.execute(
            "SELECT id, data FROM chunks WHERE id = ANY(%s)", (list(ids),)
        ).fetchall()
        return {str(chunk_id): _chunk(data) for chunk_id, data in rows}

    def by_ref(self, ref: DirectRef) -> list[Chunk]:
        params = {"doc_id": ref.doc_id, "madde": ref.madde, "kind": ref.madde_kind}
        return [_chunk(data) for (data,) in self._conn.execute(_BY_REF, params).fetchall()]

    def all(self) -> list[Chunk]:
        rows = self._conn.execute("SELECT data FROM chunks ORDER BY ordinal").fetchall()
        return [_chunk(data) for (data,) in rows]


def _chunk(data: Any) -> Chunk:
    return Chunk.model_validate(data)
