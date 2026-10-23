"""HTML → blocks. Inputs mirror the markup mevzuat.gov.tr actually serves (Word HTML)."""

import pytest

from finhak.parsing.blocks import (
    Endnote,
    Footnote,
    HistoryTable,
    Paragraph,
    Separator,
    TableBlock,
    html_blocks,
)

pytestmark = pytest.mark.unit


def _page(body: str) -> str:
    return f"<html><body>{body}</body></html>"


def test_paragraph_text_is_normalised() -> None:
    (block,) = html_blocks(_page("<p>  (1) Bu  Kanunun\n amacı;\xa0kamu</p>"))

    assert block == Paragraph(text="(1) Bu Kanunun amacı; kamu")


def test_empty_paragraphs_are_dropped() -> None:
    assert html_blocks(_page("<p> </p><p>&nbsp;</p><p>Amaç</p>")) == (Paragraph(text="Amaç"),)


def test_fully_bold_paragraph_is_marked_bold() -> None:
    blocks = html_blocks(
        _page(
            "<p><b><span>Tanımlar</span></b></p>"
            "<p><b><span>MADDE 3- </span></b><span>(1) Bu Kanunun uygulanmasında;</span></p>"
        )
    )

    assert [b.bold for b in blocks if isinstance(b, Paragraph)] == [True, False]


def test_superscript_markers_are_moved_out_of_the_text() -> None:
    html = (
        '<p class="metin"><b><span>MADDE 7 – </span></b><span>(1) '
        "<b>(Değişik cümle:RG-22/12/2023-32407)<sup>(4)</sup></b> Bu Tebliğdeki parasal</span></p>"
    )

    (block,) = html_blocks(_page(html))

    assert block == Paragraph(
        text="MADDE 7 – (1) (Değişik cümle:RG-22/12/2023-32407) Bu Tebliğdeki parasal",
        sup_refs=("4",),
    )


def test_bracket_footnote_markers_are_moved_out_of_the_text() -> None:
    html = '<p>Madde 32 <a href="#_ftn71">[71]</a> – (Ek:17/7/2019-7186/17 md.) Metin. [72]</p>'

    (block,) = html_blocks(_page(html))

    assert block == Paragraph(
        text="Madde 32 – (Ek:17/7/2019-7186/17 md.) Metin.", footnote_refs=("71", "72")
    )


def test_bracketed_superscripts_are_footnote_refs() -> None:
    # Laws put footnote numbers in <sup>, sometimes with brackets: <sup>[32]</sup>, <sup>13</sup>.
    (block,) = html_blocks(_page("<p>(3) Metin.<sup>[32]</sup> Devam<sup>13</sup></p>"))

    assert block == Paragraph(text="(3) Metin. Devam", footnote_refs=("32",), sup_refs=("13",))


def test_paragraph_starting_with_a_superscript_is_an_endnote() -> None:
    html = "<p><sup>(2)</sup> Bu değişiklik yayımından 6 ay sonra yürürlüğe girer.</p>"

    assert html_blocks(_page(html)) == (
        Endnote(number="2", text="Bu değişiklik yayımından 6 ay sonra yürürlüğe girer."),
    )


def test_plain_text_fikra_marker_is_not_an_endnote() -> None:
    (block,) = html_blocks(_page("<p>(2) Bu değişiklik yürürlüğe girer.</p>"))

    assert isinstance(block, Paragraph)


def test_underscore_line_is_a_separator() -> None:
    assert html_blocks(_page("<p>__________</p>")) == (Separator(),)


def test_footnote_bodies_become_footnote_blocks() -> None:
    html = (
        '<p><a href="#_ftnref1">[1]</a> '
        "2/7/2018 tarihli ve 703 sayılı KHK’nin 166 ncı maddesiyle…</p>"
    )

    assert html_blocks(_page(html)) == (
        Footnote(number="1", text="2/7/2018 tarihli ve 703 sayılı KHK’nin 166 ncı maddesiyle…"),
    )


