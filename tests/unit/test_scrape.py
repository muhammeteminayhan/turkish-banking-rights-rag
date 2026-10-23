from collections.abc import Callable
from datetime import date

import pytest

from finhak.ingest.scrape import (
    Amendment,
    ScrapeError,
    find_amendments,
    parse_page,
    parse_text,
)

pytestmark = pytest.mark.unit

Fixture = Callable[[str], bytes]
BASE = "https://www.mevzuat.gov.tr"


def _page_url(no: int, tur: int) -> str:
    return f"{BASE}/mevzuat?MevzuatNo={no}&MevzuatTur={tur}&MevzuatTertip=5"


# --- parse_page ------------------------------------------------------------------


def test_parse_page_reads_rg_info_text_url_and_files_for_a_law(mevzuat_fixture: Fixture) -> None:
    info = parse_page(mevzuat_fixture("page_kanun_6502.html").decode(), _page_url(6502, 1))

    assert info.rg_date == date(2013, 11, 28)
    assert info.rg_number == "28835"
    assert info.text_url == (
        f"{BASE}/anasayfa/MevzuatFihristDetayIframe?MevzuatTur=1&MevzuatNo=6502&MevzuatTertip=5"
    )
    assert info.file_urls == (
        f"{BASE}/MevzuatMetin/1.5.6502.doc",
        f"{BASE}/MevzuatMetin/1.5.6502.pdf",
    )


def test_parse_page_handles_a_regulation_without_pdf(mevzuat_fixture: Fixture) -> None:
    info = parse_page(mevzuat_fixture("page_yonetmelik_11180.html").decode(), _page_url(11180, 7))

    assert info.rg_date == date(2007, 3, 10)
    assert info.file_urls == (f"{BASE}/MevzuatMetin/yonetmelik/7.5.11180.doc",)


def test_parse_page_uses_the_yonetmelik_path_for_a_teblig(mevzuat_fixture: Fixture) -> None:
    info = parse_page(mevzuat_fixture("page_teblig_34343.html").decode(), _page_url(34343, 9))

    assert info.rg_number == "31061"
    assert info.file_urls == (
        f"{BASE}/MevzuatMetin/yonetmelik/9.5.34343.doc",
        f"{BASE}/MevzuatMetin/yonetmelik/9.5.34343.pdf",
    )


def test_parse_page_without_rg_info_raises() -> None:
    html = '<iframe id="mevzuatDetayIframe" src="/anasayfa/MevzuatFihristDetayIframe?x=1"></iframe>'

    with pytest.raises(ScrapeError, match="Resmî Gazete"):
        parse_page(html, _page_url(1, 1))


def test_parse_page_without_text_iframe_raises() -> None:
    html = "<div>Resmî Gazete Tarihi: 28.11.2013 Resmî Gazete Sayısı: 28835</div>"

    with pytest.raises(ScrapeError, match="iframe"):
        parse_page(html, _page_url(1, 1))


def test_parse_page_ignores_file_links_on_other_hosts() -> None:
    html = (
        "<div>Resmî Gazete Tarihi: 28.11.2013 Resmî Gazete Sayısı: 28835</div>"
        '<iframe id="mevzuatDetayIframe" src="/anasayfa/MevzuatFihristDetayIframe?x=1"></iframe>'
        '<a href="https://evil.example/MevzuatMetin/1.5.6502.pdf">x</a>'
        '<a href="https://mevzuat.gov.tr/MevzuatMetin/1.5.6502.doc">bare host</a>'
        '<a href="https://www.mevzuat.gov.tr/MevzuatMetin/1.5.6502.exe">y</a>'
        '<a href="/MevzuatMetin/1.5.6502.pdf">z</a>'
    )

    info = parse_page(html, _page_url(6502, 1))

    assert info.file_urls == (f"{BASE}/MevzuatMetin/1.5.6502.pdf",)


RG_DIV = "<div>Resmî Gazete Tarihi: 28.11.2013 Resmî Gazete Sayısı: 28835</div>"
TEXT_IFRAME = (
    '<iframe id="mevzuatDetayIframe" '
    'src="/anasayfa/MevzuatFihristDetayIframe?MevzuatTur=1&amp;MevzuatNo=6502"></iframe>'
)


@pytest.mark.parametrize(
    "src",
    [
        "https://evil.example/anasayfa/MevzuatFihristDetayIframe?x=1",
        "//evil.example/anasayfa/MevzuatFihristDetayIframe?x=1",
        "/somewhere/else?MevzuatFihristDetayIframe",
        "http://www.mevzuat.gov.tr/anasayfa/MevzuatFihristDetayIframe?x=1",
    ],
)
def test_parse_page_refuses_a_text_iframe_outside_mevzuat(src: str) -> None:
    html = RG_DIV + f'<iframe id="mevzuatDetayIframe" src="{src}"></iframe>'

    with pytest.raises(ScrapeError, match="iframe"):
        parse_page(html, _page_url(6502, 1))


