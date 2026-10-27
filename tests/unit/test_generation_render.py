from datetime import date

import pytest

from chunk_factory import make_chunk
from finhak.generation.render import (
    DISCLAIMER,
    INFERRED_FIKRA_NOTE,
    citation_label,
    snapshot_note,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"madde": "22", "fikra": 2}, "6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 22/2"),
        ({"madde": "30", "fikra": 2, "fikra_last": 5}, "… md. 30/2-5"),
        ({"madde": "1", "madde_kind": "gecici", "fikra": 1}, "… geçici md. 1/1"),
        ({"madde": "1", "madde_kind": "ek", "fikra": 3}, "… ek md. 1/3"),
        ({"madde": "5", "unit": "madde", "fikra": None}, "… md. 5"),
        ({"madde": "28/A", "fikra": 1}, "… md. 28/A, fıkra 1"),  # "28/A/1" would be ambiguous
    ],
)
def test_citation_labels(fields: dict[str, object], expected: str) -> None:
    label = citation_label(make_chunk("6502:m1:f1", "metin", **fields))

    assert label == expected.replace("…", "6502 sayılı Tüketicinin Korunması Hakkında Kanun")


def test_talimat_bent_and_annex_labels() -> None:
    bent = make_chunk(
        "tcmb-ucret-talimat:s9:bc", "metin", madde="9", madde_kind=None, unit="bent",
        fikra=None, bents=("c",),
    )  # fmt: skip
    annex = make_chunk(
        "6502:ek1:p1", "tablo", madde=None, madde_kind=None, unit="ek", fikra=None,
        madde_title="İDARİ PARA CEZALARI TABLOSU",
    )  # fmt: skip

    assert citation_label(bent).endswith(" md. 9 (c)")
    assert citation_label(annex) == (
        "6502 sayılı Tüketicinin Korunması Hakkında Kanun, ek: İDARİ PARA CEZALARI TABLOSU"
    )


def test_an_inferred_fikra_number_is_cited_with_a_note() -> None:
    from finhak.generation.render import render_citation

    chunk = make_chunk("5411:m2:f2", "Bu Kanun bankaları kapsar.", madde="2", fikra=2,
                       fikra_inferred=True)  # fmt: skip

    rendered = render_citation(chunk, "Bu Kanun bankaları kapsar.")

    assert rendered.label.endswith(" md. 2/2")
    assert INFERRED_FIKRA_NOTE in rendered.notes
    assert "sayılarak" in INFERRED_FIKRA_NOTE


def test_snapshot_dates_name_the_version_and_the_download() -> None:
    mevzuat = make_chunk("6502:m1:f1", "metin", collected_on=date(2026, 10, 23))
    talimat = make_chunk(
        "tcmb-ucret-talimat:s9:bc", "metin", madde="9", madde_kind=None, unit="bent",
        fikra=None, version_date=date(2026, 1, 13), collected_on=date(2026, 10, 23),
    )  # fmt: skip

    assert snapshot_note(mevzuat) == "mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı."
    assert snapshot_note(talimat) == "13.01.2026 tarihli sürüm, 23.10.2026 tarihinde alındı."


def test_the_disclaimer_says_this_is_not_legal_advice() -> None:
    assert "hukuki tavsiye değildir" in DISCLAIMER
