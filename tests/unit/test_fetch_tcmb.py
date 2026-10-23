"""Fetch + manifest for a document published on www.tcmb.gov.tr instead of mevzuat.gov.tr."""

from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest
from tcmb_stub import (
    LINK_TEXT,
    LISTING_URL,
    PDF_BYTES,
    SPEC_TALIMAT,
    TALIMAT_PREFIX,
    TcmbServer,
    listing_html,
)

from finhak.fsutil import atomic_write_bytes, atomic_write_text
from finhak.ingest.fetch import (
    FETCH_LOG_NAME,
    FetchOutcome,
    fetch_source,
    linked_files,
    read_fetch_log,
    sha256_hex,
)
from finhak.ingest.http import FetchError, PoliteClient, RateLimiter
from finhak.ingest.manifest import ManifestError, ManifestMismatch, build_entry
from finhak.ingest.scrape import ScrapeError
from finhak.ingest.tcmb import NewVersionPublished

pytestmark = pytest.mark.unit

FIXED_NOW = datetime(2026, 10, 23, 15, 0, tzinfo=UTC)
LISTING_PATH = "/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Banka+Hakkinda/Mevzuat/"
DOC_DIR = "tcmb-ucret-talimat"


def _fetch(
    tmp_path: Path, refresh: bool = False, **overrides: httpx.Response
) -> tuple[FetchOutcome, TcmbServer]:
    server = TcmbServer(overrides=dict(overrides))
    client = PoliteClient(
        transport=httpx.MockTransport(server),
        limiter=RateLimiter(1.0, clock=lambda: 0.0, sleep=lambda _: None),
        sleep=lambda _: None,
        now=lambda: FIXED_NOW,
    )
    return fetch_source(SPEC_TALIMAT, client, tmp_path, refresh=refresh), server


def _listing(replace: bytes, by: bytes) -> httpx.Response:
    html = listing_html()
    assert replace in html
    return httpx.Response(200, content=html.replace(replace, by))


# --- fetch -------------------------------------------------------------------------


def test_listing_page_and_pdf_are_downloaded(tmp_path: Path) -> None:
    outcome, server = _fetch(tmp_path)

    assert outcome.downloaded == ("page.html", "source.pdf")
    assert (tmp_path / DOC_DIR / "source.pdf").read_bytes() == PDF_BYTES
    assert server.paths[0] == "/robots.txt"
    assert any(path.startswith(TALIMAT_PREFIX) for path in server.paths)


def test_second_run_sends_no_requests(tmp_path: Path) -> None:
    _fetch(tmp_path)

    outcome, server = _fetch(tmp_path)

    assert server.paths == []
    assert outcome.cached == ("page.html", "source.pdf")


def test_pdf_with_wrong_bytes_is_fatal_because_it_is_the_only_text(tmp_path: Path) -> None:
    error_page = httpx.Response(200, content=b"<html>Sayfa bulunamadi</html>")

    with pytest.raises(FetchError, match="not a pdf file"):
        _fetch(tmp_path, **{TALIMAT_PREFIX: error_page})

    assert not (tmp_path / DOC_DIR / "source.pdf").exists()


def test_renamed_link_on_the_site_is_reported_and_not_cached(tmp_path: Path) -> None:
    renamed = _listing(b"(Say\xc4\xb1: 2020/7) \xc4\xb0li\xc5\x9fkin Uygulama", b"Yeni Uygulama")

    with pytest.raises(ScrapeError, match="not found"):
        _fetch(tmp_path, **{LISTING_PATH: renamed})

    assert not (tmp_path / DOC_DIR / "page.html").exists()


def test_new_version_on_the_site_stops_before_anything_is_overwritten(tmp_path: Path) -> None:
    _fetch(tmp_path)
    page_before = (tmp_path / DOC_DIR / "page.html").read_bytes()
    newer = _listing(b"-13+Ocak+2026.pdf", b"-12+Ocak+2027.pdf")

    with pytest.raises(NewVersionPublished, match="2027-01-12"):
        _fetch(tmp_path, refresh=True, **{LISTING_PATH: newer})

    assert (tmp_path / DOC_DIR / "page.html").read_bytes() == page_before
    assert (tmp_path / DOC_DIR / "source.pdf").read_bytes() == PDF_BYTES


def test_linked_files_lists_the_pdf_for_a_tcmb_source() -> None:
    assert linked_files(SPEC_TALIMAT, listing_html()) == ["source.pdf"]


# --- manifest ----------------------------------------------------------------------


def test_manifest_entry_has_version_date_and_no_rg_fields(tmp_path: Path) -> None:
    _fetch(tmp_path)

    entry = build_entry(SPEC_TALIMAT, tmp_path)

    assert entry.origin == "tcmb"
    assert entry.doc_type == "talimat"
    assert entry.title == LINK_TEXT
    assert entry.version_date == date(2026, 1, 13)
    assert entry.rg_date is None
    assert entry.rg_number is None
    assert entry.mevzuat_no is None
    assert entry.source_page_url == LISTING_URL
    assert [f.format for f in entry.files] == ["html_page", "pdf"]
    assert entry.files[1].url.startswith(f"https://www.tcmb.gov.tr{TALIMAT_PREFIX}")
    # Amendment notes are read from the text in M2; for a PDF-only source they are unknown here.
    assert entry.amendment_note_count is None
    assert entry.last_amendment is None


def test_manifest_detects_a_version_change_in_the_stored_listing(tmp_path: Path) -> None:
    _fetch(tmp_path)
    expecting_older = SPEC_TALIMAT.model_copy(update={"expected_version_date": date(2025, 1, 10)})

    with pytest.raises(ManifestMismatch, match="version_date"):
        build_entry(expecting_older, tmp_path)


def _replace_stored_page(tmp_path: Path, content: bytes) -> None:
    doc_dir = tmp_path / DOC_DIR
    atomic_write_bytes(doc_dir / "page.html", content)
    log = read_fetch_log(doc_dir)
    record = log.files["page.html"].model_copy(update={"sha256": sha256_hex(content)})
    updated = log.model_copy(update={"files": {**log.files, "page.html": record}})
    atomic_write_text(doc_dir / FETCH_LOG_NAME, updated.model_dump_json())


def test_manifest_refuses_a_pdf_the_listing_no_longer_links(tmp_path: Path) -> None:
    _fetch(tmp_path)
    moved = listing_html().replace(b"9fcd654e-65a7-4c42-8292-06ec3846e751", b"0000aaaa-moved")
    _replace_stored_page(tmp_path, moved)

    with pytest.raises(ManifestError, match="not the file the listing links"):
        build_entry(SPEC_TALIMAT, tmp_path)
