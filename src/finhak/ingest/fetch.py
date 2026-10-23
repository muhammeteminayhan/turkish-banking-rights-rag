"""Download one source into data/raw/{id}/ and keep a fetch log next to the files.

Layout of data/raw/{id}/:
    page.html       document page (RG info, download links)
    text.html       consolidated text served in the page's iframe
    source.{ext}    each linked Word/PDF file (.doc, .docx, .pdf)
    _fetch.json     {"files":    {name: {url, fetched_at, content_type, bytes, sha256}},
                     "rejected": {name: {url, fetched_at, reason}}}

A file is served from the cache only when it exists, was downloaded from the same URL and
still has the logged SHA-256. The page and the text are validated before they are stored.
A rejected optional file is not requested again until --refresh.
"""

import hashlib
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from finhak.fsutil import atomic_write_bytes, atomic_write_text
from finhak.ingest.http import FetchError, FetchResult, PoliteClient
from finhak.ingest.scrape import decode_html, parse_page, parse_text
from finhak.ingest.sources import SourceSpec
from finhak.ingest.tcmb import find_listing_link

logger = logging.getLogger(__name__)

FETCH_LOG_NAME = "_fetch.json"
PAGE_NAME = "page.html"
TEXT_NAME = "text.html"
SourceFormat = Literal["doc", "doc_html", "docx", "pdf"]
FILE_MAGIC: dict[str, bytes] = {
    ".pdf": b"%PDF-",
    ".doc": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",  # OLE2 compound document
    ".docx": b"PK\x03\x04",  # zip container
}
_FORMAT_FOR_SUFFIX: dict[str, SourceFormat] = {".pdf": "pdf", ".doc": "doc", ".docx": "docx"}
UTF16_LE_BOM = b"\xff\xfe"
UTF8_BOM = b"\xef\xbb\xbf"
HTML_SNIFF_BYTES = 8192
_WORD_GENERATOR = re.compile(
    r"<meta[^>]*name=[\"']?generator[\"']?[^>]*content=[\"']?microsoft word", re.IGNORECASE
)
_RECORD_CONFIG = ConfigDict(extra="forbid")


class CorruptFetchLog(RuntimeError):
    """A _fetch.json file exists but cannot be read."""


class FileRecord(BaseModel):
    model_config = _RECORD_CONFIG

    url: str
    fetched_at: datetime
    content_type: str | None
    bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Rejection(BaseModel):
    model_config = _RECORD_CONFIG

    url: str
    fetched_at: datetime
    reason: str


class FetchLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files: dict[str, FileRecord] = Field(default_factory=dict)
    rejected: dict[str, Rejection] = Field(default_factory=dict)


@dataclass(frozen=True)
class FetchOutcome:
    source_id: str
    downloaded: tuple[str, ...]
    cached: tuple[str, ...]
    rejected: tuple[str, ...] = ()
    kept_previous: tuple[str, ...] = ()
    failed: tuple[str, ...] = ()


def source_file_name(url: str) -> str:
    suffix = PurePosixPath(urlsplit(url).path).suffix.lower()
    if suffix not in FILE_MAGIC:
        raise FetchError(f"{url}: unsupported file type {suffix!r}")
    return f"source{suffix}"


def detect_file_format(name: str, content: bytes) -> SourceFormat:
    """Check the bytes really are what the extension claims; returns the manifest format.

    Some mevzuat.gov.tr ".doc" files are Word "web page" exports (HTML, often UTF-16LE),
    not OLE2 documents. They are accepted only when they carry Word's Generator meta tag,
    so that an ordinary HTML error page is still rejected, and labelled "doc_html".
    """
    suffix = PurePosixPath(name).suffix
    magic = FILE_MAGIC.get(suffix)
    if magic is None:
        raise FetchError(f"{name}: unsupported file type {suffix!r}")
    if content.startswith(magic):
        return _FORMAT_FOR_SUFFIX[suffix]
    if suffix == ".doc" and _is_word_html(content):
        return "doc_html"
    raise FetchError(f"{name}: content is not a {suffix.removeprefix('.')} file")


