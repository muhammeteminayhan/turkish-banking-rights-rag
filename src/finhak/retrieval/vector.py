"""pgvector cosine search over the chunk embeddings (HNSW index)."""

import numpy as np
from numpy.typing import NDArray

from finhak.index.db import Connection
from finhak.retrieval.types import Scored

# HNSW returns at most ef_search rows per scan; keep it well above the candidate depth.
EF_SEARCH = 100


def vector_search(conn: Connection, embedding: NDArray[np.float32], k: int) -> list[Scored]:
    if not 0 < k <= EF_SEARCH:
        raise ValueError(f"k must be 1..{EF_SEARCH}, got {k}")
    with conn.transaction():
        conn.execute(f"SET LOCAL hnsw.ef_search = {EF_SEARCH}")
        rows = conn.execute(
            "SELECT id, 1 - (embedding <=> %(v)s) AS score FROM chunks"
            " ORDER BY embedding <=> %(v)s LIMIT %(k)s",
            {"v": embedding, "k": k},
        ).fetchall()
    return [Scored(str(chunk_id), float(score)) for chunk_id, score in rows]
