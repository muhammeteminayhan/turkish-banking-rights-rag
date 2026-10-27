"""In-memory BM25 (rank_bm25 Okapi) with a Turkish analyzer: the lexical ablation row.

Two stemmers are offered. "snowball" is the Snowball Turkish stemmer, the same algorithm
PostgreSQL's turkish configuration uses. "prefix5" keeps the first five letters of each
word, a simple stemmer that does well for Turkish retrieval (Can et al., JASIST 2008).
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from typing import Any, Literal

import snowballstemmer
from rank_bm25 import BM25Okapi

from finhak.index.passages import passage
from finhak.parsing.chunker import Chunk
from finhak.retrieval.types import Scored
from finhak.textnorm import tr_casefold

Stemmer = Literal["snowball", "prefix5"]
PREFIX_LENGTH = 5

# Function words and question words that say nothing about the topic.
STOPWORDS = frozenset(
    """
    acaba ama ancak bana bazı ben beni benim bir biz bu bunu da daha de değil diye en gibi
    hangi hangisi her için ile ise ki kim mi mı mu mü miyim mıyım muyum müyüm misin mısın
    nasıl ne neden nedir nelerdir niçin o olan olarak olur onu siz şu ve veya ya yani
    """.split()  # noqa: SIM905  (a word list reads better as text)
)
_TOKEN = re.compile(r"\w+")


def analyze(text: str, stemmer: Stemmer = "snowball") -> tuple[str, ...]:
    if stemmer not in ("snowball", "prefix5"):
        raise ValueError(f"unknown stemmer {stemmer!r}")
    words = [w for w in _TOKEN.findall(tr_casefold(text)) if w not in STOPWORDS]
    if stemmer == "prefix5":
        return tuple(w[:PREFIX_LENGTH] for w in words)
    return tuple(str(stem) for stem in _snowball().stemWords(words))


@cache
def _snowball() -> Any:  # snowballstemmer ships no type hints
    return snowballstemmer.stemmer("turkish")


@dataclass(frozen=True)
class Bm25Index:
    chunk_ids: tuple[str, ...]
    model: BM25Okapi
    stemmer: Stemmer

    @classmethod
    def from_chunks(cls, chunks: Sequence[Chunk], stemmer: Stemmer = "snowball") -> "Bm25Index":
        if not chunks:
            raise ValueError("BM25 needs at least one chunk")
        corpus = [list(analyze(passage(chunk), stemmer)) for chunk in chunks]
        return cls(tuple(c.id for c in chunks), BM25Okapi(corpus), stemmer)

    def search(self, query: str, k: int) -> list[Scored]:
        terms = list(analyze(query, self.stemmer))
        if not terms:
            return []
        scores = self.model.get_scores(terms)
        ranked = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
        return [Scored(self.chunk_ids[i], float(scores[i])) for i in ranked[:k] if scores[i] > 0]
