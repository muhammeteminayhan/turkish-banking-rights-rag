"""Parsed structure → retrieval chunks (ids, notes, splitting, snapshot metadata)."""

from datetime import date

import pytest

from finhak.parsing.blocks import Endnote, Footnote, Paragraph, Separator, TableBlock
from finhak.parsing.chunker import DocInfo, chunk_mevzuat, chunk_talimat
from finhak.parsing.structure import parse_structure
from finhak.parsing.talimat import PdfLine, parse_talimat

pytestmark = pytest.mark.unit

LAW = DocInfo(
    doc_id="6502",
    title="TÜKETİCİNİN KORUNMASI HAKKINDA KANUN",
    label="6502 sayılı Tüketicinin Korunması Hakkında Kanun",
    doc_type="kanun",
    origin="mevzuat",
    number="6502",
    source_url="https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5",
    rg_date=date(2013, 11, 28),
    version_date=None,
    collected_on=date(2026, 10, 23),
)


def P(text: str, bold: bool = False, **refs: tuple[str, ...]) -> Paragraph:
    return Paragraph(text=text, bold=bold, **refs)


def _chunks(*blocks: object, info: DocInfo = LAW, max_chars: int = 2000):  # type: ignore[no-untyped-def]
    return chunk_mevzuat(info, parse_structure(list(blocks)), max_chars=max_chars)  # type: ignore[arg-type]


def test_one_chunk_per_fikra_with_citation_fields() -> None:
    chunks = _chunks(
        P("Tanımlar", bold=True),
        P("MADDE 3- (1) Bu Kanunun uygulanmasında;"),
        P("a) Bakan: Gümrük ve Ticaret Bakanını,"),
        P("(2) İkinci."),
    )

    first, second = chunks
    assert first.id == "6502:m3:f1"
    assert (first.unit, first.madde, first.madde_title, first.fikra, first.bents) == (
        "fikra",
        "3",
        "Tanımlar",
        1,
        ("a",),
    )
    assert first.text == "Bu Kanunun uygulanmasında;\na) Bakan: Gümrük ve Ticaret Bakanını,"
    assert second.id == "6502:m3:f2"
    assert (first.doc_label, first.rg_date, first.collected_on) == (
        "6502 sayılı Tüketicinin Korunması Hakkında Kanun",
        date(2013, 11, 28),
        date(2026, 10, 23),
    )


@pytest.mark.parametrize(
    ("heading", "expected_id"),
    [
        ("MADDE 28/A – (1) Metin.", "6502:m28A:f1"),
        ("GEÇİCİ MADDE 3 – (1) Metin.", "6502:gm3:f1"),
        ("EK MADDE 1 – (1) Metin.", "6502:em1:f1"),
    ],
)
def test_article_kinds_get_distinct_ids(heading: str, expected_id: str) -> None:
    (chunk,) = _chunks(P(heading))

    assert chunk.id == expected_id


def test_repealed_article_is_one_madde_chunk() -> None:
    (chunk,) = _chunks(P("Madde 7 — (Mülga: 5/12/2008-5815/5 md.)"))

    assert (chunk.id, chunk.unit, chunk.mulga, chunk.fikra) == ("6502:m7", "madde", True, None)
    assert chunk.text == "(Mülga: 5/12/2008-5815/5 md.)"


def test_inferred_fikra_is_flagged() -> None:
    chunks = _chunks(P("Madde 2 — Birinci paragraf."), P("İkinci paragraf."))

    assert [(c.id, c.fikra, c.fikra_inferred) for c in chunks] == [
        ("6502:m2:f1", 1, True),
        ("6502:m2:f2", 2, True),
    ]


def test_fikra_range_id() -> None:
    chunks = _chunks(P("MADDE 30- (1) Bir."), P("(2) ila (5) - (… yerine işlenmiştir.)"))

    assert [(c.id, c.fikra, c.fikra_last) for c in chunks] == [
        ("6502:m30:f1", 1, None),
        ("6502:m30:f2-5", 2, 5),
    ]


