"""Reciprocal rank fusion (Cormack et al., 2009)."""

from collections.abc import Sequence

RRF_K = 60


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[str]], k: int = RRF_K
) -> list[tuple[str, float]]:
    """Fuse ranked id lists: score(d) = sum over lists of 1 / (k + rank of d).

    Ties go to the item with the better single rank, then to the smaller id, so the
    result does not depend on dict ordering.
    """
    if k <= 0:
        raise ValueError(f"RRF k must be positive, got {k}")
    scores: dict[str, float] = {}
    best_rank: dict[str, int] = {}
    for ranking in rankings:
        seen: set[str] = set()
        for rank, item in enumerate(ranking, start=1):
            if item in seen:
                continue
            seen.add(item)
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
            best_rank[item] = min(best_rank.get(item, rank), rank)
    order = sorted(scores, key=lambda item: (-scores[item], best_rank[item], item))
    return [(item, scores[item]) for item in order]
