"""blocks → madde / fıkra / bent. Every input line is taken from a real corpus text."""

import pytest

from finhak.parsing.blocks import (
    Endnote,
    Footnote,
    HistoryTable,
    Paragraph,
    Separator,
    TableBlock,
)
from finhak.parsing.structure import parse_structure, split_leading_notes

pytestmark = pytest.mark.unit


def P(text: str, bold: bool = False, **refs: tuple[str, ...]) -> Paragraph:
    return Paragraph(text=text, bold=bold, **refs)


HEADER = [
    P("TÜKETİCİNİN KORUNMASI HAKKINDA KANUN"),
    P("Kanun Numarası : 6502"),
    P("Kabul Tarihi : 7/11/2013"),
    P("BİRİNCİ KISIM"),
    P("Amaç, Kapsam ve Tanımlar", bold=True),
]


# --- notes ------------------------------------------------------------------------


def test_split_leading_notes() -> None:
    notes, rest = split_leading_notes(
        "(Ek:RG-17/12/2010-27788) (Değişik: RG-8/10/2013-28789 Mükerrer) (1) Geçici 1 inci"
    )

    assert notes == ("(Ek:RG-17/12/2010-27788)", "(Değişik: RG-8/10/2013-28789 Mükerrer)")
    assert rest == "(1) Geçici 1 inci"


def test_split_leading_notes_leaves_ordinary_parentheses() -> None:
    assert split_leading_notes("(a) bendi uygulanır.") == ((), "(a) bendi uygulanır.")


# --- articles ---------------------------------------------------------------------


def test_numbered_article_with_title_section_and_bents() -> None:
    blocks = [
        *HEADER,
        P("Tanımlar", bold=True),
        P("MADDE 3- (1) Bu Kanunun uygulanmasında;"),
        P("a) Bakan: Gümrük ve Ticaret Bakanını,"),
        P("ç) Genel Müdürlük: Tüketicinin Korunması ve Piyasa Gözetimi Genel Müdürlüğünü,"),
        P("ifade eder."),
        P("(2) İkinci fıkra."),
    ]

    doc = parse_structure(blocks)

    (madde,) = doc.maddeler
    assert (madde.kind, madde.number, madde.title) == ("madde", "3", "Tanımlar")
    assert madde.kisim == "BİRİNCİ KISIM — Amaç, Kapsam ve Tanımlar"
    first, second = madde.fikralar
    assert (first.number, first.inferred, first.bents) == (1, False, ("a", "ç"))
    assert first.lines == (
        "Bu Kanunun uygulanmasında;",
        "a) Bakan: Gümrük ve Ticaret Bakanını,",
        "ç) Genel Müdürlük: Tüketicinin Korunması ve Piyasa Gözetimi Genel Müdürlüğünü,",
        "ifade eder.",
    )
    assert (second.number, second.text) == (2, "İkinci fıkra.")


@pytest.mark.parametrize(
    ("heading", "kind", "number"),
    [
        ("MADDE 1- (1) Metin.", "madde", "1"),
        ("MADDE 7 – (1) Metin.", "madde", "7"),
        ("Madde 4 — Metin.", "madde", "4"),
        ("MADDE 28/A – (1) Metin.", "madde", "28/A"),
        ("GEÇİCİ MADDE 1 – (1) Metin.", "gecici", "1"),
        ("Geçici Madde 32 – (Ek:17/7/2019-7186/17 md.) Metin.", "gecici", "32"),
        ("EK MADDE 1 – (1) Metin.", "ek", "1"),
        ("Ek Madde 2 - Metin.", "ek", "2"),
    ],
)
def test_article_heading_variants(heading: str, kind: str, number: str) -> None:
    (madde,) = parse_structure([P(heading)]).maddeler

    assert (madde.kind, madde.number) == (kind, number)
    assert madde.fikralar[0].text == "Metin."


def test_sentence_mentioning_an_article_is_not_a_heading() -> None:
    blocks = [P("MADDE 1- (1) Metin."), P("Madde 5 kapsamında yapılan işlemler.")]

    (madde,) = parse_structure(blocks).maddeler

    assert madde.fikralar[0].lines[-1] == "Madde 5 kapsamında yapılan işlemler."


