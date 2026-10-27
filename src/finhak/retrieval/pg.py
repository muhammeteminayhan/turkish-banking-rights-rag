"""Wire a Retriever to the PostgreSQL index, the embedder and the reranker."""

from functools import partial

from finhak.index.db import Connection
from finhak.index.embed import Embedder
from finhak.index.indexer import check_index
from finhak.retrieval.bm25 import Bm25Index
from finhak.retrieval.hybrid import DEFAULT_CANDIDATES, Retriever
from finhak.retrieval.lexical import fts_search
from finhak.retrieval.rerank import Reranker
from finhak.retrieval.store import PgChunkStore
from finhak.retrieval.types import Scored, Searcher
from finhak.retrieval.vector import vector_search


def open_retriever(
    conn: Connection,
    embedder: Embedder,
    reranker: Reranker | None,
    candidates: int = DEFAULT_CANDIDATES,
    with_bm25: bool = True,
) -> Retriever:
    """Check the index was built with `embedder`; BM25 indexes are built in memory."""
    check_index(conn, embedder)
    store = PgChunkStore(conn)

    def vector(query: str, k: int) -> list[Scored]:
        return vector_search(conn, embedder.embed([query])[0], k)

    searchers: dict[str, Searcher] = {"fts": partial(fts_search, conn), "vector": vector}
    if with_bm25:
        chunks = store.all()
        searchers["bm25"] = Bm25Index.from_chunks(chunks, stemmer="snowball").search
        searchers["bm25_prefix5"] = Bm25Index.from_chunks(chunks, stemmer="prefix5").search
    return Retriever(searchers=searchers, lookup=store, reranker=reranker, candidates=candidates)