def test_notes_collect_heading_notes_fikra_notes_and_resolved_references() -> None:
    chunks = _chunks(
        P("MADDE 29- (Başlığı ile Birlikte Değişik:24/3/2022-7392/4 md.)", footnote_refs=("12",)),
        P("(1) (Değişik:24/10/2024-7529/7 md.) Tüketicinin …", sup_refs=("13",)),
        Footnote(number="12", text="Başlık değiştirilmiştir."),
        Footnote(number="13", text="Fıkra değiştirilmiştir."),
    )

    (chunk,) = chunks
    assert chunk.notes == (
        "(Başlığı ile Birlikte Değişik:24/3/2022-7392/4 md.)",
        "[12] Başlık değiştirilmiştir.",
        "(Değişik:24/10/2024-7529/7 md.)",
        "[13] Fıkra değiştirilmiştir.",
    )
    assert [a.reference for a in chunk.amendments] == ["7392/4", "7529/7"]


def test_superscript_refs_resolve_to_endnotes_in_regulations() -> None:
    (chunk,) = _chunks(
        P("MADDE 6 – (1) (Ek:RG-17/12/2010-27788) Metin.", sup_refs=("2",)),
        Separator(),
        Endnote(number="2", text="Bu değişiklik yayımından 6 ay sonra yürürlüğe girer."),
    )

    assert chunk.notes[-1] == "(2) Bu değişiklik yayımından 6 ay sonra yürürlüğe girer."


def test_unresolved_and_ambiguous_references_are_reported() -> None:
    doc = parse_structure(
        [
            P("MADDE 1 – (1) Bir.", sup_refs=("1",)),
            P("(2) İki.", sup_refs=("2",)),
            Separator(),
            P("(1) Bu değişiklik 1/10/2022 tarihinde yürürlüğe girer."),
            P("(1) Bu değişiklik 1/1/2023 tarihinde yürürlüğe girer."),
        ]
    )

    chunks = chunk_mevzuat(LAW, doc)

    assert chunks[0].notes == (
        "(1) [belirsiz: kaynakta aynı numaralı 2 not var] Bu değişiklik 1/10/2022 tarihinde "
        "yürürlüğe girer. | Bu değişiklik 1/1/2023 tarihinde yürürlüğe girer.",
    )
    assert chunks[1].notes == ("(2) [kaynakta bulunamadı]",)


def test_long_fikra_is_split_at_bents_and_each_part_keeps_the_intro() -> None:
    bents = [P(f"{letter}) " + "x" * 60) for letter in "abcdef"]

    chunks = _chunks(P("MADDE 3- (1) Bu Kanunun uygulanmasında;"), *bents, max_chars=200)

    assert [c.id for c in chunks] == ["6502:m3:f1:p1", "6502:m3:f1:p2", "6502:m3:f1:p3"]
    assert all(c.text.startswith("Bu Kanunun uygulanmasında;\n") for c in chunks)
    assert [c.bents for c in chunks] == [("a", "b"), ("c", "d"), ("e", "f")]
    assert all(len(c.text) <= 200 for c in chunks)


def test_tables_become_their_own_chunks_under_the_fikra() -> None:
    table = TableBlock(rows=(("Mobil", "7,97"),))
    chunks = _chunks(P("MADDE 9 – (1) Ücretler aşağıdaki gibidir."), table)

    _fikra, tablo = chunks
    assert tablo.id == "6502:m9:f1:t1"
    assert (tablo.unit, tablo.madde, tablo.fikra, tablo.text) == ("tablo", "9", 1, "Mobil | 7,97")


def test_annexes_are_chunked() -> None:
    table = TableBlock(rows=(("Birinci fıkrasındaki ceza miktarı", "(a) bendi", "3.973"),))
    chunks = _chunks(
        P("MADDE 88- (1) Bu Kanun hükümlerini Bakanlar Kurulu yürütür."),
        P("6502 SAYILI TÜKETİCİNİN KORUNMASI HAKKINDA KANUNUN 77 NCİ MADDESİNDEKİ CEZALAR"),
        P("(23/12/2025 tarihli ve 33116 sayılı Resmî Gazete’de yayımlanan …)"),
        table,
    )

    annex = chunks[-1]
    assert (annex.id, annex.unit, annex.madde) == ("6502:ek1", "ek", None)
    assert annex.madde_title == (
        "6502 SAYILI TÜKETİCİNİN KORUNMASI HAKKINDA KANUNUN 77 NCİ MADDESİNDEKİ CEZALAR"
    )
    assert annex.text == (
        "(23/12/2025 tarihli ve 33116 sayılı Resmî Gazete’de yayımlanan …)\n"
        "Birinci fıkrasındaki ceza miktarı | (a) bendi | 3.973"
    )


# --- talimat ------------------------------------------------------------------------

