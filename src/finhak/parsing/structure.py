"""Blocks of a mevzuat.gov.tr text → sections, articles (madde), fıkra and bent.

Layout of a consolidated text, as found in the corpus:
    header       title, "Kanun Numarası : …", issuer line …
    body         KISIM / BÖLÜM headings, bold article titles, "MADDE n –" articles
    tail         endnotes "(n) …" (after a ____ separator or a leading <sup>), [n] footnotes,
                 amendment-history tables, annexes ("EK-1", "(I) SAYILI CETVEL", all-caps titles)

Fıkra numbers: newer texts write "(1)", "(2)"; older laws (5411, 5464) do not. There every
paragraph that is not a bent or a lowercase continuation ("ifade eder.") starts a new fıkra,
and the fıkra is marked `inferred` so later stages can say the number was counted, not read.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from finhak.parsing.blocks import (
    Block,
    Endnote,
    Footnote,
    HistoryTable,
    Paragraph,
    Separator,
    TableBlock,
)

MaddeKind = Literal["madde", "ek", "gecici"]

_HEADING = re.compile(
    r"^(?:(?P<prefix>EK|Ek|GEÇİCİ|Geçici)\s+)?(?:MADDE|Madde)\s+"
    r"(?P<number>\d+(?:\s*/\s*[A-ZÇĞİÖŞÜ])?)\s*"
    r"(?:[-–—]\.?\s*(?P<rest>.*)|(?P<paren>\(.*)|$)$",
    re.DOTALL,
)
_LEADING_NOTE = re.compile(
    r"^\(\s*(?:Başlığı\s+ile\s+[Bb]irlikte\s+)?(?:Ek|Değişik|Mülga|İptal|Yeniden)[^)]*\)\s*"
)
# "(3) …", "( 6) …" and the range form "(2) ila (5) - …".
_FIKRA = re.compile(
    r"^\(\s*(?P<number>\d+)\s*\)(?:\s*ila\s*\(\s*(?P<last>\d+)\s*\)\s*-?)?\s*(?P<body>.*)$",
    re.DOTALL,
)
_BENT = re.compile(r"^([a-zçğıöşü]{1,2})\)\s")
_ALT_BENT = re.compile(r"^(\d{1,2})\)\s")
_SECTION = re.compile(r"^(?:[A-ZÇĞİÖŞÜ]+\s+){1,3}(?:KISIM|BÖLÜM)$")
# An annex heading is a line of its own: "EK", "Ek-1", "EK – 2", "EKLER", "(I) SAYILI CETVEL".
_ANNEX = re.compile(
    r"^(?:EK|Ek)(?:\s*[-–—]?\s*\d+)?\s*$"
    r"|^EKLER\s*$"
    r"|^\(?[IVX]+\)?\s*SAYILI\s+CETVEL\b"
    r"|^CETVEL$"
)
_TRAILING_NOTE = re.compile(
    r"\s*\(\s*(?:Başlığı\s+ile\s+[Bb]irlikte\s+)?(?:Ek|Değişik|Mülga|İptal|Yeniden)[^)]*\)\s*$"
)
# Notes that leave nothing in force: repealed (Mülga) or annulled by the Constitutional Court.
_REPEAL_NOTE = re.compile(r"^\(\s*(?:Başlığı\s+ile\s+[Bb]irlikte\s+)?(?:Mülga|İptal)")
# Notes about one part of an article ("Değişik birinci fıkra", "Ek cümle", "Mülga ibare").
_SCOPED_NOTE = re.compile(r"fıkra|bent|cümle|ibare", re.IGNORECASE)
_RANGE_REST = re.compile(r"^(\d+)\s*[-–—]\.?\s*(.*)$", re.DOTALL)
_ENDNOTE = re.compile(r"^\(\s*(\d+)\s*\)\s+(.+)$", re.DOTALL)
_PORTAL_LINK = re.compile(r"tıklayınız\.?$", re.IGNORECASE)
MAX_TITLE_CHARS = 200


@dataclass(frozen=True)
class Fikra:
    number: int
    inferred: bool
    lines: tuple[str, ...]
    last_number: int | None = None  # "(2) ila (5)" covers fıkra 2 to 5
    bents: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    footnote_refs: tuple[str, ...] = ()
    sup_refs: tuple[str, ...] = ()
    tables: tuple[TableBlock, ...] = ()
    mulga: bool = False

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@dataclass(frozen=True)
class Madde:
    kind: MaddeKind
    number: str
    title: str | None
    fikralar: tuple[Fikra, ...]
    kisim: str | None = None
    bolum: str | None = None
    notes: tuple[str, ...] = ()
    footnote_refs: tuple[str, ...] = ()
    sup_refs: tuple[str, ...] = ()
    mulga: bool = False

    @property
    def label(self) -> str:
        prefix = {"madde": "", "ek": "EK ", "gecici": "GEÇİCİ "}[self.kind]
        return f"{prefix}MADDE {self.number}"


@dataclass(frozen=True)
class Annex:
    title: str
    blocks: tuple[Paragraph | TableBlock, ...]


@dataclass(frozen=True)
class ParsedText:
    maddeler: tuple[Madde, ...]
    header: tuple[str, ...] = ()
    annexes: tuple[Annex, ...] = ()
    footnotes: dict[str, str] = field(default_factory=dict)
    endnotes: dict[str, tuple[str, ...]] = field(default_factory=dict)
    history: tuple[HistoryTable, ...] = ()
    unplaced: tuple[str, ...] = ()


def split_leading_notes(text: str) -> tuple[tuple[str, ...], str]:
    """ "(Ek:…) (Değişik:…) rest" → (("(Ek:…)", "(Değişik:…)"), "rest")."""
    notes: list[str] = []
    rest = text
    while match := _LEADING_NOTE.match(rest):
        notes.append(match.group(0).strip())
        rest = rest[match.end() :]
    return tuple(notes), rest.strip()


def parse_structure(blocks: Sequence[Block]) -> ParsedText:
    headings = [i for i, block in enumerate(blocks) if _heading(block) is not None]
    if not headings:
        return ParsedText(maddeler=(), unplaced=tuple(_texts(blocks)))
    body_end = _body_end(blocks, headings[-1])
    header, maddeler = _parse_body(blocks[:body_end], headings[0])
    tail = _parse_tail(blocks[body_end:])
    return ParsedText(
        maddeler=maddeler,
        header=header,
        annexes=tail.annexes,
        footnotes=tail.footnotes,
        endnotes=tail.endnotes,
        history=tail.history,
        unplaced=tail.unplaced,
    )


# --- body -------------------------------------------------------------------------


@dataclass
class _Item:
    text: str
    footnote_refs: tuple[str, ...] = ()
    sup_refs: tuple[str, ...] = ()
    table: TableBlock | None = None


@dataclass
class _OpenMadde:
    kind: MaddeKind
    number: str
    title: str | None
    kisim: str | None
    bolum: str | None
    notes: tuple[str, ...]
    footnote_refs: tuple[str, ...]
    sup_refs: tuple[str, ...]
    items: list[_Item] = field(default_factory=list)


def _heading(block: Block) -> re.Match[str] | None:
    return _HEADING.match(block.text) if isinstance(block, Paragraph) else None


def _parse_body(
    blocks: Sequence[Block], first_heading: int
) -> tuple[tuple[str, ...], tuple[Madde, ...]]:
    body_start = _body_start(blocks, first_heading)
    header = tuple(_texts(blocks[:body_start]))
    maddeler: list[Madde] = []
    open_madde: _OpenMadde | None = None
    kisim: str | None = None
    bolum: str | None = None
    title: _Title | None = None
    index = body_start
    while index < len(blocks):
        block = blocks[index]
        following = blocks[index + 1] if index + 1 < len(blocks) else None
        heading = _heading(block)
        if isinstance(block, Paragraph) and _SECTION.match(block.text):
            section, index = _section(blocks, index)
            if block.text.endswith("KISIM"):
                kisim, bolum = section, None
            else:
                bolum = section
            continue
        if heading is not None and isinstance(block, Paragraph):
            if open_madde is not None:
                maddeler.append(_close(open_madde))
            open_madde = _open(heading, block, title, kisim, bolum)
            title = None
        elif _is_title(block, following):
            assert isinstance(block, Paragraph)
            title = _title(block)
        elif open_madde is not None and isinstance(block, Paragraph):
            open_madde.items.append(_Item(block.text, block.footnote_refs, block.sup_refs))
        elif open_madde is not None and isinstance(block, TableBlock):
            open_madde.items.append(_Item("", table=block))
        index += 1
    if open_madde is not None:
        maddeler.append(_close(open_madde))
    return header, tuple(maddeler)


def _body_start(blocks: Sequence[Block], first_heading: int) -> int:
    """First section heading, or the title right above the first article."""
    for index in range(first_heading):
        block = blocks[index]
        if isinstance(block, Paragraph) and _SECTION.match(block.text):
            return index
    if first_heading > 0 and _is_title(blocks[first_heading - 1], blocks[first_heading]):
        return first_heading - 1
    return first_heading


def _section(blocks: Sequence[Block], index: int) -> tuple[str, int]:
    """ "BİRİNCİ KISIM" plus its title on the next line (unless that line titles an article)."""
    heading = blocks[index]
    assert isinstance(heading, Paragraph)
    name = heading.text
    nxt = blocks[index + 1] if index + 1 < len(blocks) else None
    after = blocks[index + 2] if index + 2 < len(blocks) else None
    if (
        isinstance(nxt, Paragraph)
        and _heading(nxt) is None
        and not _SECTION.match(nxt.text)
        and not (after is not None and _heading(after) is not None)
    ):
        return f"{name} — {nxt.text}", index + 2
    return name, index + 1


def _is_title(block: Block, following: Block | None) -> bool:
    if not isinstance(block, Paragraph) or following is None or _heading(following) is None:
        return False
    if _heading(block) is not None or _FIKRA.match(block.text) or _BENT.match(block.text):
        return False
    short = len(block.text) <= MAX_TITLE_CHARS
    return short and (block.bold or not block.text.endswith((".", ":", ";")))


@dataclass(frozen=True)
class _Title:
    text: str
    notes: tuple[str, ...]
    footnote_refs: tuple[str, ...]
    sup_refs: tuple[str, ...]


def _title(block: Paragraph) -> _Title:
    """ "Sigorta … sunumu (Değişik başlık:RG-…)" → the title and its trailing notes."""
    leading, text = split_leading_notes(block.text)
    trailing: list[str] = []
    while match := _TRAILING_NOTE.search(text):
        trailing.insert(0, match.group(0).strip())
        text = text[: match.start()].rstrip()
    notes = (*leading, *trailing)
    return _Title(text or block.text, notes, block.footnote_refs, block.sup_refs)


def _is_repeal(note: str) -> bool:
    return _REPEAL_NOTE.match(note) is not None


def _is_scoped(note: str) -> bool:
    return _SCOPED_NOTE.search(note) is not None and "başlık" not in note.lower()


def _open(
    heading: re.Match[str],
    block: Paragraph,
    title: _Title | None,
    kisim: str | None,
    bolum: str | None,
) -> _OpenMadde:
    prefix = (heading.group("prefix") or "").upper()
    kind: MaddeKind = "gecici" if prefix.startswith("GE") else "ek" if prefix == "EK" else "madde"
    number = re.sub(r"\s+", "", heading.group("number"))
    rest = (heading.group("rest") or heading.group("paren") or "").strip()
    article_range = _RANGE_REST.match(rest)
    if article_range:  # "MADDE 38 – 39 – (… yerine işlenmiştir.)"
        number, rest = f"{number}-{article_range.group(1)}", article_range.group(2).strip()
    all_notes, rest = split_leading_notes(rest)
    notes = tuple(note for note in all_notes if not _is_scoped(note))
    scoped = [note for note in all_notes if _is_scoped(note)]
    if scoped and rest:
        rest = " ".join([*scoped, rest])  # becomes a leading note of the first fıkra
    numbered_first = _FIKRA.match(split_leading_notes(rest)[1]) is not None
    heading_refs = not rest or not numbered_first
    open_madde = _OpenMadde(
        kind=kind,
        number=number,
        title=title.text if title else None,
        kisim=kisim,
        bolum=bolum,
        notes=(*(title.notes if title else ()), *notes),
        footnote_refs=(
            *(title.footnote_refs if title else ()),
            *(block.footnote_refs if heading_refs else ()),
        ),
        sup_refs=(*(title.sup_refs if title else ()), *(block.sup_refs if heading_refs else ())),
    )
    if rest:
        refs = (block.footnote_refs, block.sup_refs) if numbered_first else ((), ())
        open_madde.items.append(_Item(rest, *refs))
    return open_madde


def _close(open_madde: _OpenMadde) -> Madde:
    items = list(open_madde.items)
    notes = list(open_madde.notes)
    scoped: list[str] = []
    # A note on its own line right after the heading annotates the whole article, unless it
    # names a part of it ("Değişik birinci fıkra"), which then goes to the first fıkra.
    while items and items[0].table is None:
        leading, rest = split_leading_notes(items[0].text)
        if rest or not leading:
            break
        notes.extend(note for note in leading if not _is_scoped(note))
        scoped.extend(note for note in leading if _is_scoped(note))
        items.pop(0)
    if scoped and items and items[0].table is None:
        first = items[0]
        items[0] = _Item(" ".join([*scoped, first.text]), first.footnote_refs, first.sup_refs)
    else:
        notes.extend(scoped)
    fikralar = _build_fikralar(items)
    repealed_heading = not items and any(_is_repeal(note) for note in notes)
    return Madde(
        kind=open_madde.kind,
        number=open_madde.number,
        title=open_madde.title,
        fikralar=fikralar,
        kisim=open_madde.kisim,
        bolum=open_madde.bolum,
        notes=tuple(notes),
        footnote_refs=open_madde.footnote_refs,
        sup_refs=open_madde.sup_refs,
        mulga=repealed_heading or (bool(fikralar) and all(f.mulga for f in fikralar)),
    )


@dataclass
class _OpenFikra:
    number: int
    inferred: bool
    notes: tuple[str, ...]
    last_number: int | None = None
    lines: list[str] = field(default_factory=list)
    bents: list[str] = field(default_factory=list)
    footnote_refs: list[str] = field(default_factory=list)
    sup_refs: list[str] = field(default_factory=list)
    tables: list[TableBlock] = field(default_factory=list)

    def add(self, item: _Item, line: str | None = None) -> None:
        if item.table is not None:
            self.tables.append(item.table)
            return
        text = item.text if line is None else line
        if text:
            self.lines.append(text)
        bent = _BENT.match(item.text)
        if bent:
            self.bents.append(bent.group(1))
        self.footnote_refs.extend(item.footnote_refs)
        self.sup_refs.extend(item.sup_refs)

    def close(self) -> Fikra:
        mulga = not self.lines and any(_is_repeal(note) for note in self.notes)
        return Fikra(
            number=self.number,
            inferred=self.inferred,
            lines=tuple(self.lines),
            last_number=self.last_number,
            bents=tuple(self.bents),
            notes=self.notes,
            footnote_refs=tuple(self.footnote_refs),
            sup_refs=tuple(self.sup_refs),
            tables=tuple(self.tables),
            mulga=mulga,
        )


def _build_fikralar(items: list[_Item]) -> tuple[Fikra, ...]:
    numbered = any(_FIKRA.match(split_leading_notes(item.text)[1]) for item in items)
    fikralar: list[Fikra] = []
    current: _OpenFikra | None = None
    for item in items:
        notes, rest = split_leading_notes(item.text)
        marker = _FIKRA.match(rest) if item.table is None else None
        starts_new = marker is not None or (
            not numbered and item.table is None and _starts_unnumbered_fikra(item.text, current)
        )
        if starts_new:
            if current is not None:
                fikralar.append(current.close())
            if marker is not None:
                inner_notes, body = split_leading_notes(marker.group("body"))
                last = int(marker.group("last")) if marker.group("last") else None
                current = _OpenFikra(int(marker.group("number")), False, notes + inner_notes, last)
            else:
                body = rest
                current = _OpenFikra(len(fikralar) + 1, True, notes)
            current.add(item, line=body)
            continue
        if current is None:
            current = _OpenFikra(0 if numbered else 1, True, ())
        current.add(item)
    if current is not None:
        fikralar.append(current.close())
    return tuple(fikralar)


def _starts_unnumbered_fikra(text: str, current: _OpenFikra | None) -> bool:
    if current is None:
        return True
    if _BENT.match(text) or _ALT_BENT.match(text):
        return False
    if current.lines and current.lines[-1].rstrip().endswith((",", ";", ":")):
        return False  # the previous line opened a list ("Bu Kanunda geçen;") or an item ","
    first = text[:1]
    return not (first.isalpha() and first.islower())


# --- tail -------------------------------------------------------------------------


def _body_end(blocks: Sequence[Block], last_heading: int) -> int:
    """Index of the first block after the last article that is not article text."""
    for index in range(last_heading + 1, len(blocks)):
        block = blocks[index]
        if isinstance(block, Separator | Endnote | Footnote | HistoryTable):
            return index
        if isinstance(block, Paragraph) and (
            _ANNEX.match(block.text) or _is_caps_title(block.text)
        ):
            return index
    return len(blocks)


def _is_caps_title(text: str) -> bool:
    """An all-caps heading line (annex titles); not a sentence, fıkra or bent in capitals."""
    if text.endswith(".") or _FIKRA.match(text) or _BENT.match(text):
        return False
    letters = [char for char in text if char.isalpha()]
    return len(text.split()) >= 2 and bool(letters) and all(char.isupper() for char in letters)


@dataclass(frozen=True)
class _Tail:
    footnotes: dict[str, str]
    endnotes: dict[str, tuple[str, ...]]
    history: tuple[HistoryTable, ...]
    annexes: tuple[Annex, ...]
    unplaced: tuple[str, ...]


def _parse_tail(blocks: Sequence[Block]) -> _Tail:
    parser = _TailParser()
    for block in blocks:
        parser.feed(block)
    return parser.result()


class _TailParser:
    """What follows the last article: endnotes, footnotes, history tables, annexes."""

    def __init__(self) -> None:
        self.footnotes: dict[str, str] = {}
        self.endnotes: dict[str, list[str]] = {}
        self.history: list[HistoryTable] = []
        self.annexes: list[Annex] = []
        self.unplaced: list[str] = []
        self._annex_title: list[str] = []
        self._annex_blocks: list[Paragraph | TableBlock] = []
        self._caps_title_open = False  # an annex titled by all-caps lines may span lines
        self._in_endnotes = False
        self._last_endnote: str | None = None

    def feed(self, block: Block) -> None:
        if isinstance(block, Footnote | Endnote | HistoryTable | Separator):
            self._close_annex()
            self._feed_marker_block(block)
        elif isinstance(block, Paragraph) and _ANNEX.match(block.text):
            self._start_annex(block.text, caps=False)
        elif isinstance(block, Paragraph) and self._continues_caps_title(block.text):
            self._start_annex(block.text, caps=True)
        elif self._annex_title:
            self._caps_title_open = False
            self._annex_blocks.append(block)  # Paragraph | TableBlock: markers handled above
        elif isinstance(block, Paragraph):
            self._feed_paragraph(block.text)
        else:
            assert isinstance(block, TableBlock)
            self.unplaced.append(block.render())

    def _feed_marker_block(self, block: Footnote | Endnote | HistoryTable | Separator) -> None:
        if isinstance(block, Footnote):
            self.footnotes[block.number] = block.text
        elif isinstance(block, Endnote):
            self.endnotes.setdefault(block.number, []).append(block.text)
            self._in_endnotes, self._last_endnote = True, block.number
        elif isinstance(block, HistoryTable):
            self.history.append(block)
            self._in_endnotes = False
        else:
            self._in_endnotes = True

    def _continues_caps_title(self, text: str) -> bool:
        return _is_caps_title(text) and (self._caps_title_open or not self._annex_title)

    def _start_annex(self, text: str, caps: bool) -> None:
        if not (caps and self._caps_title_open):
            self._close_annex()
        self._annex_title.append(text)
        self._caps_title_open = caps
        self._in_endnotes = False

    def _feed_paragraph(self, text: str) -> None:
        match = _ENDNOTE.match(text) if self._in_endnotes else None
        if match:
            self.endnotes.setdefault(match.group(1), []).append(match.group(2))
            self._last_endnote = match.group(1)
        elif self._in_endnotes and self._last_endnote and not _PORTAL_LINK.search(text):
            texts = self.endnotes[self._last_endnote]
            texts[-1] = f"{texts[-1]} {text}"
        else:
            self.unplaced.append(text)

    def _close_annex(self) -> None:
        if self._annex_title:
            title = " ".join(self._annex_title)
            self.annexes.append(Annex(title=title, blocks=tuple(self._annex_blocks)))
            self._annex_title = []
            self._annex_blocks = []

    def result(self) -> _Tail:
        self._close_annex()
        return _Tail(
            footnotes=self.footnotes,
            endnotes={number: tuple(texts) for number, texts in self.endnotes.items()},
            history=tuple(self.history),
            annexes=tuple(self.annexes),
            unplaced=tuple(self.unplaced),
        )


def _texts(blocks: Sequence[Block]) -> list[str]:
    return [block.text for block in blocks if isinstance(block, Paragraph)]
