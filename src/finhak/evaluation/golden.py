"""Golden questions: eval/golden.jsonl (approved) and eval/drafts/*.jsonl (awaiting approval)."""

import json
from collections.abc import Iterable, Set
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

Category = Literal[
    "dogrudan",  # one fıkra answers it
    "cok_maddeli",  # needs two or more chunks
    "sayisal",  # an amount, rate or time limit
    "degisiklik",  # an amended provision; asks for the current rule
    "kapsam_disi",  # the corpus cannot answer it
    "yanlis_onerme",  # built on a premise the corpus contradicts
]
_FROZEN = ConfigDict(frozen=True, extra="forbid")


class GoldenError(ValueError):
    """A golden file that cannot be read or does not validate."""


class Evidence(BaseModel):
    model_config = _FROZEN

    chunk: str
    quote: str  # exact substring of that chunk's text or notes


class GoldenQuestion(BaseModel):
    model_config = _FROZEN

    id: str
    category: Category
    question: str
    expected_chunks: tuple[str, ...]
    expected_answer: str
    evidence: tuple[Evidence, ...]
    confidence: Literal["high", "needs_user_check"]
    comment: str = ""
    status: Literal["draft", "approved"] = "draft"
    # The same rule in another document (Tebliğ ↔ Talimat, Kanun ↔ Yönetmelik): retrieving
    # an equivalent counts as retrieving the expected chunk.
    equivalent_chunks: dict[str, tuple[str, ...]] = {}

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.category == "kapsam_disi":
            if self.expected_chunks or self.evidence:
                raise ValueError("kapsam_disi questions have no expected_chunks or evidence")
        elif not self.expected_chunks:
            raise ValueError(f"{self.category} questions need expected_chunks")
        stray = [e.chunk for e in self.evidence if e.chunk not in self.expected_chunks]
        if stray:
            raise ValueError(f"evidence from chunks that are not expected: {stray}")
        orphans = [c for c in self.equivalent_chunks if c not in self.expected_chunks]
        if orphans:
            raise ValueError(f"equivalent_chunks for chunks that are not expected: {orphans}")
        return self

    @property
    def answerable(self) -> bool:
        return bool(self.expected_chunks)

    @property
    def groups(self) -> tuple[frozenset[str], ...]:
        """Expected chunks with their equivalents; groups sharing a chunk are merged, so
        each rule counts once whichever copy is retrieved."""
        return merge_overlapping(
            frozenset({chunk, *self.equivalent_chunks.get(chunk, ())})
            for chunk in self.expected_chunks
        )

    @property
    def all_chunk_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(c for group in self.groups for c in sorted(group)))


def merge_overlapping(groups: Iterable[frozenset[str]]) -> tuple[frozenset[str], ...]:
    """Union groups that share a member (transitively), keeping first-seen order."""
    merged: list[frozenset[str]] = []
    for group in groups:
        overlapping = [g for g in merged if g & group]
        joined = group.union(*overlapping)
        merged = [g for g in merged if g not in overlapping] + [joined]
    return tuple(merged)


def load_golden(path: Path) -> list[GoldenQuestion]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise GoldenError(f"cannot read {path}: {exc}") from exc
    questions: list[GoldenQuestion] = []
    seen: set[str] = set()
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            question = GoldenQuestion.model_validate(json.loads(line))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise GoldenError(f"{path} line {number}: {exc}") from exc
        if question.id in seen:
            raise GoldenError(f"{path} line {number}: duplicate id {question.id}")
        seen.add(question.id)
        questions.append(question)
    return questions


def unknown_chunk_ids(
    questions: Iterable[GoldenQuestion], known: Set[str]
) -> dict[str, tuple[str, ...]]:
    """Expected (or equivalent) chunk ids that the index does not have, per question."""
    unknown = {q.id: tuple(c for c in q.all_chunk_ids if c not in known) for q in questions}
    return {qid: ids for qid, ids in unknown.items() if ids}