def test_parse_page_refuses_two_different_files_with_the_same_extension() -> None:
    html = (
        RG_DIV
        + TEXT_IFRAME
        + '<a href="/MevzuatMetin/1.5.6502.pdf">a</a><a href="/MevzuatMetin/1.5.6503.pdf">b</a>'
    )

    with pytest.raises(ScrapeError, match="pdf"):
        parse_page(html, _page_url(6502, 1))


def test_parse_page_accepts_the_same_link_twice() -> None:
    html = RG_DIV + TEXT_IFRAME + '<a href="/MevzuatMetin/1.5.6502.pdf">a</a>' * 2

    assert parse_page(html, _page_url(6502, 1)).file_urls == (f"{BASE}/MevzuatMetin/1.5.6502.pdf",)


def test_parse_page_with_an_impossible_rg_date_raises_scrape_error() -> None:
    html = RG_DIV.replace("28.11.2013", "31.02.2013") + TEXT_IFRAME

    with pytest.raises(ScrapeError, match="date"):
        parse_page(html, _page_url(6502, 1))


# --- parse_text ------------------------------------------------------------------


def test_parse_text_reads_law_title_and_declared_number(mevzuat_fixture: Fixture) -> None:
    info = parse_text(mevzuat_fixture("text_kanun_6502.html").decode())

    assert info.title == "TÜKETİCİNİN KORUNMASI HAKKINDA KANUN"
    assert info.declared_number == "6502"


def test_parse_text_collapses_a_title_printed_twice(mevzuat_fixture: Fixture) -> None:
    info = parse_text(mevzuat_fixture("text_yonetmelik_11180.html").decode())

    assert info.title == "BANKA KARTLARI VE KREDİ KARTLARI HAKKINDA YÖNETMELİK"
    assert info.declared_number is None


def test_parse_text_joins_a_title_split_over_lines(mevzuat_fixture: Fixture) -> None:
    info = parse_text(mevzuat_fixture("text_teblig_34343.html").decode())

    assert info.title == (
        "FİNANSAL TÜKETİCİLERDEN ALINACAK ÜCRETLERE İLİŞKİN USÛL VE ESASLAR HAKKINDA TEBLİĞ"
    )
    assert info.declared_number == "2020/7"


def test_parse_text_collects_amendment_notes(mevzuat_fixture: Fixture) -> None:
    info = parse_text(mevzuat_fixture("text_teblig_34343.html").decode())

    assert len(info.amendments) == 11
    assert info.latest_amendment == Amendment(
        date=date(2023, 12, 22), kind="rg", reference="RG-22/12/2023-32407"
    )


def test_parse_text_without_title_raises() -> None:
    with pytest.raises(ScrapeError, match="title"):
        parse_text("<html><body><p>MADDE 1 – (1) Metin.</p></body></html>")


# --- find_amendments -------------------------------------------------------------


def test_find_amendments_reads_regulation_style_notes() -> None:
    text = "c) (Değişik ibare:RG-9/8/2021-31563) Finansal Kurumlar Birliğini,"

    assert find_amendments(text) == (
        Amendment(date=date(2021, 8, 9), kind="rg", reference="RG-9/8/2021-31563"),
    )


def test_find_amendments_reads_law_and_decree_style_notes() -> None:
    text = (
        "(Değişik:24/3/2022-7392/2 md.) ... (Ek: 2/7/2018-KHK-703/97 md.) ... "
        "(Mülga: 1/2/2018 - 7074/8 md.)"
    )

    assert find_amendments(text) == (
        Amendment(date=date(2022, 3, 24), kind="law", reference="7392/2"),
        Amendment(date=date(2018, 7, 2), kind="law", reference="KHK-703/97"),
        Amendment(date=date(2018, 2, 1), kind="law", reference="7074/8"),
    )


def test_find_amendments_reads_rg_notes_written_without_the_rg_prefix() -> None:
    # Seen in the Banka Kartları ve Kredi Kartları Hakkında Yönetmelik (MevzuatNo 11180).
    text = (
        "( Değişik:RG -21/12/2008-27087) ... (Ek:17/12/2010-27788) ... (Değişik:RG-25/9/2020-31255)"
    )

    assert find_amendments(text) == (
        Amendment(date=date(2008, 12, 21), kind="rg", reference="RG-21/12/2008-27087"),
        Amendment(date=date(2010, 12, 17), kind="rg", reference="RG-17/12/2010-27788"),
        Amendment(date=date(2020, 9, 25), kind="rg", reference="RG-25/9/2020-31255"),
    )


def test_find_amendments_does_not_read_a_law_note_as_an_rg_note() -> None:
    assert [a.kind for a in find_amendments("(Ek:24/3/2022-7392/2 md.)")] == ["law"]


def test_find_amendments_skips_impossible_dates() -> None:
    assert find_amendments("(Değişik:RG-31/2/2020-31000)") == ()


def test_latest_amendment_is_none_when_text_was_never_amended() -> None:
    html = "<p>TÜKETİCİ HAKEM HEYETLERİ YÖNETMELİĞİ</p><p>BİRİNCİ BÖLÜM</p><p>MADDE 1- (1) x</p>"

    assert parse_text(html).latest_amendment is None