def _is_word_html(content: bytes) -> bool:
    head = content[:HTML_SNIFF_BYTES]
    if head.startswith(UTF16_LE_BOM):
        text = head[len(UTF16_LE_BOM) :].decode("utf-16-le", errors="ignore")
    else:
        text = head.removeprefix(UTF8_BOM).decode("utf-8", errors="ignore")
    is_html = text.lstrip().lower().startswith(("<html", "<!doctype html"))
    return is_html and _WORD_GENERATOR.search(text) is not None


def fetch_source(
    spec: SourceSpec, client: PoliteClient, raw_dir: Path, refresh: bool = False
) -> FetchOutcome:
    store = _DocumentStore(raw_dir / spec.id, client, refresh)
    if spec.origin == "tcmb":
        _fetch_tcmb(spec, store)
    else:
        _fetch_mevzuat(spec, store)
    return FetchOutcome(
        source_id=spec.id,
        downloaded=tuple(store.downloaded),
        cached=tuple(store.cached),
        rejected=tuple(store.rejected),
        kept_previous=tuple(store.kept_previous),
        failed=tuple(store.failed),
    )


def _fetch_mevzuat(spec: SourceSpec, store: "_DocumentStore") -> None:
    """Page and consolidated HTML text are required; linked Word/PDF files are optional."""
    page = store.get_required(PAGE_NAME, spec.page_url, _validate_page(spec.page_url))
    info = parse_page(decode_html(page, spec.page_url), spec.page_url)
    store.get_required(TEXT_NAME, info.text_url, _validate_text(info.text_url))
    for url in info.file_urls:
        store.get_optional(source_file_name(url), url)


def _fetch_tcmb(spec: SourceSpec, store: "_DocumentStore") -> None:
    """Listing page and the PDF are both required: the PDF is the only copy of the text."""
    link_text = _link_text(spec)
    listing = store.get_required(
        PAGE_NAME, spec.page_url, _validate_listing(spec.page_url, link_text)
    )
    link = find_listing_link(decode_html(listing, spec.page_url), spec.page_url, link_text)
    name = source_file_name(link.url)
    store.get_required(name, link.url, _validate_file(name))


def linked_files(spec: SourceSpec, page: bytes) -> list[str]:
    """The files a stored page leads to, in fetch order (used by --dry-run)."""
    html = decode_html(page, spec.page_url)
    if spec.origin == "tcmb":
        link = find_listing_link(html, spec.page_url, _link_text(spec))
        return [source_file_name(link.url)]
    info = parse_page(html, spec.page_url)
    return [TEXT_NAME, *(source_file_name(url) for url in info.file_urls)]


def _link_text(spec: SourceSpec) -> str:
    if spec.link_text is None:
        raise ValueError(f"{spec.id}: tcmb source without link_text")
    return spec.link_text


def _validate_listing(url: str, link_text: str) -> Callable[[bytes], None]:
    """Raises ScrapeError unless the listing still links the document."""

    def check(content: bytes) -> None:
        find_listing_link(decode_html(content, url), url, link_text)

    return check


def _validate_file(name: str) -> Callable[[bytes], None]:
    """Raises FetchError unless the bytes are what the file extension claims."""

    def check(content: bytes) -> None:
        detect_file_format(name, content)

    return check


def _validate_page(url: str) -> Callable[[bytes], None]:
    """Raises ScrapeError unless the bytes are a mevzuat.gov.tr document page."""

    def check(content: bytes) -> None:
        parse_page(decode_html(content, url), url)

    return check


def _validate_text(url: str) -> Callable[[bytes], None]:
    """Raises ScrapeError unless the bytes are a consolidated text with a title."""

    def check(content: bytes) -> None:
        parse_text(decode_html(content, url))

    return check