def test_heading_notes_are_kept_on_the_article() -> None:
    blocks = [
        P("İntibak", bold=True),
        P(
            "MADDE 28/A – (Ek:17/12/2010-27788) (Değişik: RG-8/10/2013-28789 Mükerrer)",
            sup_refs=("4",),
        ),
        P("(1) Geçici 1 inci maddenin yürürlüğe girdiği tarihten önce …"),
    ]

    (madde,) = parse_structure(blocks).maddeler

    assert madde.title == "İntibak"
    assert madde.notes == ("(Ek:17/12/2010-27788)", "(Değişik: RG-8/10/2013-28789 Mükerrer)")
    assert madde.sup_refs == ("4",)
    assert [f.number for f in madde.fikralar] == [1]


def test_fikra_notes_and_references_are_separated_from_the_text() -> None:
    blocks = [
        P(
            "MADDE 7 – (1) (Değişik cümle:RG-22/12/2023-32407) Bu Tebliğdeki parasal",
            sup_refs=("4",),
        )
    ]

    (fikra,) = parse_structure(blocks).maddeler[0].fikralar

    assert fikra.notes == ("(Değişik cümle:RG-22/12/2023-32407)",)
    assert fikra.text == "Bu Tebliğdeki parasal"
    assert fikra.sup_refs == ("4",)


# --- unnumbered (older laws) -----------------------------------------------------


def test_unnumbered_paragraphs_become_inferred_fikralar() -> None:
    blocks = [
        P("Kapsam", bold=True),
        P("Madde 2 — Türkiye'de kurulu mevduat bankaları … tabidir."),
        P("Özel kanunlarla kurulmuş olan bankalar hakkında da … uygulanır."),
        P("Bu Kanunda hüküm bulunmayan hallerde genel hükümler tatbik olunur."),
    ]

    (madde,) = parse_structure(blocks).maddeler

    assert [(f.number, f.inferred) for f in madde.fikralar] == [(1, True), (2, True), (3, True)]


def test_bents_and_lowercase_continuations_stay_in_the_inferred_fikra() -> None:
    blocks = [
        P("Madde 4 — Bankalar … aşağıda belirtilen faaliyetleri gerçekleştirebilirler:"),
        P("a) Mevduat kabulü."),
        P("b) Katılım fonu kabulü."),
        P("ifade eder."),
        P("Bankalar, … ayrıca izin alır."),
    ]

    first, second = parse_structure(blocks).maddeler[0].fikralar

    assert first.bents == ("a", "b")
    assert first.lines[-1] == "ifade eder."
    assert (second.number, second.inferred) == (2, True)


# --- repeals ------------------------------------------------------------------------


def test_repealed_article() -> None:
    (madde,) = parse_structure([P("Madde 7 — (Mülga: 5/12/2008-5815/5 md.)")]).maddeler

    assert madde.mulga
    assert madde.notes == ("(Mülga: 5/12/2008-5815/5 md.)",)


def test_repealed_fikra_inside_a_living_article() -> None:
    blocks = [
        P("MADDE 9 – (1) Birinci."),
        P("(2) (Mülga:RG-1/11/2012-28454)"),
        P("(3) Üçüncü."),
    ]

    (madde,) = parse_structure(blocks).maddeler

    assert not madde.mulga
    assert [f.mulga for f in madde.fikralar] == [False, True, False]


# --- tables, tail, annexes -------------------------------------------------------


def test_table_inside_an_article_belongs_to_the_current_fikra() -> None:
    table = TableBlock(rows=(("EFT", "8.300 TL ve Altı"), ("Mobil", "7,97")))
    blocks = [P("MADDE 9 – (1) Ücretler aşağıdaki gibidir."), table, P("(2) Sonra.")]

    first, _ = parse_structure(blocks).maddeler[0].fikralar

    assert first.tables == (table,)


