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
from urllib.parse import unquote, unquote_plus, urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from finhak.ingest.scrape import ScrapeError
from finhak.ingest.sources import TCMB_HOST, TcmbSource
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
# A "13 Ocak 2026" date that ends the file name (before the extension).
_TRAILING_DATE = re.compile(r"(?<!\d)(\d{1,2})\s+([^\W\d_]+)\s+(\d{4})\s*$")


class NewVersionPublished(ScrapeError):
    """The listing links a version other than the one recorded in sources.yaml."""


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
    path = PurePosixPath(unquote(parts.path))
    try:
        port = parts.port
    except ValueError:
        port = -1
    if (
        parts.scheme != "https"
        or parts.hostname != TCMB_HOST
        or port not in (None, 443)
        or parts.username is not None
        or not parts.path.startswith(CONTENT_PREFIX)
        or ".." in path.parts
        or path.suffix.lower() != ".pdf"
    ):
        raise ScrapeError(f"{url}: not a PDF under https://{TCMB_HOST}{CONTENT_PREFIX}")


def version_date_from_url(url: str) -> date | None:
    """The "13 Ocak 2026"-style date that ends the file name, or None."""
    stem = PurePosixPath(unquote_plus(PurePosixPath(urlsplit(url).path).name)).stem
    match = _TRAILING_DATE.search(stem)
    if match is None:
        return None
    day, month_name, year = match.groups()
    month = TURKISH_MONTHS.get(tr_casefold(month_name))
    if month is None:
        return None
    try:
        return date(int(year), month, int(day))
    except ValueError:
        return None


def check_version(spec: TcmbSource, link: ListingLink) -> date:
    """The version date of the linked file; raises unless it is the one in sources.yaml."""
    version = version_date_from_url(link.url)
    if version != spec.expected_version_date:
        raise NewVersionPublished(
            f"{spec.id}: the site links version {version} but sources.yaml expects "
            f"{spec.expected_version_date}; check the new text, then update "
            f"expected_version_date ({link.url})"
        )
    return version
