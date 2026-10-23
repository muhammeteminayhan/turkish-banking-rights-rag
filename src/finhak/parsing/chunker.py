"""Parsed texts → retrieval chunks written to data/processed/chunks.jsonl.

Chunk ids (stable, human-readable, used as citation keys from M4 on):
    6502:m3:f1          madde 3, fıkra 1            6502:m3:f1:p2    second part of a long fıkra
    6502:gm3:f1         geçici madde 3               6502:em1:f1      ek madde 1
    kart-yon:m28A:f1    madde 28/A                   6698:m30:f2-5    "(2) ila (5)"
    6502:m7             a repealed article           6502:m9:f1:t1    first table in fıkra 1
    6502:ek1            first annex                  …:s9:bc          talimat section 9, bent c
    …:ek1:g3:2.1        talimat Ek-1, group 3, item "2.1" as printed

`text` is the legal text as published (footnote markers removed). `notes` holds what
explains or updates it: amendment notes, resolved footnotes/endnotes and, for the talimat,
footnote tables with the current amounts. Retrieval and answer verification use both.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from finhak.ingest.scrape import find_amendments
from finhak.ingest.sources import DocType, Origin
from finhak.parsing.blocks import TableBlock
from finhak.parsing.structure import Annex, Fikra, Madde, MaddeKind, ParsedText
from finhak.parsing.talimat import ParsedTalimat, Table, TalimatBent

Unit = Literal["fikra", "madde", "tablo", "ek", "giris", "bent"]
MAX_CHUNK_CHARS = 2000
_ID_PREFIX: dict[str, str] = {"madde": "m", "gecici": "gm", "ek": "em"}


@dataclass(frozen=True)
class DocInfo:
    doc_id: str
    title: str
    label: str
    doc_type: DocType
    origin: Origin
    number: str | None
    source_url: str
    rg_date: date | None
    version_date: date | None
    collected_on: date


class ChunkAmendment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    date: date
    kind: Literal["rg", "law"]
    reference: str


class Chunk(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    doc_id: str
    doc_title: str
    doc_label: str
    doc_type: DocType
    origin: Origin
    unit: Unit
    madde: str | None
    madde_kind: MaddeKind | None
    madde_title: str | None
    fikra: int | None
    fikra_last: int | None
    fikra_inferred: bool
    bents: tuple[str, ...]
    part: int | None
    kisim: str | None
    bolum: str | None
    text: str
    notes: tuple[str, ...]
    amendments: tuple[ChunkAmendment, ...]
    mulga: bool
    pages: tuple[int, ...]
    source_url: str
    rg_date: date | None
    version_date: date | None
    collected_on: date


@dataclass(frozen=True)
class _Place:
    """Where in the document a chunk sits; shared by all chunks of one article."""

    madde: str | None = None
    madde_kind: MaddeKind | None = None
    madde_title: str | None = None
    kisim: str | None = None
    bolum: str | None = None


# --- mevzuat ---------------------------------------------------------------------


def chunk_mevzuat(
    info: DocInfo, doc: ParsedText, max_chars: int = MAX_CHUNK_CHARS
) -> tuple[Chunk, ...]:
    resolver = _Resolver(doc)
    chunks: list[Chunk] = []
    seen: dict[str, int] = {}
    for madde in doc.maddeler:
        key = _unique(f"{_ID_PREFIX[madde.kind]}{madde.number.replace('/', '')}", seen)
        chunks.extend(_madde_chunks(info, madde, f"{info.doc_id}:{key}", resolver, max_chars))
    for index, annex in enumerate(doc.annexes, start=1):
        chunks.extend(_annex_chunks(info, annex, f"{info.doc_id}:ek{index}", max_chars))
    return tuple(chunks)


def _unique(key: str, seen: dict[str, int]) -> str:
    seen[key] = seen.get(key, 0) + 1
    return key if seen[key] == 1 else f"{key}~{seen[key]}"


def _madde_chunks(
    info: DocInfo, madde: Madde, base: str, resolver: "_Resolver", max_chars: int
) -> list[Chunk]:
    place = _Place(madde.number, madde.kind, madde.title, madde.kisim, madde.bolum)
    heading_notes = (*madde.notes, *resolver.notes(madde.footnote_refs, madde.sup_refs))
    if madde.mulga or not madde.fikralar:
        # "MADDE 7 – (1) (Mülga:…)": the repeal note sits on the fıkra, keep it.
        fikra_notes = [note for fikra in madde.fikralar for note in fikra.notes]
        text = " ".join((*madde.notes, *fikra_notes)) or madde.label
        notes = (*heading_notes, *fikra_notes)
        return [_chunk(info, base, "madde", place, text, notes, mulga=madde.mulga)]

    chunks: list[Chunk] = []
    for fikra in madde.fikralar:
        number = f"{fikra.number}-{fikra.last_number}" if fikra.last_number else str(fikra.number)
        fikra_id = f"{base}:f{number}"
        notes = (
            *heading_notes,
            *fikra.notes,
            *resolver.notes(fikra.footnote_refs, fikra.sup_refs),
        )
        parts = _split(fikra, max_chars)
        for index, (lines, bents) in enumerate(parts, start=1):
            chunks.append(
                _chunk(
                    info,
                    fikra_id if len(parts) == 1 else f"{fikra_id}:p{index}",
                    "fikra",
                    place,
                    "\n".join(lines) or " ".join(fikra.notes),
                    notes,
                    fikra=fikra,
                    bents=bents,
                    part=index if len(parts) > 1 else None,
                    mulga=fikra.mulga,
                )
            )
        for index, table in enumerate(fikra.tables, start=1):
            chunks.append(
                _chunk(
                    info, f"{fikra_id}:t{index}", "tablo", place, table.render(), notes, fikra=fikra
                )
            )
    return chunks


def _split(fikra: Fikra, max_chars: int) -> list[tuple[list[str], tuple[str, ...]]]:
    """One part, or parts cut at bent lines that each repeat the fıkra's opening line."""
    if len(fikra.text) <= max_chars or not fikra.bents:
        return [(list(fikra.lines), fikra.bents)]
    intro, rest = fikra.lines[0], list(fikra.lines[1:])
    parts: list[tuple[list[str], list[str]]] = []
    for line in rest:
        bent = _bent_label(line)
        current = parts[-1] if parts else None
        length = len(intro) + sum(len(x) + 1 for x in current[0]) if current else 0
        if current is None or (bent and length + len(line) + 1 > max_chars):
            parts.append(([], []))
            current = parts[-1]
        current[0].append(line)
        if bent:
            current[1].append(bent)
    return [([intro, *lines], tuple(bents)) for lines, bents in parts]


