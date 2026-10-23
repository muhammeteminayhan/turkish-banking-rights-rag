"""PDF helpers for the parse report: page lookup (best effort) and an independent article count.

The HTML text is what gets parsed. The official PDF of the same text is used only to
- find the page a chunk starts on (`sayfa` in citations), and
- count article headings a second, independent way to check the HTML parser.
"""

import re
from collections.abc import Sequence
from pathlib import Path

from finhak.textnorm import tr_casefold

LOOKUP_CHARS = 60
_NON_WORD = re.compile(r"[\W_]+")
_HEADING_LINE = re.compile(
    r"(?m)^\s*(?:(?:EK|Ek|GEÇİCİ|Geçici)\s+)?(?:MADDE|Madde)\s+\d+(?:\s*/\s*[A-ZÇĞİÖŞÜ])?"
    r"\s*(?:\[\d+\]\s*)?[-–—]"
)


def compact(text: str) -> str:
    """Lowercase (Turkish), without circumflex, spaces or punctuation: for fuzzy lookups."""
    return _NON_WORD.sub("", tr_casefold(text))


def count_madde_headings(text: str) -> int:
    """Lines that start like "MADDE 3 –" / "Geçici Madde 32 –" (sentences mentioning an
    article and table rows without a dash are not counted)."""
    return len(_HEADING_LINE.findall(text))


class PageIndex:
    def __init__(self, pages: Sequence[str]) -> None:
        self._raw = list(pages)
        self._pages = [compact(page) for page in pages]
        self._joined = "".join(self._pages)
        self._starts: list[int] = []
        offset = 0
        for page in self._pages:
            self._starts.append(offset)
            offset += len(page)

    @classmethod
    def from_pdf(cls, path: Path) -> "PageIndex":
        import pdfplumber  # only the report needs PDF text

        with pdfplumber.open(path) as pdf:
            return cls([page.extract_text() or "" for page in pdf.pages])

    def raw_text(self) -> str:
        return "\n".join(self._raw)

    def locate(self, text: str, start: int = 1) -> int | None:
        """1-based page where `text` starts, searching from page `start` first."""
        key = compact(text)[:LOOKUP_CHARS]
        if not key:
            return None
        from_offset = self._starts[max(0, min(start, len(self._starts)) - 1)] if self._starts else 0
        position = self._joined.find(key, from_offset)
        if position < 0:
            position = self._joined.find(key)
        if position < 0:
            return None
        page = 1
        for index, offset in enumerate(self._starts, start=1):
            if offset <= position:
                page = index
        return page
