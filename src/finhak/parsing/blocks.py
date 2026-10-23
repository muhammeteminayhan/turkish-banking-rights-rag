"""mevzuat.gov.tr consolidated-text HTML → a flat sequence of blocks in document order.

What the Word-exported HTML of mevzuat.gov.tr contains, and how it is mapped:
- `<p>` paragraphs → `Paragraph`, whitespace-normalised, with a `bold` flag (article titles
  are fully bold, article text is not);
- single-column tables are page layout (whole regulations sit in one cell) → read through;
- multi-column tables → `TableBlock`, or `HistoryTable` for the amendment lists
  ("…Yayımlandığı Resmî Gazete", "…Yürürlüğe Giriş Tarihi") that end many texts;
- footnote markers: `[n]` in laws, `<sup>(n)</sup>` in regulations, `<sup>13</sup>` /
  `<sup>[32]</sup>` in laws. They are removed from the text and kept as references;
- a paragraph that *starts* with `[n]` is a footnote body (`Footnote`); one that starts with
  a `<sup>` marker is an endnote body (`Endnote`); `____` lines are `Separator`s.
"""

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

from finhak.textnorm import normalize_space, tr_casefold

PARAGRAPH_TAGS = ("p", "h1", "h2", "h3", "h4", "h5", "h6", "li")
_CONTAINER_TAGS = (*PARAGRAPH_TAGS, "table", "div")
_BRACKET_REF = re.compile(r"\s*\[(\d+)\]")
_FOOTNOTE_BODY = re.compile(r"^\[(\d+)\]\s*(.*)$", re.DOTALL)
_SEPARATOR = re.compile(r"^_{3,}$")
_SUP_BRACKET = re.compile(r"^\[\s*(\d+)\s*\]$")
_SUP_NUMBER = re.compile(r"^\(?\s*(\d+)\s*\)?$")
# Compared after tr_casefold, which also drops the circumflex of "Resmî".
_HISTORY_HEADINGS = ("yayımlandığı resmi gazete", "yürürlüğe giriş tarihi")
_NUMBERED_ROW = re.compile(r"^(\d+)\.$")
# Word HTML splits text into spans; joining spans with a space must not detach punctuation.
_SPACE_BEFORE = re.compile(r"\s+([,.;:!?)\]”’])")
_SPACE_AFTER = re.compile(r"([(\[“‘])\s+")
_SPACE_AFTER_SLASH = re.compile(r"(?<=\S)/\s+(?=\S)")


@dataclass(frozen=True)
class Paragraph:
    text: str
    bold: bool = False
    footnote_refs: tuple[str, ...] = ()
    sup_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class TableBlock:
    rows: tuple[tuple[str, ...], ...]

    def render(self) -> str:
        return "\n".join(" | ".join(row) for row in self.rows)


@dataclass(frozen=True)
class HistoryTable:
    rows: tuple[tuple[str, ...], ...]

    def numbered_rows(self) -> dict[str, tuple[str, str]]:
        """Rows like ("4.", "22/12/2023", "32407") keyed by their number."""
        numbered: dict[str, tuple[str, str]] = {}
        for row in self.rows:
            match = _NUMBERED_ROW.match(row[0]) if len(row) >= 3 else None
            if match:
                numbered[match.group(1)] = (row[1], row[2])
        return numbered


@dataclass(frozen=True)
class Footnote:
    number: str
    text: str


@dataclass(frozen=True)
class Endnote:
    number: str
    text: str


@dataclass(frozen=True)
class Separator:
    pass


Block = Paragraph | TableBlock | HistoryTable | Footnote | Endnote | Separator


def tidy_punctuation(text: str) -> str:
    """Remove the spaces that span boundaries put before "," "." ")" … and after "(" "“"."""
    text = _SPACE_BEFORE.sub(r"\1", text)
    text = _SPACE_AFTER.sub(r"\1", text)
    return _SPACE_AFTER_SLASH.sub("/", text)


