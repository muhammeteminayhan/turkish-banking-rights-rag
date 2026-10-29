"""Check a golden-question draft before it goes to the owner for approval.

    python eval/check_golden.py eval/drafts/batch2.jsonl

Checks every quote against its chunk's text and notes, the chunk ids, ids and questions
already in eval/golden.jsonl, and questions that copy five words of their article. Prints
the category and document counts for the approval table. Exit codes: 0 no problems,
1 problems, 2 a file cannot be read.
"""

import argparse
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from finhak.evaluation.draft_check import check_draft
from finhak.evaluation.golden import GoldenError, load_golden
from finhak.index.indexer import load_chunks

EXIT_OK, EXIT_PROBLEMS, EXIT_UNREADABLE = 0, 1, 2


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("draft", type=Path)
    parser.add_argument("--chunks", type=Path, default=Path("data/processed/chunks.jsonl"))
    parser.add_argument("--golden", type=Path, default=Path("eval/golden.jsonl"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, out: TextIO | None = None) -> int:
    out = out or sys.stdout
    args = parse_args(argv)
    try:
        draft = load_golden(args.draft)
        existing = load_golden(args.golden) if args.golden.exists() else []
        chunks = {chunk.id: chunk for chunk in load_chunks(args.chunks)}
    except (GoldenError, OSError, ValueError) as exc:
        out.write(f"error: {exc}\n")
        return EXIT_UNREADABLE
    problems = check_draft(draft, chunks, existing)
    for problem in problems:
        out.write(f"{problem.question_id}: {problem.message}\n")
    categories = Counter(q.category for q in draft)
    documents = Counter(
        doc for q in draft for doc in {chunks[c].doc_id for c in q.expected_chunks if c in chunks}
    )
    flagged = [q.id for q in draft if q.confidence == "needs_user_check"]
    out.write("categories: " + ", ".join(f"{k} {n}" for k, n in sorted(categories.items())) + "\n")
    out.write("documents: " + ", ".join(f"{k} {n}" for k, n in documents.most_common()) + "\n")
    out.write(f"needs_user_check: {', '.join(flagged) or '-'}\n")
    out.write(f"{len(draft)} questions, {len(problems)} problems\n")
    return EXIT_PROBLEMS if problems else EXIT_OK