def read_fetch_log(doc_dir: Path) -> FetchLog:
    path = doc_dir / FETCH_LOG_NAME
    if not path.exists():
        return FetchLog()
    try:
        return FetchLog.model_validate_json(path.read_bytes())
    except ValidationError as exc:
        raise CorruptFetchLog(f"{path}: {exc}") from exc


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class _DocumentStore:
    """Cache-or-download for the files of one document, updating the fetch log as it goes.

    Required files (page, text) are validated before they are stored; any failure aborts the
    document. Optional Word/PDF files never abort it: wrong bytes are rejected (recorded with
    the reason), network failures are reported in `failed`, and a bad response on --refresh
    keeps the previous good copy.
    """

    def __init__(self, doc_dir: Path, client: PoliteClient, refresh: bool) -> None:
        self._dir = doc_dir
        self._client = client
        self._refresh = refresh
        self._log = read_fetch_log(doc_dir)
        self.downloaded: list[str] = []
        self.cached: list[str] = []
        self.rejected: list[str] = []
        self.kept_previous: list[str] = []
        self.failed: list[str] = []

    def get_required(self, name: str, url: str, validate: Callable[[bytes], None]) -> bytes:
        cached = self._from_cache(name, url)
        if cached is not None:
            return cached
        result = self._client.get(url)
        validate(result.content)
        self._save(name, result)
        return result.content

    def get_optional(self, name: str, url: str) -> None:
        if self._from_cache(name, url) is not None:
            return
        previous = self._log.rejected.get(name)
        if not self._refresh and previous is not None and previous.url == url:
            self.rejected.append(name)
            return
        try:
            result = self._client.get(url)
        except FetchError as exc:
            logger.error("%s: %s", name, exc)
            self.failed.append(f"{name}: {exc}")
            return
        try:
            detect_file_format(name, result.content)
        except FetchError as exc:
            self._reject(name, result, str(exc))
            return
        self._save(name, result)

    def _from_cache(self, name: str, url: str) -> bytes | None:
        record = self._log.files.get(name)
        path = self._dir / name
        if self._refresh or record is None or not path.exists():
            return None
        if record.url != url:
            logger.warning(
                "%s: source URL changed (%s -> %s), downloading again", path, record.url, url
            )
            return None
        content = path.read_bytes()
        if sha256_hex(content) != record.sha256:
            logger.warning("%s: changed on disk since download, downloading again", path)
            return None
        self.cached.append(name)
        return content

    def _save(self, name: str, result: FetchResult) -> None:
        path = self._dir / name
        atomic_write_bytes(path, result.content)
        record = FileRecord(
            url=result.url,
            fetched_at=result.fetched_at,
            content_type=result.content_type,
            bytes=len(result.content),
            sha256=sha256_hex(result.content),
        )
        rejected = {k: v for k, v in self._log.rejected.items() if k != name}
        self._write_log(FetchLog(files={**self._log.files, name: record}, rejected=rejected))
        self.downloaded.append(name)
        logger.info("downloaded %s (%d bytes) <- %s", path, len(result.content), result.url)

    def _reject(self, name: str, result: FetchResult, reason: str) -> None:
        path = self._dir / name
        if name in self._log.files and path.exists():
            logger.warning(
                "%s: refresh returned bad content (%s); keeping the previous copy", path, reason
            )
            self.kept_previous.append(name)
            return
        logger.warning("rejected %s from %s: %s", name, result.url, reason)
        path.unlink(missing_ok=True)
        rejection = Rejection(url=result.url, fetched_at=result.fetched_at, reason=reason)
        files = {k: v for k, v in self._log.files.items() if k != name}
        self._write_log(FetchLog(files=files, rejected={**self._log.rejected, name: rejection}))
        self.rejected.append(name)

    def _write_log(self, log: FetchLog) -> None:
        self._log = log
        atomic_write_text(self._dir / FETCH_LOG_NAME, log.model_dump_json(indent=2) + "\n")
