"""Retrieval metrics: Recall@k and MRR, at chunk level and at article (madde) level.

Article level counts a hit when any of the top-k *chunks* belongs to the expected article:
a split fıkra (":p2") or a neighbouring fıkra of the right article is still the right
place to read. k always counts chunks, because generation reads the top-k chunks.
Expected chunks with equivalents form groups (finhak.evaluation.golden); a group is hit
when any member is. Out-of-scope questions have nothing to find and are not scored here.
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence, Set
from dataclasses import dataclass

import numpy as np

from finhak.evaluation.golden import GoldenQuestion, merge_overlapping
from finhak.retrieval.direct_ref import find_direct_refs

KS = (1, 5, 10)
MRR_CUTOFF = 10


def madde_key(chunk_id: str) -> str:
    """ "6502:m22:f1:p2" → "6502:m22"; annex and talimat parts keep their first segment."""
    doc_id, _, rest = chunk_id.partition(":")
    first = rest.split(":", 1)[0].split("~", 1)[0]
    return f"{doc_id}:{first}" if first else doc_id


def recall_at_k(ranked: Sequence[str], groups: Sequence[Set[str]], k: int) -> float:
    """Share of expected groups (a chunk and its equivalents) hit in the top k."""
    if not groups:
        raise ValueError("recall needs at least one expected group")
    top = set(ranked[:k])
    return sum(1 for group in groups if group & top) / len(groups)


def reciprocal_rank(
    ranked: Sequence[str], groups: Sequence[Set[str]], cutoff: int = MRR_CUTOFF
) -> float:
    relevant = set().union(*groups)
    for rank, item in enumerate(ranked[:cutoff], start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


@dataclass(frozen=True)
class QuestionScore:
    question_id: str
    category: str
    chunk: dict[str, float]
    madde: dict[str, float]
    ranked: tuple[str, ...]
    latency_ms: float
    cites_article: bool = False  # the question names an article ("TKHK m.22")


@dataclass(frozen=True)
class Summary:
    n: int
    chunk: dict[str, float]
    madde: dict[str, float]
    by_category: dict[str, dict[str, float]]
    by_citation: dict[str, dict[str, float]]  # "cites_article" / "no_citation"
    latency_ms: dict[str, float]


def score_question(
    question: GoldenQuestion, ranked: Sequence[str], latency_ms: float
) -> QuestionScore:
    if not question.answerable:
        raise ValueError(f"{question.id}: no expected chunks to score against")
    articles = [madde_key(chunk_id) for chunk_id in ranked]  # same positions as the chunks
    madde_groups = merge_overlapping(frozenset(map(madde_key, g)) for g in question.groups)
    return QuestionScore(
        question_id=question.id,
        category=question.category,
        chunk=_metrics(ranked, question.groups),
        madde=_metrics(articles, madde_groups),
        ranked=tuple(ranked[: max(KS)]),
        latency_ms=latency_ms,
        cites_article=bool(find_direct_refs(question.question)),
    )


def summarize(scores: Iterable[QuestionScore]) -> Summary:
    scores = list(scores)
    if not scores:
        raise ValueError("no scored questions")
    by_category: dict[str, list[QuestionScore]] = defaultdict(list)
    by_citation: dict[str, list[QuestionScore]] = defaultdict(list)
    for score in scores:
        by_category[score.category].append(score)
        by_citation["cites_article" if score.cites_article else "no_citation"].append(score)
    latencies = np.array([s.latency_ms for s in scores])
    return Summary(
        n=len(scores),
        chunk=_mean(s.chunk for s in scores),
        madde=_mean(s.madde for s in scores),
        by_category={name: _group_stats(group) for name, group in sorted(by_category.items())},
        by_citation={name: _group_stats(group) for name, group in sorted(by_citation.items())},
        latency_ms={
            "p50": round(float(np.percentile(latencies, 50)), 1),
            "p95": round(float(np.percentile(latencies, 95)), 1),
        },
    )


def _group_stats(group: Sequence[QuestionScore]) -> dict[str, float]:
    return {
        "n": float(len(group)),
        **{f"chunk_{k}": v for k, v in _mean(s.chunk for s in group).items()},
        **{f"madde_{k}": v for k, v in _mean(s.madde for s in group).items()},
    }


def _metrics(ranked: Sequence[str], groups: Sequence[Set[str]]) -> dict[str, float]:
    metrics = {f"recall@{k}": recall_at_k(ranked, groups, k) for k in KS}
    metrics["mrr"] = reciprocal_rank(ranked, groups)
    return metrics


def _mean(rows: Iterable[dict[str, float]]) -> dict[str, float]:
    rows = list(rows)
    return {key: round(sum(row[key] for row in rows) / len(rows), 4) for key in rows[0]}
