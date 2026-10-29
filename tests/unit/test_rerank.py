import sys
from collections.abc import Sequence
from types import SimpleNamespace

import pytest

from finhak.index.embed import ModelLoadError, SentenceTransformerEmbedder
from finhak.retrieval.rerank import CrossEncoderReranker

pytestmark = pytest.mark.unit


class LengthScorer:
    """Stands in for the cross-encoder: scores a pair by its passage length."""

    def __init__(self) -> None:
        self.seen: list[str] = []

    def predict(
        self, pairs: Sequence[tuple[str, str]], batch_size: int, show_progress_bar: bool
    ) -> list[float]:
        self.seen += [passage for _, passage in pairs]
        return [float(len(passage)) for _, passage in pairs]


def test_passages_are_scored_shortest_first_but_returned_in_their_own_order() -> None:
    scorer = LengthScorer()
    reranker = object.__new__(CrossEncoderReranker)  # no model download in a unit test
    reranker._model = scorer
    reranker._batch_size = 4
    passages = ["uzun bir kaynak metni parçası", "kısa", "orta uzunlukta"]

    scores = reranker.scores("soru", passages)

    assert scores == [float(len(p)) for p in passages]
    assert scorer.seen == sorted(passages, key=len)  # less padding per batch on the CPU
    assert reranker.scores("soru", []) == []


def test_a_model_that_does_not_fit_on_the_gpu_is_a_load_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def gpu_full(*args: object, **kwargs: object) -> None:
        raise RuntimeError("CUDA out of memory")

    # light stand-ins: importing torch and sentence-transformers takes seconds
    fake_torch = SimpleNamespace(float16="fp16", cuda=SimpleNamespace(is_available=lambda: True))
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    fake_st = SimpleNamespace(CrossEncoder=gpu_full, SentenceTransformer=gpu_full)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st)

    with pytest.raises(ModelLoadError, match="RETRIEVAL_DEVICE=cpu"):
        CrossEncoderReranker(device="cuda")
    with pytest.raises(ModelLoadError, match="out of memory"):
        SentenceTransformerEmbedder(device="cuda")
