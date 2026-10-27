"""Small value types shared by the retrievers."""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Scored:
    """One retriever's hit: a chunk id and that retriever's score (higher is better)."""

    chunk_id: str
    score: float


# query, k -> at most k hits, best first
Searcher = Callable[[str, int], list[Scored]]