def _bent_label(line: str) -> str | None:
    head, _, _ = line.partition(") ")
    return head if head and len(head) <= 2 and head.isalpha() and head.islower() else None


def _annex_chunks(info: DocInfo, annex: Annex, base: str, max_chars: int) -> list[Chunk]:
    place = _Place(madde_title=annex.title)
    texts = [b.render() if isinstance(b, TableBlock) else b.text for b in annex.blocks]
    groups: list[list[str]] = [[]]
    for text in texts:
        if groups[-1] and sum(len(t) + 1 for t in groups[-1]) + len(text) > max_chars:
            groups.append([])
        groups[-1].append(text)
    return [
        _chunk(
            info,
            base if len(groups) == 1 else f"{base}:p{index}",
            "ek",
            place,
            "\n".join(group) or annex.title,
            (),
            part=index if len(groups) > 1 else None,
        )
        for index, group in enumerate(groups, start=1)
    ]


class _Resolver:
    """Footnote ([n]) and endnote ((n)) references → note texts, flagging what is wrong."""

    def __init__(self, doc: ParsedText) -> None:
        self._footnotes = doc.footnotes
        self._endnotes = doc.endnotes

    def notes(self, footnote_refs: Iterable[str], sup_refs: Iterable[str]) -> list[str]:
        resolved = [self._footnote(ref) for ref in footnote_refs]
        for ref in sup_refs:
            # Regulations number endnotes with <sup>; laws put footnote numbers in <sup>.
            resolved.append(self._endnote(ref) if self._endnotes else self._footnote(ref))
        return resolved

    def _footnote(self, ref: str) -> str:
        text = self._footnotes.get(ref)
        return f"[{ref}] {text}" if text is not None else f"[{ref}] [kaynakta bulunamadı]"

    def _endnote(self, ref: str) -> str:
        texts = self._endnotes.get(ref)
        if not texts:
            return f"({ref}) [kaynakta bulunamadı]"
        if len(texts) > 1:
            joined = " | ".join(texts)
            return f"({ref}) [belirsiz: kaynakta aynı numaralı {len(texts)} not var] {joined}"
        return f"({ref}) {texts[0]}"