def test_tail_after_the_last_article_is_split_into_notes_history_and_annexes() -> None:
    history = HistoryTable(rows=(("", "Yönetmeliğin Yayımlandığı Resmî Gazete"),))
    form = TableBlock(rows=(("Kuruluşun Unvanı", ""),))
    blocks = [
        P("MADDE 30 – (1) Bu Yönetmelik hükümlerini Bankacılık Düzenleme ve Denetleme Kurumu"),
        Separator(),
        Endnote(number="1", text="1/8/2009 tarihli … yürürlüğe girer."),
        P("(2) Bu değişiklik yayımından 6 ay sonra yürürlüğe girer."),
        history,
        P("Ek-1"),
        P("BAŞVURU FORMU"),
        form,
        Footnote(number="3", text="Kanunla değiştirilmiştir."),
    ]

    doc = parse_structure(blocks)

    assert [f.number for f in doc.maddeler[0].fikralar] == [1]
    assert doc.endnotes == {
        "1": ("1/8/2009 tarihli … yürürlüğe girer.",),
        "2": ("Bu değişiklik yayımından 6 ay sonra yürürlüğe girer.",),
    }
    assert doc.history == (history,)
    assert doc.footnotes == {"3": "Kanunla değiştirilmiştir."}
    (annex,) = doc.annexes
    assert annex.title == "Ek-1"
    assert annex.blocks == (P("BAŞVURU FORMU"), form)


def test_all_caps_title_after_the_last_article_starts_an_annex() -> None:
    table = TableBlock(rows=(("Birinci fıkrasındaki ceza miktarı", "(a) bendi", "3.973"),))
    blocks = [
        P("MADDE 88- (1) Bu Kanun hükümlerini Bakanlar Kurulu yürütür."),
        P("6502 SAYILI TÜKETİCİNİN KORUNMASI HAKKINDA"),
        P("KANUNUN 77 NCİ MADDESİNDEKİ İDARİ PARA CEZALARI"),
        P("(23/12/2025 tarihli ve 33116 sayılı Resmî Gazete’de yayımlanan …)"),
        table,
    ]

    doc = parse_structure(blocks)

    (annex,) = doc.annexes
    assert annex.title == (
        "6502 SAYILI TÜKETİCİNİN KORUNMASI HAKKINDA KANUNUN 77 NCİ MADDESİNDEKİ İDARİ PARA CEZALARI"
    )
    assert annex.blocks[-1] == table
    assert doc.maddeler[0].fikralar[0].lines == ("Bu Kanun hükümlerini Bakanlar Kurulu yürütür.",)


def test_cetvel_heading_starts_an_annex() -> None:
    blocks = [
        P("Madde 171 — Bu Kanun hükümlerini yürütür."),
        P("(I) SAYILI CETVEL"),
        P("KURUMU: X"),
    ]

    (annex,) = parse_structure(blocks).annexes

    assert annex.title == "(I) SAYILI CETVEL"


def test_duplicate_endnote_numbers_are_kept_not_merged() -> None:
    blocks = [
        P("MADDE 32 – (1) Yürütür."),
        Separator(),
        P("(1) Bu değişiklik 1/10/2022 tarihinde yürürlüğe girer."),
        P("(1) Bu değişiklik 1/1/2023 tarihinde yürürlüğe girer."),
    ]

    assert parse_structure(blocks).endnotes == {
        "1": (
            "Bu değişiklik 1/10/2022 tarihinde yürürlüğe girer.",
            "Bu değişiklik 1/1/2023 tarihinde yürürlüğe girer.",
        )
    }


def test_header_lines_are_not_reported_as_unplaced() -> None:
    doc = parse_structure([*HEADER, P("Amaç", bold=True), P("MADDE 1- (1) Amaç.")])

    assert doc.unplaced == ()
    assert doc.maddeler[0].title == "Amaç"


def test_text_outside_any_known_structure_is_reported() -> None:
    blocks = [P("MADDE 1- (1) Metin."), Separator(), P("Ekleri için tıklayınız.")]

    assert parse_structure(blocks).unplaced == ("Ekleri için tıklayınız.",)


# --- spelling variants seen in the corpus ------------------------------------------