def test_single_column_layout_tables_are_read_as_paragraphs() -> None:
    html = (
        "<table><tr><td><p>TÜKETİCİ HAKEM HEYETLERİ YÖNETMELİĞİ</p>"
        "<table><tr><td><p><b>Amaç</b></p>"
        "<p>MADDE 1- (1) Bu Yönetmeliğin amacı…</p></td></tr></table>"
        "</td></tr></table>"
    )

    blocks = html_blocks(_page(html))

    assert [b.text for b in blocks if isinstance(b, Paragraph)] == [
        "TÜKETİCİ HAKEM HEYETLERİ YÖNETMELİĞİ",
        "Amaç",
        "MADDE 1- (1) Bu Yönetmeliğin amacı…",
    ]


def test_multi_column_tables_become_table_blocks() -> None:
    html = (
        "<table><tr><td>6502 sayılı Kanunun 77 nci maddesinin;</td><td>TL</td></tr>"
        "<tr><td>Birinci fıkrasındaki ceza miktarı</td><td>(a) bendi</td>"
        "<td>3.973</td></tr></table>"
    )

    (block,) = html_blocks(_page(html))

    assert block == TableBlock(
        rows=(
            ("6502 sayılı Kanunun 77 nci maddesinin;", "TL"),
            ("Birinci fıkrasındaki ceza miktarı", "(a) bendi", "3.973"),
        )
    )
    assert block.render() == (
        "6502 sayılı Kanunun 77 nci maddesinin; | TL\n"
        "Birinci fıkrasındaki ceza miktarı | (a) bendi | 3.973"
    )


@pytest.mark.parametrize(
    "first_row",
    [
        "<td></td><td>Tebliğin Yayımlandığı Resmî Gazete</td>",
        "<td></td><td>Yönetmeliğin Yayımlandığı Resmî Gazete</td>",
        "<td>Değiştiren Kanunun/KHK’nin/ Numarası</td>"
        "<td>6502 Sayılı Kanunun Değişen Maddeleri</td>"
        "<td>Yürürlüğe Giriş Tarihi</td>",
    ],
)
def test_amendment_history_tables_are_recognised(first_row: str) -> None:
    html = f"<table><tr>{first_row}</tr><tr><td>1.</td><td>9/8/2021</td><td>31563</td></tr></table>"

    (block,) = html_blocks(_page(html))

    assert isinstance(block, HistoryTable)
    assert block.rows[-1] == ("1.", "9/8/2021", "31563")


def test_history_table_rows_are_indexed_by_their_number() -> None:
    table = HistoryTable(
        rows=(
            ("", "Tebliğin Yayımlandığı Resmî Gazete"),
            ("", "Tarihi", "Sayısı"),
            ("", "7/3/2020", "31061"),
            ("1.", "9/8/2021", "31563"),
            ("2.", "31/12/2020", "31351"),
        )
    )

    assert table.numbered_rows() == {"1": ("9/8/2021", "31563"), "2": ("31/12/2020", "31351")}


def test_blocks_keep_document_order_across_tables() -> None:
    html = "<p>Önce</p><table><tr><td>a</td><td>b</td></tr></table><p>Sonra</p>"

    assert [type(b).__name__ for b in html_blocks(_page(html))] == [
        "Paragraph",
        "TableBlock",
        "Paragraph",
    ]


def test_superscripts_inside_tables_do_not_leak_into_cells() -> None:
    html = "<table><tr><td>a<sup>(2)</sup></td><td>b</td></tr></table>"

    (block,) = html_blocks(_page(html))

    assert block == TableBlock(rows=(("a", "b"),))


@pytest.mark.parametrize(
    ("html", "text"),
    [
        ("<p><span>sistemlerine</span><span>,</span> hizmetler</p>", "sistemlerine, hizmetler"),
        ("<p>saat <span>16.30</span><span>,</span> sonra<span>.</span></p>", "saat 16.30, sonra."),
        (
            "<p>kartın <span>setini/</span><span>setlerini</span> belirler</p>",
            "kartın setini/setlerini belirler",
        ),
        (
            "<p><b>(</b><b>Ek:RG-13/11/2021-31658)</b>Hesaptan</p>",
            "(Ek:RG-13/11/2021-31658) Hesaptan",
        ),
        ("<p>“<span>ibare</span>” şeklinde</p>", "“ibare” şeklinde"),
    ],
)
def test_span_boundaries_do_not_break_turkish_punctuation(html: str, text: str) -> None:
    (block,) = html_blocks(_page(html))

    assert block.text == text
