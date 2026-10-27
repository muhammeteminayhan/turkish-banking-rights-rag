from collections.abc import Sequence

import pytest

from chunk_factory import make_chunk
from finhak.parsing.chunker import Chunk
from finhak.retrieval.direct_ref import DirectRef
from finhak.retrieval.hybrid import CONFIGS, MAX_CITED_REFS, Retriever, SearchConfig
from finhak.retrieval.types import Scored

pytestmark = pytest.mark.unit

CHUNKS = [
    make_chunk("6502:m22:f1", "Faiz oranı yazılır.", madde="22", fikra=1),
    make_chunk("6502:m22:f2", "Değişken faiz bildirilir.", madde="22", fikra=2),
    make_chunk("6502:m30:f2-5", "Cayma hakkı süresi.", madde="30", fikra=2, fikra_last=5),
    make_chunk("5464:m10:f1", "Kart aidatı alınabilir.", madde="10"),
    make_chunk("5464:m11:f1", "Kart limiti belirlenir.", madde="11"),
    make_chunk("kart-yon:m5:f1", "Aidat iadesi aidat.", madde="5"),
]
BY_ID = {c.id: c for c in CHUNKS}


class FakeLookup:
    def by_ids(self, ids: Sequence[str]) -> dict[str, Chunk]:
        return {i: BY_ID[i] for i in ids if i in BY_ID}

    def by_ref(self, ref: DirectRef) -> list[Chunk]:
        return [c for c in CHUNKS if (c.doc_id, c.madde) == (ref.doc_id, ref.madde)]


class FakeSearcher:
    def __init__(self, ids: list[str]) -> None:
        self.ids = ids
        self.calls: list[tuple[str, int]] = []

    def __call__(self, query: str, k: int) -> list[Scored]:
        self.calls.append((query, k))
        return [Scored(i, 1.0 / (n + 1)) for n, i in enumerate(self.ids)][:k]


class KeywordReranker:
    """Scores a passage by how often it contains the word "aidat"."""

    def __init__(self) -> None:
        self.seen: list[int] = []

    def scores(self, query: str, passages: Sequence[str]) -> list[float]:
        self.seen.append(len(passages))
        return [float(p.lower().count("aidat")) for p in passages]


def _retriever(
    fts: list[str] | None = None,
    vector: list[str] | None = None,
    reranker: KeywordReranker | None = None,
    candidates: int = 30,
) -> Retriever:
    return Retriever(
        searchers={
            "fts": FakeSearcher(fts or ["6502:m22:f1", "5464:m10:f1", "5464:m11:f1"]),
            "bm25": FakeSearcher(["kart-yon:m5:f1"]),
            "vector": FakeSearcher(vector or ["5464:m11:f1", "kart-yon:m5:f1", "6502:m22:f1"]),
        },
        lookup=FakeLookup(),
        reranker=reranker,
        candidates=candidates,
    )


def _ids(retriever: Retriever, query: str, config: str, limit: int = 10) -> list[str]:
    return [r.chunk.id for r in retriever.search(query, config, limit=limit).results]


def test_single_retriever_configs_return_that_ranking() -> None:
    retriever = _retriever()

    assert _ids(retriever, "q", "fts") == ["6502:m22:f1", "5464:m10:f1", "5464:m11:f1"]
    assert _ids(retriever, "q", "bm25") == ["kart-yon:m5:f1"]
    assert _ids(retriever, "q", "fts", limit=2) == ["6502:m22:f1", "5464:m10:f1"]
    assert {r.via for r in retriever.search("q", "fts").results} == {"fts"}


def test_hybrid_fuses_full_text_and_vector_rankings() -> None:
    retriever = _retriever(
        fts=["6502:m22:f1", "5464:m10:f1", "5464:m11:f1"],
        vector=["5464:m11:f1", "kart-yon:m5:f1", "6502:m22:f1"],
    )

    # 22:f1 and 11:f1 tie on 1/61 + 1/63 (best rank 1 each) and sort by id.
    assert _ids(retriever, "q", "hybrid") == [
        "5464:m11:f1",
        "6502:m22:f1",
        "5464:m10:f1",
        "kart-yon:m5:f1",
    ]


def test_hybrid_asks_each_retriever_for_the_candidate_depth() -> None:
    retriever = _retriever(candidates=7)

    retriever.search("q", "hybrid", limit=3)

    fts = retriever.searchers["fts"]
    assert isinstance(fts, FakeSearcher)
    assert fts.calls == [("q", 7)]


def test_rerank_orders_the_fused_candidates_by_the_reranker() -> None:
    reranker = KeywordReranker()
    retriever = _retriever(reranker=reranker, candidates=3)

    results = retriever.search("q", "hybrid_rerank", limit=2).results

    # Fused order is 11:f1, 22:f1, 10:f1, m5; only the first three are candidates, so m5
    # (two "aidat") is never scored. 10:f1 wins; the 0-score tie keeps the fused order.
    assert [r.chunk.id for r in results] == ["5464:m10:f1", "5464:m11:f1"]
    assert results[0].score == 1.0
    assert {r.via for r in results} == {"rerank"}
    assert reranker.seen == [3]


def test_full_config_puts_the_cited_article_first() -> None:
    retriever = _retriever(reranker=KeywordReranker())

    outcome = retriever.search("TKHK m.22 kart aidatı", "full", limit=4)

    ids = [r.chunk.id for r in outcome.results]
    assert ids[:2] == ["6502:m22:f1", "6502:m22:f2"]
    assert ids[2] == "kart-yon:m5:f1"
    assert len(ids) == len(set(ids)) == 4
    assert [r.via for r in outcome.results[:2]] == ["direct", "direct"]
    assert [r.label for r in outcome.refs] == ["6502 md. 22"]
    assert outcome.unmatched_refs == ()