# --- talimat ---------------------------------------------------------------------


def chunk_talimat(info: DocInfo, doc: ParsedTalimat) -> tuple[Chunk, ...]:
    chunks: list[Chunk] = []
    if doc.intro:
        chunks.append(_chunk(info, f"{info.doc_id}:giris", "giris", _Place(), doc.intro, ()))
    for section in doc.sections:
        place = _Place(madde=section.number, madde_title=section.title)
        for bent in section.bents:
            chunks.append(_talimat_bent(info, doc, place, section.number, bent))
    for item in doc.annex_items:
        chunk_id = f"{info.doc_id}:ek1:g{item.group}:{item.label}"
        place = _Place(madde_title=item.group_title)
        chunks.append(
            _chunk(info, chunk_id, "ek", place, f"{item.label} {item.text}", (), pages=(item.page,))
        )
    return tuple(chunks)


def _talimat_bent(
    info: DocInfo, doc: ParsedTalimat, place: _Place, section: str, bent: TalimatBent
) -> Chunk:
    notes: list[str] = []
    for ref in bent.footnote_refs:
        footnote = doc.footnotes.get(ref)
        if footnote is None:
            notes.append(f"[Dipnot {ref}] [kaynakta bulunamadı]")
            continue
        tables = "\n".join(_render(table) for table in footnote.tables)
        notes.append(f"[Dipnot {ref}] {footnote.text}" + (f"\n{tables}" if tables else ""))
    notes.extend(_render(table) for table in bent.tables)
    return _chunk(
        info,
        f"{info.doc_id}:s{section}:b{bent.label}",
        "bent",
        place,
        bent.text,
        tuple(notes),
        bents=(bent.label,),
        pages=bent.pages,
    )


def _render(table: Table) -> str:
    return "\n".join(" | ".join(row) for row in table)


# --- shared ------------------------------------------------------------------------


def _chunk(
    info: DocInfo,
    chunk_id: str,
    unit: Unit,
    place: _Place,
    text: str,
    notes: Sequence[str],
    fikra: Fikra | None = None,
    bents: tuple[str, ...] = (),
    part: int | None = None,
    mulga: bool = False,
    pages: tuple[int, ...] = (),
) -> Chunk:
    notes = tuple(dict.fromkeys(notes))  # the same endnote can be cited by title and fıkra
    amendments = find_amendments(" ".join((*notes, text)))
    return Chunk(
        id=chunk_id,
        doc_id=info.doc_id,
        doc_title=info.title,
        doc_label=info.label,
        doc_type=info.doc_type,
        origin=info.origin,
        unit=unit,
        madde=place.madde,
        madde_kind=place.madde_kind,
        madde_title=place.madde_title,
        fikra=fikra.number if fikra else None,
        fikra_last=fikra.last_number if fikra else None,
        fikra_inferred=fikra.inferred if fikra else False,
        bents=bents,
        part=part,
        kisim=place.kisim,
        bolum=place.bolum,
        text=text,
        notes=tuple(notes),
        amendments=tuple(
            ChunkAmendment(date=a.date, kind=a.kind, reference=a.reference) for a in amendments
        ),
        mulga=mulga,
        pages=pages,
        source_url=info.source_url,
        rg_date=info.rg_date,
        version_date=info.version_date,
        collected_on=info.collected_on,
    )
