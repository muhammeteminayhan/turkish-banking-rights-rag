"""TCMB Uygulama Talimatı: PDF lines → sections (n)), bents (a.), footnotes and Ek-1.

The lines below are copied from the 13.01.2026 version of the talimat (page/size/top as
pdfplumber reports them: body 12 pt, footnotes 10 pt, markers 6.5–8 pt).
"""

import pytest

from finhak.parsing.talimat import PdfLine, parse_talimat

pytestmark = pytest.mark.unit


def body(page: int, text: str, refs: tuple[str, ...] = ()) -> PdfLine:
    return PdfLine(page=page, kind="body", text=text, refs=refs)


def footnote(page: int, text: str, number: str | None = None) -> PdfLine:
    return PdfLine(page=page, kind="footnote", text=text, footnote_number=number)


TITLE = [
    body(1, "FİNANSAL TÜKETİCİLERDEN ALINACAK ÜCRETLERE İLİŞKİN USÛL VE"),
    body(1, "ESASLAR HAKKINDA TEBLİĞE (SAYI: 2020/7)"),
    body(1, "İLİŞKİN UYGULAMA TALİMATI"),
    body(1, "Bu Talimat, kuruluşlar tarafından finansal tüketicilere sunulan ürün veya hizmetlere"),
    body(1, "ilişkin olarak … uygulama ayrıntılarını göstermektedir."),
]


def test_title_and_introduction() -> None:
    doc = parse_talimat([*TITLE, body(1, "1) Kapsam"), body(1, "a. Tebliğ,")])

    assert doc.title == (
        "FİNANSAL TÜKETİCİLERDEN ALINACAK ÜCRETLERE İLİŞKİN USÛL VE ESASLAR HAKKINDA TEBLİĞE "
        "(SAYI: 2020/7) İLİŞKİN UYGULAMA TALİMATI"
    )
    assert doc.intro == (
        "Bu Talimat, kuruluşlar tarafından finansal tüketicilere sunulan ürün veya hizmetlere "
        "ilişkin olarak … uygulama ayrıntılarını göstermektedir."
    )


def test_sections_bents_and_numbered_items() -> None:
    doc = parse_talimat(
        [
            *TITLE,
            body(1, "1) Kapsam"),
            body(1, "a. Tebliğ,"),
            body(1, "1. 19/10/2005 tarihli ve 5411 sayılı Bankacılık Kanununun 3 üncü maddesinde"),
            body(1, "tanımlanan bankalar,"),
            body(1, "2. 21/11/2012 tarihli ve 6361 sayılı … verenler,"),
            body(
                1,
                "ile bu kuruluşlar tarafından finansal tüketiciye sunulan ürün veya "
                "hizmetleri kapsar.",
            ),
            body(1, "b. İlgili mevzuat çerçevesinde … Tebliğ kapsamında değildir."),
            body(1, "2) Sözleşme esasları"),
            body(2, "a. Kuruluşlar ile finansal tüketiciler arasında …"),
        ]
    )

    first, second = doc.sections
    assert (first.number, first.title) == ("1", "Kapsam")
    a, b = first.bents
    assert a.label == "a"
    assert a.lines == (
        "Tebliğ,",
        "1. 19/10/2005 tarihli ve 5411 sayılı Bankacılık Kanununun 3 üncü maddesinde "
        "tanımlanan bankalar,",
        "2. 21/11/2012 tarihli ve 6361 sayılı … verenler, ile bu kuruluşlar tarafından "
        "finansal tüketiciye sunulan ürün veya hizmetleri kapsar.",
    )
    assert (b.label, b.pages) == ("b", (1,))
    assert (second.number, second.title, second.bents[0].pages) == ("2", "Sözleşme esasları", (2,))


def test_bent_crossing_a_page_records_both_pages() -> None:
    doc = parse_talimat(
        [
            *TITLE,
            body(9, "9) Para ve kıymetli maden transfer işlemleri"),
            body(
                9, "c. EFT işlemlerinden alınacak ücret işlem tutarının 1.000 TL ve altında olması"
            ),
            body(10, "100 TL olarak uygulanır. Havale işlemlerinde ise …", refs=("1",)),
        ]
    )

    (bent,) = doc.sections[0].bents
    assert bent.pages == (9, 10)
    assert bent.footnote_refs == ("1",)


def test_footnote_with_its_table_is_attached_to_the_bent_that_cites_it() -> None:
    table = (
        ("EFT", "8.300 TL ve Altı", "8.300,01-399.000 TL", "399.000 TL Üzeri"),
        ("Mobil/İnternet/Düzenli Ödeme", "7,97", "15,96", "199,41"),
    )
    doc = parse_talimat(
        [
            *TITLE,
            body(9, "9) Para ve kıymetli maden transfer işlemleri"),
            body(9, "c. EFT işlemlerinden alınacak ücret …"),
            body(10, "100 TL olarak uygulanır.", refs=("1",)),
            footnote(10, "Tebliğin 7 nci maddesinin birinci fıkrası uyarınca 6/1/2026", number="1"),
            footnote(10, "tarihinden itibaren; EFT işlemlerinden alınabilecek azami"),
            PdfLine(page=10, kind="table", text="", table=table),
            body(10, "d. Düzenli ödemelerle yapılan EFT ve havale işlemleri …"),
        ]
    )

    note = doc.footnotes["1"]
    assert note.text == (
        "Tebliğin 7 nci maddesinin birinci fıkrası uyarınca 6/1/2026 tarihinden itibaren; "
        "EFT işlemlerinden alınabilecek azami"
    )
    assert note.tables == (table,)
    c, d = doc.sections[0].bents
    assert (c.footnote_refs, d.footnote_refs) == (("1",), ())


def test_annex_groups_and_items() -> None:
    doc = parse_talimat(
        [
            *TITLE,
            body(13, "12) Kampanyalar ve özel hizmetler"),
            body(13, "i. Referans mektubu … ücret tahsil edilemez."),
            body(
                14,
                "Ek-1 Finansal Tüketicilerden Alınacak Ücretlere İlişkin Ürün veya "
                "Hizmet Tanımları ve",
            ),
            body(14, "Kapsamları"),
            body(14, "1. Bireysel Krediler"),
            body(14, "1.1 Tahsis Ücreti: Finansal tüketicilere kullandırılan krediler için …"),
            body(14, "amacıyla alınan ücrettir."),
            body(14, "3. Para ve Kıymetli Maden Transferi"),
            body(
                14, "2.1. Elektronik Fon Transferi/Kıymetli Maden Transferi Ücreti: EFT gönderim ve"
            ),
            body(14, "3.2. Havale Ücreti: Havale gönderim işle…"),
        ]
    )

    assert doc.sections[-1].bents[-1].lines == ("Referans mektubu … ücret tahsil edilemez.",)
    assert doc.annex_title == (
        "Ek-1 Finansal Tüketicilerden Alınacak Ücretlere İlişkin Ürün veya Hizmet Tanımları ve "
        "Kapsamları"
    )
    items = doc.annex_items
    assert [(i.group, i.label) for i in items] == [("1", "1.1"), ("3", "2.1"), ("3", "3.2")]
    assert items[0].group_title == "Bireysel Krediler"
    assert items[0].text == (
        "Tahsis Ücreti: Finansal tüketicilere kullandırılan krediler için … "
        "amacıyla alınan ücrettir."
    )
    # The source numbers the first item of group 3 as "2.1."; it is kept as printed and reported.
    assert doc.warnings == ("Ek-1: item 2.1 printed under group 3",)
