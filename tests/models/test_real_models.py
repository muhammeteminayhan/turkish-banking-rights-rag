"""bge-m3 and bge-reranker-v2-m3 as pinned in the code. Skipped when sentence-transformers
is not installed or the models are not in the local Hugging Face cache (e.g. in CI)."""

import numpy as np
import pytest

from finhak.index.embed import BGE_M3, ModelRef, SentenceTransformerEmbedder
from finhak.retrieval.rerank import BGE_RERANKER, CrossEncoderReranker

pytestmark = pytest.mark.models

st = pytest.importorskip("sentence_transformers")
hub = pytest.importorskip("huggingface_hub")


def _cached(model: ModelRef, filename: str) -> bool:
    found = hub.try_to_load_from_cache(model.name, filename, revision=model.revision)
    return isinstance(found, str)


@pytest.mark.skipif(not _cached(BGE_M3, "config.json"), reason="bge-m3 not downloaded")
def test_bge_m3_gives_unit_vectors_that_rank_a_paraphrase_first() -> None:
    embedder = SentenceTransformerEmbedder()

    query, near, far = embedder.embed(
        [
            "Kredi kartı yıllık aidatını geri alabilir miyim?",
            "Kart çıkaran kuruluş yıllık üyelik ücreti tahsil edebilir.",
            "Mevduat hesapları on yıl sonra zamanaşımına uğrar.",
        ]
    )

    assert embedder.dim == query.shape[0] == 1024
    np.testing.assert_allclose(np.linalg.norm([query, near, far], axis=1), 1.0, rtol=1e-3)
    assert float(query @ near) > float(query @ far)
    assert embedder.embed([]).shape == (0, 1024)
    assert embedder.name == "BAAI/bge-m3@5617a9f6"


@pytest.mark.skipif(
    not _cached(BGE_RERANKER, "config.json"), reason="bge-reranker-v2-m3 not downloaded"
)
def test_reranker_scores_the_relevant_passage_higher() -> None:
    reranker = CrossEncoderReranker()

    relevant, unrelated = reranker.scores(
        "Kart aidatı",
        ["Kart sahibinden yıllık üyelik ücreti alınabilir.", "Mevduat zamanaşımına uğrar."],
    )

    assert relevant > unrelated
    assert reranker.scores("q", []) == []
