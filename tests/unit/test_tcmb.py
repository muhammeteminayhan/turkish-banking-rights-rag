from datetime import date

import pytest
from finhak.ingest.tcmb import find_listing_link, version_date_from_url
from tcmb_stub import LINK_TEXT, LISTING_URL, TALIMAT_PREFIX, listing_html

from finhak.ingest.scrape import ScrapeError

pytestmark = pytest.mark.unit


def _anchor(href: str, text: str) -> str:
    return f'<a href="{href}">{text}</a>'


def test_the_talimat_link_is_found_on_the_real_listing_page() -> None:
    link = find_listing_link(listing_html().decode("utf-8"), LISTING_URL, LINK_TEXT)

    assert link.url.startswith(f"https://www.tcmb.gov.tr{TALIMAT_PREFIX}")
    assert link.url.split("?")[0].endswith("13+Ocak+2026.pdf")
    assert link.text == LINK_TEXT


def test_link_text_is_matched_ignoring_case_spacing_and_circumflex() -> None:
    html = _anchor("/wps/wcm/connect/abc/x.pdf", "  finansal TÜKETİCİLERDEN\n  usul ")

    link = find_listing_link(html, LISTING_URL, "Finansal Tüketicilerden Usûl")

    assert link.url == "https://www.tcmb.gov.tr/wps/wcm/connect/abc/x.pdf"


def test_missing_link_raises() -> None:
    with pytest.raises(ScrapeError, match="not found"):
        find_listing_link(_anchor("/x.pdf", "Başka bir belge"), LISTING_URL, LINK_TEXT)


def test_one_link_text_pointing_to_two_files_raises() -> None:
    html = _anchor("/wps/wcm/connect/a/1.pdf", LINK_TEXT) + _anchor(
        "/wps/wcm/connect/b/2.pdf", LINK_TEXT
    )

    with pytest.raises(ScrapeError, match="two"):
        find_listing_link(html, LISTING_URL, LINK_TEXT)


@pytest.mark.parametrize(
    "href",
    [
        "https://evil.example/wps/wcm/connect/a/1.pdf",
        "http://www.tcmb.gov.tr/wps/wcm/connect/a/1.pdf",
        "/wps/wcm/connect/a/1.zip",
        "/baska/yer/1.pdf",
    ],
)
def test_link_must_be_a_pdf_in_tcmb_content_store(href: str) -> None:
    with pytest.raises(ScrapeError, match="not a PDF under"):
        find_listing_link(_anchor(href, LINK_TEXT), LISTING_URL, LINK_TEXT)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://www.tcmb.gov.tr/wps/wcm/connect/9fcd/2023-39+say%C4%B1l%C4%B1+FT+"
            "Tebli%C4%9Fi+Uygulama+Talimat%C4%B1+-13+Ocak+2026.pdf?MOD=AJPERES&CACHEID=X",
            date(2026, 1, 13),
        ),
        (
            "https://www.tcmb.gov.tr/wps/wcm/connect/x/5+%C5%9Eubat+2025+Talimat.pdf",
            date(2025, 2, 5),
        ),
        ("https://www.tcmb.gov.tr/wps/wcm/connect/x/Talimat_Haziran+2026.pdf", None),
        ("https://www.tcmb.gov.tr/wps/wcm/connect/x/Talimat.pdf", None),
        ("https://www.tcmb.gov.tr/wps/wcm/connect/x/31+%C5%9Eubat+2025.pdf", None),
    ],
)
def test_version_date_is_read_from_the_file_name(url: str, expected: date | None) -> None:
    assert version_date_from_url(url) == expected
