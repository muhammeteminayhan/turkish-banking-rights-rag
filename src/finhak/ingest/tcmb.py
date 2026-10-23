"""Find a document on a www.tcmb.gov.tr listing page and read its version date.

TCMB publishes some texts (e.g. the Uygulama Talimatı of Tebliğ 2020/7) only on its own
site, as PDFs whose URL contains the version date in the file name:
    /wps/wcm/connect/<uuid>/2023-39+sayılı+FT+Tebliği+Uygulama+Talimatı+-13+Ocak+2026.pdf?...
The URL changes with every version, so it is always read from the listing page by its link
text, and the date in the file name is checked against sources.yaml.
"""

import re
from dataclasses import dataclass
from datetime import date
from pathlib import PurePosixPath
from urllib.parse import unquote_plus, urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from finhak.ingest.scrape import ScrapeError
from finhak.ingest.sources import TCMB_HOST
from finhak.textnorm import normalize_space, tr_casefold

CONTENT_PREFIX = "/wps/wcm/connect/"
TURKISH_MONTHS = {
    "ocak": 1,
    "şubat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "eylül": 9,
    "ekim": 10,
    "kasım": 11,
    "aralık": 12,
}
_DAY_MONTH_YEAR = re.compile(r"(?<!\d)(\d{1,2})\s+([^\W\d_]+)\s+(\d{4})(?!\d)")


@dataclass(frozen=True)
class ListingLink:
    url: str
    text: str


def find_listing_link(html: str, listing_url: str, link_text: str) -> ListingLink:
    """The single PDF whose anchor text equals `link_text` (Turkish case-insensitive)."""
    soup = BeautifulSoup(html, "html.parser")
    wanted = tr_casefold(link_text)
    matches: dict[str, str] = {}
    for anchor in soup.find_all("a", href=True):
        if not isinstance(anchor, Tag):
            continue
        text = normalize_space(anchor.get_text(" "))
        if tr_casefold(text) != wanted:
            continue
        url = urljoin(listing_url, str(anchor["href"]))
        _check_pdf_link(url)
        matches.setdefault(url, text)

    if not matches:
        raise ScrapeError(f"{listing_url}: link {link_text!r} not found")
    if len(matches) > 1:
        raise ScrapeError(f"{listing_url}: {link_text!r} points to two different files")
    ((url, text),) = matches.items()
    return ListingLink(url=url, text=text)


def _check_pdf_link(url: str) -> None:
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname != TCMB_HOST
        or not parts.path.startswith(CONTENT_PREFIX)
        or not parts.path.lower().endswith(".pdf")
    ):
        raise ScrapeError(f"{url}: not a PDF under https://{TCMB_HOST}{CONTENT_PREFIX}")


def version_date_from_url(url: str) -> date | None:
    """The last valid "13 Ocak 2026"-style date in the file name, or None."""
    name = unquote_plus(PurePosixPath(urlsplit(url).path).name)
    found: date | None = None
    for day, month_name, year in _DAY_MONTH_YEAR.findall(name):
        month = TURKISH_MONTHS.get(tr_casefold(month_name))
        if month is None:
            continue
        try:
            found = date(int(year), month, int(day))
        except ValueError:
            continue
    return found