def test_full_config_narrows_to_the_cited_fikra_including_ranges() -> None:
    retriever = _retriever(reranker=KeywordReranker())

    assert _ids(retriever, "TKHK m.22/2", "full")[0] == "6502:m22:f2"
    assert _ids(retriever, "TKHK md. 30/4", "full")[0] == "6502:m30:f2-5"


def test_a_missing_fikra_falls_back_to_the_whole_article() -> None:
    retriever = _retriever(reranker=KeywordReranker())

    assert _ids(retriever, "TKHK m.22/9", "full")[:2] == ["6502:m22:f1", "6502:m22:f2"]


def test_an_article_that_does_not_exist_is_reported() -> None:
    retriever = _retriever(reranker=KeywordReranker())

    outcome = retriever.search("TKHK m.999", "full")

    assert [r.label for r in outcome.unmatched_refs] == ["6502 md. 999"]
    assert [r.chunk.id for r in outcome.results] == _ids(retriever, "TKHK m.999", "hybrid_rerank")


def test_rerank_configs_need_a_reranker() -> None:
    with pytest.raises(ValueError, match="reranker"):
        _retriever().search("q", "hybrid_rerank")


def test_unknown_config_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="hybrid"):
        _retriever().search("q", "nope")


def test_a_config_needing_a_missing_searcher_is_rejected() -> None:
    retriever = Retriever(searchers={}, lookup=FakeLookup(), reranker=None)

    with pytest.raises(ValueError, match="fts"):
        retriever.search("q", SearchConfig("x", ("fts",)))


def test_ids_missing_from_the_store_are_an_error() -> None:
    retriever = _retriever(fts=["6502:m1:f1"])

    with pytest.raises(LookupError, match="6502:m1:f1"):
        retriever.search("q", "fts")


def test_the_named_configs_cover_the_ablation() -> None:
    assert set(CONFIGS) >= {"fts", "bm25", "vector", "hybrid", "hybrid_rerank", "full"}
    assert CONFIGS["full"].direct_refs and CONFIGS["full"].rerank


LONG_ARTICLE = [
    make_chunk(f"6502:m22:f{n}", f"Fıkra {n}." + (" aidat" if n == 4 else ""), madde="22", fikra=n)
    for n in range(1, 7)
]
OTHER = make_chunk("5464:m10:f1", "Kart aidatı aidat alınabilir.", madde="10")


class ManyChunksLookup:
    chunks = (*LONG_ARTICLE, OTHER)

    def by_ids(self, ids: Sequence[str]) -> dict[str, Chunk]:
        return {c.id: c for c in self.chunks if c.id in ids}

    def by_ref(self, ref: DirectRef) -> list[Chunk]:
        return [c for c in self.chunks if (c.doc_id, c.madde) == (ref.doc_id, ref.madde)]


def _many(direct_per_ref: int = 3) -> Retriever:
    searchers = {"fts": FakeSearcher(["5464:m10:f1"]), "vector": FakeSearcher(["6502:m22:f6"])}
    return Retriever(
        searchers=searchers,
        lookup=ManyChunksLookup(),
        reranker=KeywordReranker(),
        direct_per_ref=direct_per_ref,
    )


def test_a_long_cited_article_does_not_crowd_out_a_second_citation() -> None:
    ids = _ids(_many(), "TKHK m.22 ve 5464 m.10", "full", limit=4)

    # Round-robin over the two citations, best-reranked chunks of each first.
    assert ids == ["6502:m22:f4", "5464:m10:f1", "6502:m22:f1", "6502:m22:f2"]


def test_the_cited_chunks_are_ordered_by_the_reranker() -> None:
    ids = _ids(_many(direct_per_ref=6), "TKHK m.22", "full", limit=3)

    assert ids[0] == "6502:m22:f4"  # the only fıkra with "aidat"


def test_search_results_follow_the_capped_citation() -> None:
    ids = _ids(_many(direct_per_ref=2), "TKHK m.22", "full", limit=5)

    assert ids[:2] == ["6502:m22:f4", "6502:m22:f1"]
    assert "5464:m10:f1" in ids[2:]


@pytest.mark.parametrize("limit", [0, -1])
def test_limit_must_be_positive(limit: int) -> None:
    with pytest.raises(ValueError, match="limit"):
        _retriever().search("q", "fts", limit=limit)


def test_settings_are_checked_when_the_retriever_is_made() -> None:
    with pytest.raises(ValueError, match="candidates"):
        Retriever(searchers={}, lookup=FakeLookup(), reranker=None, candidates=0)
    with pytest.raises(ValueError, match="direct_per_ref"):
        Retriever(searchers={}, lookup=FakeLookup(), reranker=None, direct_per_ref=0)


class CountingLookup(FakeLookup):
    def __init__(self) -> None:
        self.ref_calls = 0

    def by_ref(self, ref: DirectRef) -> list[Chunk]:
        self.ref_calls += 1
        return super().by_ref(ref)


def test_only_the_first_cited_articles_are_looked_up() -> None:
    lookup = CountingLookup()
    retriever = Retriever(
        searchers={"fts": FakeSearcher([]), "vector": FakeSearcher([])},
        lookup=lookup,
        reranker=KeywordReranker(),
    )
    query = "TKHK " + " ve ".join(f"m.{n}" for n in (22, 30, 1, 2, 3, 4, 5, 6))

    outcome = retriever.search(query, "full")

    assert lookup.ref_calls == len(outcome.refs) == MAX_CITED_REFS
    # Cited articles take turns: m22, m30, then m22 again.
    assert [r.chunk.id for r in outcome.results[:3]] == [
        "6502:m22:f1",
        "6502:m30:f2-5",
        "6502:m22:f2",
    ]