TALIMAT = DocInfo(
    doc_id="tcmb-ucret-talimat",
    title="… İLİŞKİN UYGULAMA TALİMATI",
    label="Ücret Tebliği Uygulama Talimatı (TCMB, 13.01.2026)",
    doc_type="talimat",
    origin="tcmb",
    number=None,
    source_url="https://www.tcmb.gov.tr/…/Bankacilik/",
    rg_date=None,
    version_date=date(2026, 1, 13),
    collected_on=date(2026, 10, 23),
)


def _talimat_lines() -> list[PdfLine]:
    table = (("EFT", "8.300 TL ve Altı"), ("Mobil/İnternet/Düzenli Ödeme", "7,97"))
    return [
        PdfLine(page=1, kind="body", text="… İLİŞKİN UYGULAMA TALİMATI"),
        PdfLine(page=1, kind="body", text="Bu Talimat, … göstermektedir."),
        PdfLine(page=9, kind="body", text="9) Para ve kıymetli maden transfer işlemleri"),
        PdfLine(page=9, kind="body", text="c. EFT işlemlerinden alınacak ücret … 5 TL’yi geçemez."),
        PdfLine(page=10, kind="body", text="100 TL olarak uygulanır.", refs=("1",)),
        PdfLine(
            page=10, kind="footnote", text="6/1/2026 tarihinden itibaren; …", footnote_number="1"
        ),
        PdfLine(page=10, kind="table", text="", table=table),
        PdfLine(page=14, kind="body", text="Ek-1 Ürün veya Hizmet Tanımları"),
        PdfLine(page=14, kind="body", text="1. Bireysel Krediler"),
        PdfLine(page=14, kind="body", text="1.1 Tahsis Ücreti: … alınan ücrettir."),
    ]


def test_talimat_chunks_keep_footnote_tables_and_version_date() -> None:
    chunks = chunk_talimat(TALIMAT, parse_talimat(_talimat_lines()))

    intro, bent, item = chunks
    assert (intro.id, intro.unit) == ("tcmb-ucret-talimat:giris", "giris")
    assert bent.id == "tcmb-ucret-talimat:s9:bc"
    assert (bent.unit, bent.madde, bent.madde_title, bent.bents, bent.pages) == (
        "bent",
        "9",
        "Para ve kıymetli maden transfer işlemleri",
        ("c",),
        (9, 10),
    )
    assert bent.notes == (
        "[Dipnot 1] 6/1/2026 tarihinden itibaren; …\n"
        "EFT | 8.300 TL ve Altı\nMobil/İnternet/Düzenli Ödeme | 7,97",
    )
    assert bent.version_date == date(2026, 1, 13)
    assert item.id == "tcmb-ucret-talimat:ek1:g1:1.1"
    assert (item.unit, item.madde_title, item.text) == (
        "ek",
        "Bireysel Krediler",
        "1.1 Tahsis Ücreti: … alınan ücrettir.",
    )


def test_chunk_ids_are_unique() -> None:
    chunks = _chunks(P("MADDE 1- (1) Bir."), P("MADDE 1- (1) Yine bir."))

    assert len({c.id for c in chunks}) == len(chunks)
    assert chunks[1].id == "6502:m1~2:f1"


def test_a_note_cited_twice_appears_once() -> None:
    (chunk,) = _chunks(
        P("Başlık (Değişik başlık:RG-23/9/2022-31962)", bold=True, sup_refs=("2",)),
        P("MADDE 10 – (1) (Değişik:RG-23/9/2022-31962) Metin.", sup_refs=("2",)),
        Separator(),
        Endnote(number="2", text="Bu değişiklik 1/10/2022 tarihinde yürürlüğe girer."),
    )

    assert chunk.notes == (
        "(Değişik başlık:RG-23/9/2022-31962)",
        "(2) Bu değişiklik 1/10/2022 tarihinde yürürlüğe girer.",
        "(Değişik:RG-23/9/2022-31962)",
    )


def test_repealed_article_keeps_the_note_found_on_its_fikra() -> None:
    (chunk,) = _chunks(P("MADDE 7 – (1) (Mülga:RG-1/1/2020-1)"))

    assert (chunk.id, chunk.mulga) == ("6502:m7", True)
    assert chunk.text == "(Mülga:RG-1/1/2020-1)"
    assert chunk.notes == ("(Mülga:RG-1/1/2020-1)",)
