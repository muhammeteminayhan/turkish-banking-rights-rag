"""How a verified citation is shown: label, quote, snapshot date and notes.

Two owner decisions live here: every citation shows when its text was taken (the TCMB
Talimat also its version date), and a fıkra number counted from the paragraphs (5411,
5464 print none) is cited like a printed one but carries INFERRED_FIKRA_NOTE.
"""

from dataclasses import dataclass
from datetime import date

from finhak.parsing.chunker import Chunk

DISCLAIMER = (
    "Bu cevap mevzuat metinlerine dayanan bir bilgilendirmedir, hukuki tavsiye değildir. "
    "Kendi durumunuz için resmî metne bakın veya bir hukukçuya danışın."
)
INFERRED_FIKRA_NOTE = (
    "Fıkra numarası kaynak metinde yazmıyor; maddenin paragrafları sayılarak bulundu."
)
_KINDS = {"gecici": "geçici md.", "ek": "ek md."}


@dataclass(frozen=True)
class RenderedCitation:
    chunk_id: str
    label: str  # "5411 sayılı Bankacılık Kanunu md. 2/2"
    quote: str
    source_url: str
    snapshot: str  # when (and which version of) the text was taken
    notes: tuple[str, ...]


def citation_label(chunk: Chunk) -> str:
    if chunk.madde is None:  # an annex or table
        return f"{chunk.doc_label}, ek" + (f": {chunk.madde_title}" if chunk.madde_title else "")
    article = f"{chunk.doc_label} {_KINDS.get(chunk.madde_kind or '', 'md.')} {chunk.madde}"
    if chunk.unit == "bent" and chunk.bents:
        return f"{article} ({', '.join(chunk.bents)})"
    if chunk.fikra is None:
        return article
    fikra = f"{chunk.fikra}-{chunk.fikra_last}" if chunk.fikra_last else str(chunk.fikra)
    # "28/A/1" would read as article 28, letter A, number 1.
    return f"{article}, fıkra {fikra}" if "/" in chunk.madde else f"{article}/{fikra}"


def snapshot_note(chunk: Chunk) -> str:
    fetched = _tr_date(chunk.collected_on)
    if chunk.version_date is not None:
        return f"{_tr_date(chunk.version_date)} tarihli sürüm, {fetched} tarihinde alındı."
    return f"mevzuat.gov.tr'deki metin, {fetched} tarihinde alındı."


def render_citation(chunk: Chunk, quote: str) -> RenderedCitation:
    notes = (INFERRED_FIKRA_NOTE,) if chunk.fikra_inferred and chunk.fikra is not None else ()
    return RenderedCitation(
        chunk_id=chunk.id,
        label=citation_label(chunk),
        quote=quote,
        source_url=chunk.source_url,
        snapshot=snapshot_note(chunk),
        notes=notes,
    )


def _tr_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")