def html_blocks(html: str) -> tuple[Block, ...]:
    soup = BeautifulSoup(html, "html.parser")
    blocks: list[Block] = []
    _walk(soup.body or soup, blocks)
    return tuple(blocks)


def _walk(node: Tag, out: list[Block]) -> None:
    for child in node.children:
        if not isinstance(child, Tag) or child.name in ("script", "style"):
            continue
        if child.name == "table":
            _table(child, out)
        elif child.name in PARAGRAPH_TAGS:
            block = _paragraph(child)
            if block is not None:
                out.append(block)
        else:
            _walk(child, out)


def _table(table: Tag, out: list[Block]) -> None:
    rows = [row for row in table.find_all("tr") if row.find_parent("table") is table]
    cells = [[c for c in row.find_all(["td", "th"], recursive=False)] for row in rows]
    if all(len(row) <= 1 for row in cells):
        for row in cells:
            for cell in row:
                _layout_cell(cell, out)
        return

    text_rows = tuple(tuple(_cell_text(cell) for cell in row) for row in cells)
    text_rows = tuple(row for row in text_rows if any(row))
    heading = tr_casefold(" ".join(" ".join(row) for row in text_rows[:2]))
    if any(marker in heading for marker in _HISTORY_HEADINGS):
        out.append(HistoryTable(rows=text_rows))
    elif text_rows:
        out.append(TableBlock(rows=text_rows))


def _layout_cell(cell: Tag, out: list[Block]) -> None:
    if cell.find(_CONTAINER_TAGS):
        _walk(cell, out)
        return
    block = _paragraph(cell)
    if block is not None:
        out.append(block)


def _cell_text(cell: Tag) -> str:
    for sup in cell.find_all("sup"):
        sup.decompose()
    return tidy_punctuation(normalize_space(cell.get_text(" ")))


def _paragraph(tag: Tag) -> Paragraph | Footnote | Endnote | Separator | None:
    sups = tag.find_all("sup")
    leading_sup = sups[0] if sups and _starts_with(tag, sups[0]) else None
    footnote_refs: list[str] = []
    sup_refs: list[str] = []
    endnote_number: str | None = None
    for sup in sups:
        marker = normalize_space(sup.get_text(" "))
        bracket = _SUP_BRACKET.match(marker)
        number = _SUP_NUMBER.match(marker)
        if sup is leading_sup and number:
            endnote_number = number.group(1)
        elif bracket:
            footnote_refs.append(bracket.group(1))
        elif number:
            sup_refs.append(number.group(1))
        sup.decompose()

    raw_text = tidy_punctuation(normalize_space(tag.get_text(" ")))
    if not raw_text:
        return None
    if endnote_number is not None:
        return Endnote(number=endnote_number, text=raw_text)
    if _SEPARATOR.match(raw_text):
        return Separator()
    footnote = _FOOTNOTE_BODY.match(raw_text)
    if footnote:
        return Footnote(number=footnote.group(1), text=normalize_space(footnote.group(2)))

    footnote_refs.extend(_BRACKET_REF.findall(raw_text))
    text = normalize_space(_BRACKET_REF.sub("", raw_text))
    return Paragraph(
        text=text,
        bold=_is_bold(tag, text),
        footnote_refs=tuple(footnote_refs),
        sup_refs=tuple(sup_refs),
    )


def _starts_with(tag: Tag, sup: Tag) -> bool:
    """True when nothing but whitespace comes before `sup` inside `tag`."""
    for node in tag.descendants:
        if node is sup:
            return True
        if isinstance(node, NavigableString) and node.strip():
            return False
    return False


def _is_bold(tag: Tag, text: str) -> bool:
    outermost = [
        b for b in tag.find_all(["b", "strong"]) if b.find_parent(["b", "strong"]) in (None, tag)
    ]
    bold_text = _BRACKET_REF.sub("", normalize_space(" ".join(b.get_text(" ") for b in outermost)))
    return bool(text) and len(normalize_space(bold_text)) >= len(text) - 1
