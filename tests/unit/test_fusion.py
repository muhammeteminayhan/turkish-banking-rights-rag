import pytest

from finhak.retrieval.fusion import reciprocal_rank_fusion

pytestmark = pytest.mark.unit


def test_scores_are_the_sum_of_reciprocal_ranks() -> None:
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["c", "a"]], k=60)

    scores = dict(fused)
    assert scores["a"] == pytest.approx(1 / 61 + 1 / 62)
    assert scores["c"] == pytest.approx(1 / 63 + 1 / 61)
    assert scores["b"] == pytest.approx(1 / 62)
    assert [chunk_id for chunk_id, _ in fused] == ["a", "c", "b"]


def test_ties_go_to_the_better_single_rank_then_the_id() -> None:
    # a and b both score 1/61 + 1/62 with a best rank of 1; d and e both 1/63 at rank 3.
    fused = reciprocal_rank_fusion([["b", "a", "e"], ["a", "b", "d"]], k=60)

    assert [chunk_id for chunk_id, _ in fused] == ["a", "b", "d", "e"]


def test_a_single_ranking_keeps_its_order() -> None:
    assert [c for c, _ in reciprocal_rank_fusion([["z", "y", "x"]])] == ["z", "y", "x"]


def test_only_the_first_occurrence_in_a_ranking_counts() -> None:
    fused = dict(reciprocal_rank_fusion([["a", "a", "b"]], k=60))

    assert fused == {"a": pytest.approx(1 / 61), "b": pytest.approx(1 / 63)}


def test_empty_input_gives_nothing() -> None:
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []


def test_k_must_be_positive() -> None:
    with pytest.raises(ValueError, match="k"):
        reciprocal_rank_fusion([["a"]], k=0)
