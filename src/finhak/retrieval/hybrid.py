"""The retrieval pipeline: retrievers → RRF → reranker, with cited articles put first.

Named configurations are the M3 ablation rows. "full" is what M4 generation uses:
PostgreSQL FTS + bge-m3 vectors fused with RRF, reranked, and any article the question
cites ("TKHK m.22") placed ahead of the search results.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import zip_longest
from typing import Literal, Protocol

from finhak.index.passages import passage
from finhak.parsing.chunker import Chunk
from finhak.retrieval.direct_ref import DirectRef, find_direct_refs
from finhak.retrieval.fusion import reciprocal_rank_fusion
from finhak.retrieval.rerank import Reranker
from finhak.retrieval.types import Searcher

DEFAULT_CANDIDATES = 30  # each retriever's depth before fusion, and the reranker's input
DEFAULT_LIMIT = 10
# Chunks of one cited article placed first (an article can have 30+ fıkra); the rest of
# the article can still come back through search.
DEFAULT_DIRECT_PER_REF = 3
MAX_CITED_REFS = 5  # more citations in one question are not looked up

# How a result was ranked; a single-retriever config uses that retriever's name instead.
Via = Literal["direct", "rerank", "fusion"]


@dataclass(frozen=True)
class SearchConfig:
    name: str
    retrievers: tuple[str, ...]  # keys of Retriever.searchers
    rerank: bool = False
    direct_refs: bool = False


CONFIGS: dict[str, SearchConfig] = {
    c.name: c
    for c in (
        SearchConfig("fts", ("fts",)),
        SearchConfig("bm25", ("bm25",)),
        SearchConfig("bm25_prefix5", ("bm25_prefix5",)),
        SearchConfig("vector", ("vector",)),
        SearchConfig("hybrid", ("fts", "vector")),
        SearchConfig("hybrid_rerank", ("fts", "vector"), rerank=True),
        SearchConfig("full", ("fts", "vector"), rerank=True, direct_refs=True),
        # The same pipeline with BM25 (prefix-5 stems) as the lexical leg instead of FTS.
        SearchConfig("hybrid_bm25", ("bm25_prefix5", "vector")),
        SearchConfig("hybrid_bm25_rerank", ("bm25_prefix5", "vector"), rerank=True),
        SearchConfig("full_bm25", ("bm25_prefix5", "vector"), rerank=True, direct_refs=True),
    )
}


class ChunkLookup(Protocol):
    def by_ids(self, ids: Sequence[str]) -> dict[str, Chunk]: ...

    def by_ref(self, ref: DirectRef) -> list[Chunk]: ...


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    # On the scale of `via`: retriever score, RRF or reranker score. Cited chunks carry the
    # reranker score when the config reranks, else 1.0.
    score: float
    via: str  # a Via, or the retriever's name for a single-retriever config


@dataclass(frozen=True)
class SearchOutcome:
    results: tuple[RetrievedChunk, ...]
    refs: tuple[DirectRef, ...]  # articles the question cites
    unmatched_refs: tuple[DirectRef, ...]  # cited articles that are not in the corpus


@dataclass(frozen=True)
class Retriever:
    searchers: Mapping[str, Searcher]
    lookup: ChunkLookup
    reranker: Reranker | None
    candidates: int = DEFAULT_CANDIDATES
    direct_per_ref: int = DEFAULT_DIRECT_PER_REF

    def __post_init__(self) -> None:
        if self.candidates < 1:
            raise ValueError(f"candidates must be positive, got {self.candidates}")
        if self.direct_per_ref < 1:
            raise ValueError(f"direct_per_ref must be positive, got {self.direct_per_ref}")

    def search(
        self, query: str, config: SearchConfig | str, limit: int = DEFAULT_LIMIT
    ) -> SearchOutcome:
        if limit < 1:
            raise ValueError(f"limit must be positive, got {limit}")
        cfg = self._config(config)
        refs = find_direct_refs(query)[:MAX_CITED_REFS] if cfg.direct_refs else ()
        cited, unmatched = self._cited(refs)

        ranked = self._ranked(query, cfg, limit)
        chunks = self._chunks([chunk_id for chunk_id, _ in ranked])
        if cfg.rerank:
            pool = [chunks[chunk_id] for chunk_id, _ in ranked[: max(self.candidates, limit)]]
            results = self._reranked(query, pool, via="rerank")
        else:
            via = cfg.retrievers[0] if len(cfg.retrievers) == 1 else "fusion"
            results = [RetrievedChunk(chunks[chunk_id], s, via) for chunk_id, s in ranked]

        if cited:
            head = self._head(query, cited, rerank=cfg.rerank)
            placed = {r.chunk.id for r in head}
            results = head + [r for r in results if r.chunk.id not in placed]
        return SearchOutcome(tuple(results[:limit]), refs, tuple(unmatched))

    def _head(self, query: str, cited: Sequence[list[Chunk]], rerank: bool) -> list[RetrievedChunk]:
        """The best `direct_per_ref` chunks of each cited article, taken in turn."""
        per_ref = [
            (
                self._reranked(query, chunks, via="direct")
                if rerank
                else [RetrievedChunk(chunk, 1.0, "direct") for chunk in chunks]
            )[: self.direct_per_ref]
            for chunks in cited
        ]
        return [r for turn in zip_longest(*per_ref) for r in turn if r is not None]

    def _config(self, config: SearchConfig | str) -> SearchConfig:
        if isinstance(config, str):
            if config not in CONFIGS:
                raise ValueError(f"unknown config {config!r}; choose from {', '.join(CONFIGS)}")
            config = CONFIGS[config]
        missing = [name for name in config.retrievers if name not in self.searchers]
        if missing:
            raise ValueError(f"config {config.name!r} needs searchers {missing}")
        if config.rerank and self.reranker is None:
            raise ValueError(f"config {config.name!r} needs a reranker")
        return config

    def _cited(self, refs: Sequence[DirectRef]) -> tuple[list[list[Chunk]], list[DirectRef]]:
        """Chunks per cited article (a chunk cited twice is kept the first time)."""
        cited: list[list[Chunk]] = []
        unmatched: list[DirectRef] = []
        seen: set[str] = set()
        for ref in refs:
            found = _narrow_to_fikra(self.lookup.by_ref(ref), ref.fikra)
            if not found:
                unmatched.append(ref)
            fresh = [chunk for chunk in found if chunk.id not in seen]
            seen.update(chunk.id for chunk in fresh)
            if fresh:
                cited.append(fresh)
        return cited, unmatched

    def _ranked(self, query: str, cfg: SearchConfig, limit: int) -> list[tuple[str, float]]:
        deep = cfg.rerank or len(cfg.retrievers) > 1
        depth = max(self.candidates, limit) if deep else limit
        hits = [self.searchers[name](query, depth) for name in cfg.retrievers]
        if len(hits) == 1:
            return [(hit.chunk_id, hit.score) for hit in hits[0]]
        return reciprocal_rank_fusion([[hit.chunk_id for hit in ranking] for ranking in hits])

    def _chunks(self, ids: Sequence[str]) -> dict[str, Chunk]:
        found = self.lookup.by_ids(ids)
        missing = [chunk_id for chunk_id in ids if chunk_id not in found]
        if missing:
            raise LookupError(f"search returned ids missing from the chunk store: {missing[:5]}")
        return found

    def _reranked(self, query: str, pool: Sequence[Chunk], via: Via) -> list[RetrievedChunk]:
        assert self.reranker is not None  # checked in _config
        scores = self.reranker.scores(query, [passage(chunk) for chunk in pool])
        if len(scores) != len(pool):
            raise ValueError(f"reranker returned {len(scores)} scores for {len(pool)} passages")
        order = sorted(range(len(pool)), key=lambda i: (-scores[i], i))  # ties keep pool order
        return [RetrievedChunk(pool[i], scores[i], via) for i in order]


def _narrow_to_fikra(chunks: list[Chunk], fikra: int | None) -> list[Chunk]:
    """The cited fıkra (a range "f2-5" covers 4); the whole article if it has no such fıkra."""
    if fikra is None:
        return chunks
    hits = [
        c for c in chunks if c.fikra is not None and c.fikra <= fikra <= (c.fikra_last or c.fikra)
    ]
    return hits or chunks
