"""Checks against the real downloaded corpus (data/raw). Skipped when it is absent (CI).

Expected values were read by hand from the official texts (mevzuat.gov.tr pages, the TCMB
PDF of 13.01.2026) on 2026-10-23/24; see docs/milestones/M2.md for the verification table.
"""

from pathlib import Path

import pytest

from finhak.ingest.scrape import decode_html
from finhak.parsing.blocks import html_blocks
from finhak.parsing.structure import Madde, ParsedText, parse_structure
from finhak.parsing.talimat import ParsedTalimat, parse_talimat, pdf_lines

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"

pytestmark = [
    pytest.mark.data,
    pytest.mark.skipif(not (RAW / "6502" / "text.html").exists(), reason="data/raw not downloaded"),
]


def _parsed(doc_id: str) -> ParsedText:
    html = decode_html((RAW / doc_id / "text.html").read_bytes(), doc_id)
    return parse_structure(html_blocks(html))


def _madde(doc: ParsedText, number: str, kind: str = "madde") -> Madde:
    return next(m for m in doc.maddeler if m.number == number and m.kind == kind)


@pytest.fixture(scope="module")
def talimat() -> ParsedTalimat:
    return parse_talimat(pdf_lines(RAW / "tcmb-ucret-talimat" / "source.pdf"))


def test_talimat_has_its_twelve_sections(talimat: ParsedTalimat) -> None:
    assert [s.number for s in talimat.sections] == [str(n) for n in range(1, 13)]
    assert talimat.sections[8].title == "Para ve kıymetli maden transfer işlemleri"


def test_talimat_eft_caps_from_6_1_2026_are_attached_to_bent_9c(talimat: ParsedTalimat) -> None:
    bent = next(b for b in talimat.sections[8].bents if b.label == "c")

    assert bent.footnote_refs == ("1",)
    (table,) = talimat.footnotes["1"].tables
    assert table == (
        ("EFT", "8.300 TL ve Altı", "8.300,01-399.000 TL", "399.000 TL Üzeri"),
        ("Mobil/İnternet/Düzenli Ödeme", "7,97", "15,96", "199,41"),
        ("ATM/Kiosk", "27,84", "55,69", "398,83"),
        ("Diğer", "39,87", "79,76", "797,68"),
    )
    assert talimat.footnotes["1"].text.startswith(
        "Tebliğin 7 nci maddesinin birinci fıkrası uyarınca 6/1/2026 tarihinden itibaren;"
    )


def test_talimat_annex_and_its_source_numbering_slip(talimat: ParsedTalimat) -> None:
    assert len(talimat.annex_items) == 17
    assert talimat.warnings == ("Ek-1: item 2.1 printed under group 3",)


def test_6502_definitions_article() -> None:
    madde = _madde(_parsed("6502"), "3")

    assert madde.title == "Tanımlar"
    (fikra,) = madde.fikralar
    assert fikra.lines[0] == "Bu Kanunun uygulanmasında;"
    assert fikra.bents[:4] == ("a", "b", "c", "ç")


def test_6502_paket_tur_has_fikra_6_written_with_an_inner_space() -> None:
    madde = _madde(_parsed("6502"), "51")

    assert [f.number for f in madde.fikralar] == list(range(1, len(madde.fikralar) + 1))


ORDINALS = {
    "birinci": 1, "ikinci": 2, "üçüncü": 3, "dördüncü": 4, "beşinci": 5,
    "altıncı": 6, "yedinci": 7, "sekizinci": 8, "dokuzuncu": 9, "onuncu": 10,
}  # fmt: skip


def _ordinal_mismatches(doc_id: str) -> list[str]:
    """Notes like "(Değişik sekizinci fıkra: …)" on a fıkra whose number is not 8."""
    import re

    pattern = re.compile(r"\((?:Değişik|Ek|Mülga)\s+(" + "|".join(ORDINALS) + r")\s+fıkra")
    mismatches = []
    for madde in _parsed(doc_id).maddeler:
        for fikra in madde.fikralar:
            for note in fikra.notes:
                match = pattern.match(note)
                if match and ORDINALS[match.group(1)] != fikra.number:
                    mismatches.append(f"{madde.label} f{fikra.number}: {note[:50]}")
    return mismatches


@pytest.mark.parametrize("doc_id", ["5411", "5464", "6502", "6493", "6698"])
def test_ordinal_fikra_notes_match_the_fikra_number(doc_id: str) -> None:
    # A cross-check of fıkra counting that does not depend on the parser's own rules.
    assert _ordinal_mismatches(doc_id) == []