@pytest.mark.parametrize(
    "note",
    [
        "(Başlığı ile Birlikte Değişik:24/3/2022-7392/4 md.)",
        "( Değişik:RG -21/12/2008-27087)",
        "(Değişik ibare:RG-9/8/2021-31563)",
        "(Mülga ikinci cümle:RG-1/1/2020-1)",
    ],
)
def test_note_spellings_are_recognised(note: str) -> None:
    assert split_leading_notes(f"{note} (1) Metin.") == ((note,), "(1) Metin.")


def test_note_on_its_own_line_before_the_first_fikra_belongs_to_the_article() -> None:
    blocks = [
        P("MADDE 29- (Başlığı ile Birlikte Değişik:24/3/2022-7392/4 md.)"),
        P("(1) Tüketicinin yazılı veya kalıcı veri saklayıcısı aracılığıyla …"),
    ]

    (madde,) = parse_structure(blocks).maddeler

    assert madde.notes == ("(Başlığı ile Birlikte Değişik:24/3/2022-7392/4 md.)",)
    assert [f.number for f in madde.fikralar] == [1]


def test_fikra_marker_with_inner_space() -> None:
    blocks = [P("MADDE 51- (5) Beşinci."), P("( 6) Tüketici, kendisinden kaynaklanmayan …")]

    (madde,) = parse_structure(blocks).maddeler

    assert [f.number for f in madde.fikralar] == [5, 6]


def test_fikra_range_written_as_ila() -> None:
    blocks = [
        P(
            "MADDE 30- (1) (10/12/2003 tarihli ve 5018 sayılı Kanun ile ilgili olup "
            "yerine işlenmiştir.)"
        ),
        P(
            "(2) ila (5) - (26/9/2004 tarihli ve 5237 sayılı Kanun ile ilgili olup "
            "yerine işlenmiştir.)"
        ),
        P("(6) (7/5/1987 tarihli ve 3359 sayılı …)"),
    ]

    fikralar = parse_structure(blocks).maddeler[0].fikralar

    assert [(f.number, f.last_number) for f in fikralar] == [(1, None), (2, 5), (6, None)]
    assert (
        fikralar[1].text
        == "(26/9/2004 tarihli ve 5237 sayılı Kanun ile ilgili olup yerine işlenmiştir.)"
    )


def test_endnote_continuation_lines_and_portal_links() -> None:
    blocks = [
        P("MADDE 11 – (1) Yürütür."),
        Separator(),
        Endnote(number="1", text="1/11/2012 tarihli … yürürlük tarihleri hakkında:"),
        P("RG-14/12/2012-28497 - Mevduat ve Katılım Fonunun Kabulüne …"),
        P("(2) Bu değişiklik yayımlandığı tarihten altı ay sonra yürürlüğe girer."),
        P("Yönetmeliğin ekini görmek için tıklayınız"),
    ]

    doc = parse_structure(blocks)

    assert doc.endnotes["1"] == (
        "1/11/2012 tarihli … yürürlük tarihleri hakkında: RG-14/12/2012-28497 - Mevduat ve Katılım "
        "Fonunun Kabulüne …",
    )
    assert doc.endnotes["2"] == (
        "Bu değişiklik yayımlandığı tarihten altı ay sonra yürürlüğe girer.",
    )
    assert doc.unplaced == ("Yönetmeliğin ekini görmek için tıklayınız",)


def test_amendment_note_at_the_end_of_a_title_moves_to_the_article() -> None:
    blocks = [
        P(
            "Sigorta, yan finansal ürün ve hizmet sunumu (Değişik başlık:RG-23/9/2022-31962)",
            bold=True,
            sup_refs=("2",),
        ),
        P("MADDE 10 – (1) (Değişik:RG-23/9/2022-31962) Tüketicinin yazılı olarak …"),
    ]

    (madde,) = parse_structure(blocks).maddeler

    assert madde.title == "Sigorta, yan finansal ürün ve hizmet sunumu"
    assert madde.notes == ("(Değişik başlık:RG-23/9/2022-31962)",)
    assert madde.sup_refs == ("2",)


