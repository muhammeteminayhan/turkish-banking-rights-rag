"""TCMB Uygulama Talimatı (PDF) → title, introduction, sections "n)", bents "a.", Ek-1.

The talimat is published only as a PDF. Its layout (13.01.2026 version):
- body text 12 pt (Ek-1 group headings 11 pt), footnotes 10 pt, page numbers 10 pt at the
  bottom, footnote markers 6.5–8 pt;
- sections "9) Para ve kıymetli maden transfer işlemleri", bents "c. …", items "1. …";
- footnotes can hold tables: the CPI-updated EFT caps "from 6/1/2026" are a table inside
  footnote 1, cited from bent 9(c). The footnote is therefore kept with that bent.

`pdf_lines` is the only pdfplumber-dependent part; `parse_talimat` works on its output.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

LineKind = Literal["body", "footnote", "table"]
Table = tuple[tuple[str, ...], ...]

FOOTNOTE_MAX_SIZE = 10.5  # body text is 12 pt, Ek-1 group headings 11 pt
MARKER_MAX_SIZE = 9.0
LINE_TOLERANCE = 3.0  # superscripts sit 1–2 pt above their line
PAGE_NUMBER_ZONE = 0.88  # fraction of the page height below which a lone number is a page number

_SECTION = re.compile(r"^(\d{1,2})\)\s+(.+)$")
_BENT = re.compile(r"^([a-zçğıöşü])\.\s+(.*)$")
_ITEM = re.compile(r"^\d{1,2}\.\s")
_ANNEX = re.compile(r"^Ek-\d+\b")
_ANNEX_ITEM = re.compile(r"^(\d+\.\d+)\.?\s+(.+)$")
_ANNEX_GROUP = re.compile(r"^(\d+)\.\s+(.+)$")


@dataclass(frozen=True)
class PdfLine:
    page: int
    kind: LineKind
    text: str
    refs: tuple[str, ...] = ()
    footnote_number: str | None = None
    table: Table | None = None


@dataclass(frozen=True)
class TalimatBent:
    label: str
    lines: tuple[str, ...]
    pages: tuple[int, ...]
    footnote_refs: tuple[str, ...] = ()
    tables: tuple[Table, ...] = ()

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@dataclass(frozen=True)
class TalimatSection:
    number: str
    title: str
    bents: tuple[TalimatBent, ...]


@dataclass(frozen=True)
class TalimatFootnote:
    number: str
    text: str
    page: int
    tables: tuple[Table, ...] = ()


@dataclass(frozen=True)
class AnnexItem:
    group: str
    group_title: str
    label: str
    text: str
    page: int


@dataclass(frozen=True)
class ParsedTalimat:
    title: str
    intro: str
    sections: tuple[TalimatSection, ...]
    footnotes: dict[str, TalimatFootnote] = field(default_factory=dict)
    annex_title: str | None = None
    annex_items: tuple[AnnexItem, ...] = ()
    warnings: tuple[str, ...] = ()


# --- PDF → lines -------------------------------------------------------------------


def pdf_lines(path: Path) -> tuple[PdfLine, ...]:
    """Lines of every page in reading order, page numbers dropped, tables as table lines."""
    import pdfplumber  # imported here: only the data-collection path needs it

    lines: list[PdfLine] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            lines.extend(_page_lines(page))
    return tuple(lines)


def _page_lines(page: Any) -> list[PdfLine]:
    tables = page.find_tables()
    boxes = [table.bbox for table in tables]
    words = [
        word
        for word in page.extract_words(extra_attrs=["size"], use_text_flow=True)
        if not any(_inside(word, box) for box in boxes)
    ]
    placed: list[tuple[float, PdfLine]] = []
    for top, row in _rows(words):
        line = _line(page, top, row)
        if line is not None:
            placed.append((top, line))
    for table in tables:
        rows = tuple(tuple(cell or "" for cell in row) for row in table.extract())
        placed.append(
            (table.bbox[1], PdfLine(page=page.page_number, kind="table", text="", table=rows))
        )
    return [line for _, line in sorted(placed, key=lambda item: item[0])]


def _inside(word: dict[str, Any], box: tuple[float, float, float, float]) -> bool:
    x0, top, x1, bottom = box
    return bool(
        word["x0"] >= x0 and word["x1"] <= x1 and word["top"] >= top and word["bottom"] <= bottom
    )


def _rows(words: Iterable[dict[str, Any]]) -> list[tuple[float, list[dict[str, Any]]]]:
    rows: list[tuple[float, list[dict[str, Any]]]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows and abs(word["top"] - rows[-1][0]) <= LINE_TOLERANCE:
            rows[-1][1].append(word)
        else:
            rows.append((word["top"], [word]))
    return [(top, sorted(row, key=lambda w: w["x0"])) for top, row in rows]


def _line(page: Any, top: float, row: list[dict[str, Any]]) -> PdfLine | None:
    markers = [w for w in row if w["size"] < MARKER_MAX_SIZE and w["text"].isdigit()]
    words = [w for w in row if w not in markers]
    if not words:
        return None
    text = " ".join(w["text"] for w in words)
    size = max(w["size"] for w in words)
    if size <= FOOTNOTE_MAX_SIZE and text.isdigit() and top > page.height * PAGE_NUMBER_ZONE:
        return None  # page number
    if size <= FOOTNOTE_MAX_SIZE:
        leading = markers[0]["text"] if markers and markers[0]["x0"] <= words[0]["x0"] else None
        return PdfLine(page=page.page_number, kind="footnote", text=text, footnote_number=leading)
    return PdfLine(
        page=page.page_number, kind="body", text=text, refs=tuple(m["text"] for m in markers)
    )


# --- lines → structure ------------------------------------------------------------


@dataclass
class _OpenBent:
    label: str
    lines: list[str] = field(default_factory=list)
    pages: list[int] = field(default_factory=list)
    refs: list[str] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)

    def add(self, line: PdfLine, text: str, new_line: bool) -> None:
        if new_line or not self.lines:
            self.lines.append(text)
        else:
            self.lines[-1] = f"{self.lines[-1]} {text}"
        if line.page not in self.pages:
            self.pages.append(line.page)
        self.refs.extend(line.refs)

    def close(self) -> TalimatBent:
        return TalimatBent(
            label=self.label,
            lines=tuple(self.lines),
            pages=tuple(self.pages),
            footnote_refs=tuple(self.refs),
            tables=tuple(self.tables),
        )


def parse_talimat(lines: Sequence[PdfLine]) -> ParsedTalimat:
    body = [line for line in lines if line.kind == "body"]
    title_lines = _title_lines(body)
    parser = _TalimatParser()
    for line in lines[len(title_lines) :] if _starts_with(lines, title_lines) else lines:
        parser.feed(line)
    return parser.result(" ".join(line.text for line in title_lines))


def _title_lines(body: Sequence[PdfLine]) -> list[PdfLine]:
    title: list[PdfLine] = []
    for line in body:
        letters = [char for char in line.text if char.isalpha()]
        if not letters or not all(char.isupper() for char in letters):
            break
        title.append(line)
    return title


def _starts_with(lines: Sequence[PdfLine], prefix: Sequence[PdfLine]) -> bool:
    return list(lines[: len(prefix)]) == list(prefix)


class _TalimatParser:
    def __init__(self) -> None:
        self.intro: list[str] = []
        self.sections: list[TalimatSection] = []
        self.footnotes: dict[str, TalimatFootnote] = {}
        self.annex_title: list[str] = []
        self.annex_items: list[AnnexItem] = []
        self.warnings: list[str] = []
        self._section: tuple[str, str] | None = None
        self._bents: list[TalimatBent] = []
        self._bent: _OpenBent | None = None
        self._footnote: TalimatFootnote | None = None
        self._group: tuple[str, str] | None = None
        self._item: list[Any] | None = None  # [label, text, page]
        self._in_annex = False

    def feed(self, line: PdfLine) -> None:
        if line.kind == "footnote":
            self._feed_footnote(line)
        elif line.kind == "table":
            self._feed_table(line)
        elif self._in_annex or _ANNEX.match(line.text):
            self._close_footnote()
            self._feed_annex(line)
        else:
            self._close_footnote()
            self._feed_body(line)

    def _feed_body(self, line: PdfLine) -> None:
        section = _SECTION.match(line.text)
        bent = _BENT.match(line.text)
        if section:
            self._close_section()
            self._section = (section.group(1), section.group(2))
        elif bent and self._section is not None:
            self._close_bent()
            self._bent = _OpenBent(label=bent.group(1))
            self._bent.add(line, bent.group(2), new_line=True)
        elif self._bent is not None:
            self._bent.add(line, line.text, new_line=bool(_ITEM.match(line.text)))
        elif self._section is None:
            self.intro.append(line.text)
        else:
            self.warnings.append(f"text outside any bent on page {line.page}: {line.text[:60]}")

    def _feed_footnote(self, line: PdfLine) -> None:
        if line.footnote_number is not None:
            self._close_footnote()
            self._footnote = TalimatFootnote(line.footnote_number, line.text, line.page)
        elif self._footnote is not None:
            self._footnote = TalimatFootnote(
                self._footnote.number,
                f"{self._footnote.text} {line.text}",
                self._footnote.page,
                self._footnote.tables,
            )
        else:
            self.warnings.append(f"footnote text without a number on page {line.page}")

    def _feed_table(self, line: PdfLine) -> None:
        assert line.table is not None
        if self._footnote is not None and self._footnote.page == line.page:
            self._footnote = TalimatFootnote(
                self._footnote.number,
                self._footnote.text,
                self._footnote.page,
                (*self._footnote.tables, line.table),
            )
        elif self._bent is not None:
            self._bent.tables.append(line.table)
        else:
            self.warnings.append(f"table outside any bent on page {line.page}")

    def _feed_annex(self, line: PdfLine) -> None:
        if not self._in_annex:
            self._close_section()
            self._in_annex = True
        item = _ANNEX_ITEM.match(line.text)
        group = _ANNEX_GROUP.match(line.text)
        if item:
            self._close_item()
            self._item = [item.group(1), item.group(2), line.page]
        elif group:
            self._close_item()
            self._group = (group.group(1), group.group(2))
        elif self._item is not None:
            self._item[1] = f"{self._item[1]} {line.text}"
        elif self._group is None:
            self.annex_title.append(line.text)

    def _close_footnote(self) -> None:
        if self._footnote is not None:
            self.footnotes[self._footnote.number] = self._footnote
            self._footnote = None

    def _close_bent(self) -> None:
        if self._bent is not None:
            self._bents.append(self._bent.close())
            self._bent = None

    def _close_section(self) -> None:
        self._close_bent()
        if self._section is not None:
            number, title = self._section
            self.sections.append(TalimatSection(number, title, tuple(self._bents)))
        self._section = None
        self._bents = []

    def _close_item(self) -> None:
        if self._item is None:
            return
        label, text, page = self._item
        group, group_title = self._group or ("", "")
        if label.split(".")[0] != group:
            self.warnings.append(f"Ek-1: item {label} printed under group {group}")
        self.annex_items.append(AnnexItem(group, group_title, label, text, page))
        self._item = None

    def result(self, title: str) -> ParsedTalimat:
        self._close_footnote()
        self._close_item()
        self._close_section()
        return ParsedTalimat(
            title=title,
            intro=" ".join(self.intro),
            sections=tuple(self.sections),
            footnotes=dict(self.footnotes),
            annex_title=" ".join(self.annex_title) or None,
            annex_items=tuple(self.annex_items),
            warnings=tuple(self.warnings),
        )
