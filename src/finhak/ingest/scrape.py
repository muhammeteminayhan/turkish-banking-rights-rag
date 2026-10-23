"""Read metadata out of mevzuat.gov.tr HTML.

Two kinds of page are involved:
- the document page (`/mevzuat?MevzuatNo=…`): Resmî Gazete date/number, the iframe that
  holds the consolidated text, and Word/PDF download links;
- the text iframe (`/anasayfa/MevzuatFihristDetayIframe?…`): title, declared number and the
  inline amendment notes such as "(Değişik:RG-9/8/2021-31563)".
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import Literal
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from finhak.textnorm import normalize_space

MEVZUAT_HOST = "www.mevzuat.gov.tr"
FILE_EXTENSIONS = (".doc", ".docx", ".pdf")
TEXT_IFRAME_MARKER = "MevzuatFihristDetayIframe"
TEXT_IFRAME_PATH = "/anasayfa/MevzuatFihristDetayIframe"
# How many leading non-title lines (e.g. an issuer line) may precede the title.
MAX_LINES_BEFORE_TITLE = 5
HEADER_SCAN_CHARS = 3000

_RG_INFO = re.compile(
    r"Resm[îi]\s+Gazete\s+Tarihi\s*:\s*(\d{2})\.(\d{2})\.(\d{4})\s*"
    r"Resm[îi]\s+Gazete\s+Sayısı\s*:\s*(\d+)"
)
_LAW_NUMBER = re.compile(r"Kanun\s+Numarası\s*:\s*(\d+)")
_TEBLIG_NUMBER = re.compile(r"\(\s*SAYI\s*:\s*([\d/]+)\s*\)")
_TITLE_STOP = re.compile(
    r"^(?:(?:BİRİNCİ|İKİNCİ|ÜÇÜNCÜ)\s+)?(?:KISIM|BÖLÜM)\b"
    r"|^(?:EK\s+|GEÇİCİ\s+)?MADDE\s+\d+"
    r"|^\(\s*SAYI\s*:"
)
# "RG-9/8/2021-31563", "RG -21/12/2008-27087" and "17/12/2010-27788" (no prefix). RG issue numbers
# have five digits; amending laws have four and are followed by "/article md." instead.
_RG_AMENDMENT = re.compile(
    r"(?:RG\s*-\s*|(?<![\d/]))(\d{1,2})/(\d{1,2})/(\d{4})\s*-\s*(\d{5})(?![\d/])"
)
_LAW_AMENDMENT = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})\s*-\s*((?:KHK-)?\d{3,4})/(\d+)\s*md")


class ScrapeError(ValueError):
    """The HTML does not have the structure mevzuat.gov.tr normally serves."""


@dataclass(frozen=True)
class PageInfo:
    rg_date: date
    rg_number: str
    text_url: str
    file_urls: tuple[str, ...]


@dataclass(frozen=True)
class Amendment:
    date: date
    kind: Literal["rg", "law"]
    reference: str


@dataclass(frozen=True)
class TextInfo:
    title: str
    declared_number: str | None
    amendments: tuple[Amendment, ...]

    @property
    def latest_amendment(self) -> Amendment | None:
        return max(self.amendments, key=lambda a: a.date, default=None)


def decode_html(content: bytes, origin: str) -> str:
    """mevzuat.gov.tr serves UTF-8; anything else means we did not get the page we expect."""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ScrapeError(f"{origin}: not valid UTF-8 HTML") from exc


def parse_page(html: str, page_url: str) -> PageInfo:
    soup = BeautifulSoup(html, "html.parser")

    rg = _RG_INFO.search(normalize_space(soup.get_text(" ")))
    if rg is None:
        raise ScrapeError(f"{page_url}: Resmî Gazete date/number not found")
    day, month, year, number = rg.groups()
    rg_date = _safe_date(year, month, day)
    if rg_date is None:
        raise ScrapeError(f"{page_url}: impossible Resmî Gazete date {day}.{month}.{year}")

    return PageInfo(
        rg_date=rg_date,
        rg_number=number,
        text_url=_text_url(soup, page_url),
        file_urls=_file_links(soup, page_url),
    )


def _text_url(soup: BeautifulSoup, page_url: str) -> str:
    iframe = soup.find("iframe", id="mevzuatDetayIframe") or soup.find(
        "iframe", src=re.compile(TEXT_IFRAME_MARKER)
    )
    src = iframe.get("src") if isinstance(iframe, Tag) else None
    if not src:
        raise ScrapeError(f"{page_url}: text iframe not found")
    url = urljoin(page_url, str(src))
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname != MEVZUAT_HOST
        or parts.path.lower() != TEXT_IFRAME_PATH.lower()
    ):
        raise ScrapeError(f"{page_url}: text iframe points outside mevzuat.gov.tr: {url}")
    return url


def _file_links(soup: BeautifulSoup, page_url: str) -> tuple[str, ...]:
    """Official Word/PDF links, at most one per extension (each is stored as source.{ext})."""
    by_extension: dict[str, str] = {}
    for anchor in soup.find_all("a", href=True):
        if not isinstance(anchor, Tag):
            continue
        url = urljoin(page_url, str(anchor["href"]))
        parts = urlsplit(url)
        path = parts.path.lower()
        extension = next((ext for ext in FILE_EXTENSIONS if path.endswith(ext)), None)
        is_official_file = (
            parts.scheme == "https"
            and parts.hostname == MEVZUAT_HOST
            and "/mevzuatmetin/" in path
            and extension is not None
        )
        if not is_official_file or extension is None:
            continue
        known = by_extension.setdefault(extension, url)
        if known != url:
            raise ScrapeError(f"{page_url}: two different {extension[1:]} files: {known}, {url}")
    return tuple(by_extension.values())


def parse_text(html: str) -> TextInfo:
    soup = BeautifulSoup(html, "html.parser")
    lines = [normalize_space(line) for line in soup.get_text("\n").splitlines()]
    lines = [line for line in lines if line]

    title = _title_from_lines(lines)
    if not title:
        raise ScrapeError("document title not found at the top of the text")

    flat = normalize_space(" ".join(lines))
    header = flat[:HEADER_SCAN_CHARS]
    number = _LAW_NUMBER.search(header) or _TEBLIG_NUMBER.search(header)
    return TextInfo(
        title=title,
        declared_number=number.group(1) if number else None,
        amendments=find_amendments(flat),
    )


def _title_from_lines(lines: list[str]) -> str:
    """Join the leading all-caps lines; mevzuat.gov.tr sometimes prints the title twice."""
    collected: list[str] = []
    for index, line in enumerate(lines):
        if _TITLE_STOP.search(line):
            break
        if _is_upper(line):
            collected.append(line)
        elif collected or index >= MAX_LINES_BEFORE_TITLE:
            break

    words = " ".join(collected).split()
    half = len(words) // 2
    if words and len(words) % 2 == 0 and words[:half] == words[half:]:
        words = words[:half]
    return " ".join(words)


def _is_upper(line: str) -> bool:
    letters = [char for char in line if char.isalpha()]
    return bool(letters) and all(char.isupper() for char in letters)


def find_amendments(text: str) -> tuple[Amendment, ...]:
    """Amendment notes in order of appearance; notes with impossible dates are skipped."""
    found: list[tuple[int, Amendment]] = []
    for match in _RG_AMENDMENT.finditer(text):
        day, month, year, rg_number = match.groups()
        when = _safe_date(year, month, day)
        if when:
            reference = f"RG-{int(day)}/{int(month)}/{year}-{rg_number}"
            found.append((match.start(), Amendment(when, "rg", reference)))
    for match in _LAW_AMENDMENT.finditer(text):
        day, month, year, act, article = match.groups()
        when = _safe_date(year, month, day)
        if when:
            found.append((match.start(), Amendment(when, "law", f"{act}/{article}")))
    return tuple(amendment for _, amendment in sorted(found, key=lambda item: item[0]))


def _safe_date(year: str, month: str, day: str) -> date | None:
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None