# --- review findings (2026-10-24) ---------------------------------------------------


def test_unnumbered_definition_list_stays_one_fikra() -> None:
    # 5411 md. 3: each definition ends with "," and the list closes with "ifade eder."
    blocks = [
        P("Madde 3 — Bu Kanunda geçen;"),
        P("Kanun: 5411 sayılı Bankacılık Kanununu,"),
        P("Kurum: Bankacılık Düzenleme ve Denetleme Kurumunu,"),
        P("Banka: Mevduat bankaları, katılım bankaları …,"),
        P("ifade eder."),
        P("Bu Kanunun uygulanmasında ayrıca …"),
    ]

    fikralar = parse_structure(blocks).maddeler[0].fikralar

    assert [f.number for f in fikralar] == [1, 2]
    assert fikralar[0].lines[-1] == "ifade eder."


@pytest.mark.parametrize("ending", [",", ";", ":"])
def test_line_after_an_open_sentence_continues_the_fikra(ending: str) -> None:
    blocks = [P(f"Madde 9 — Bankalar aşağıdaki işlemleri yapamaz{ending}"), P("Kredi vermek.")]

    assert len(parse_structure(blocks).maddeler[0].fikralar) == 1


def test_note_naming_a_fikra_belongs_to_that_fikra_not_the_article() -> None:
    blocks = [
        P("Madde 63 — (Değişik birinci fıkra: 22/7/2010-6009/52 md.) Birinci paragraf."),
        P("İkinci paragraf."),
    ]

    (madde,) = parse_structure(blocks).maddeler

    assert madde.notes == ()
    first, second = madde.fikralar
    assert first.notes == ("(Değişik birinci fıkra: 22/7/2010-6009/52 md.)",)
    assert second.notes == ()


def test_dash_followed_by_a_full_stop() -> None:
    blocks = [P("Madde 129 —. (Değişik: 5/12/2008-5815/1 md.) Birinci."), P("İkinci.")]

    (madde,) = parse_structure(blocks).maddeler

    assert madde.number == "129"
    assert [f.lines[0] for f in madde.fikralar] == ["Birinci.", "İkinci."]


def test_two_article_numbers_on_one_heading_line() -> None:
    blocks = [
        P(
            "MADDE 38 – 39 – (3/6/2007 tarihli ve 5684 sayılı Kanun ile ilgili olup "
            "yerine işlenmiştir.)"
        )
    ]

    (madde,) = parse_structure(blocks).maddeler

    assert madde.number == "38-39"
    assert madde.fikralar[0].text.startswith("(3/6/2007")


@pytest.mark.parametrize("line", ["Ek olarak bildirim yapılır.", "EK SÜRE VERİLİR."])
def test_ordinary_lines_starting_with_ek_or_in_capitals_do_not_end_the_last_article(
    line: str,
) -> None:
    blocks = [P("MADDE 30 – (1) Birinci."), P(f"(2) {line}"), P(line)]

    doc = parse_structure(blocks)

    assert doc.annexes == ()
    assert len(doc.maddeler[0].fikralar) == 2


def test_leading_note_is_removed_from_a_title() -> None:
    blocks = [
        P("(Değişik başlık:RG-31/12/2013-28868) Kredi kartı limiti", bold=True),
        P("MADDE 22 – (1) Metin."),
    ]

    (madde,) = parse_structure(blocks).maddeler

    assert madde.title == "Kredi kartı limiti"
    assert madde.notes == ("(Değişik başlık:RG-31/12/2013-28868)",)


@pytest.mark.parametrize(
    "note",
    [
        "(Başlığı ile birlikte Mülga:RG-1/1/2020-1)",
        "(İptal: Anayasa Mahkemesinin 1/2/2024 tarihli ve E.:2023/110; K.:2024/35 "
        "sayılı Kararı ile.)",
    ],
)
def test_repealed_or_annulled_note_only_fikra_is_not_in_force(note: str) -> None:
    blocks = [P("MADDE 9 – (1) Birinci."), P(f"(2) {note}")]

    assert parse_structure(blocks).maddeler[0].fikralar[1].mulga
