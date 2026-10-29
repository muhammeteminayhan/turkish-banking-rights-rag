"""Checks a golden-question draft must pass before it goes to the owner for approval."""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from finhak.evaluation.golden import GoldenQuestion
from finhak.parsing.chunker import Chunk
from finhak.textnorm import tr_casefold

# A question that repeats this many consecutive words of its article tests string matching,
# not retrieval (the rule batch 1 was written to).
MIN_COPIED_WORDS = 5
_WORD = re.compile(r"\w+")


@dataclass(frozen=True)
class DraftProblem:
    question_id: str
    message: str


def check_draft(
    draft: Sequence[GoldenQuestion],
    chunks: Mapping[str, Chunk],
    existing: Sequence[GoldenQuestion] = (),
) -> list[DraftProblem]:
    """Every problem of every draft question; `existing` is the approved golden set."""
    used_ids = {q.id for q in existing}
    asked = {_question_key(q.question): q.id for q in existing}
    problems: list[DraftProblem] = []
    for question in draft:
        key = _question_key(question.question)
        messages = [f"id {question.id} is already used"] if question.id in used_ids else []
        if key in asked:
            messages.append(f"the same question as {asked[key]}")
        messages += _chunk_problems(question, chunks)
        problems += [DraftProblem(question.id, message) for message in messages]
        used_ids.add(question.id)
        asked.setdefault(key, question.id)
    return problems


def _chunk_problems(question: GoldenQuestion, chunks: Mapping[str, Chunk]) -> list[str]:
    messages = [f"unknown chunk {c}" for c in question.all_chunk_ids if c not in chunks]
    for evidence in question.evidence:
        chunk = chunks.get(evidence.chunk)
        if chunk is not None and not any(evidence.quote in s for s in (chunk.text, *chunk.notes)):
            messages.append(f"quote not found in {evidence.chunk}: {evidence.quote!r}")
    quoted = {evidence.chunk for evidence in question.evidence}
    messages += [
        f"expected chunk {c} has no evidence quote"
        for c in question.expected_chunks
        if c not in quoted
    ]
    for chunk_id in question.expected_chunks:
        chunk = chunks.get(chunk_id)
        copied = _longest_shared_run(question.question, chunk.text) if chunk else []
        if len(copied) >= MIN_COPIED_WORDS:
            messages.append(f"question copies {' '.join(copied)!r} from {chunk_id}")
    return messages


def _words(text: str) -> list[str]:
    return _WORD.findall(tr_casefold(text))


def _question_key(question: str) -> str:
    return " ".join(_words(question))


def _longest_shared_run(question: str, text: str) -> list[str]:
    """The longest run of consecutive words the question shares with the text."""
    asked, source = _words(question), _words(text)
    best_length, best_end = 0, 0
    previous = [0] * (len(source) + 1)
    for i, word in enumerate(asked, start=1):
        current = [0] * (len(source) + 1)
        for j, other in enumerate(source, start=1):
            if word == other:
                current[j] = previous[j - 1] + 1
                if current[j] > best_length:
                    best_length, best_end = current[j], i
        previous = current
    return asked[best_end - best_length : best_end]
