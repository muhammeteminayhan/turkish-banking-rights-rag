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

from finhak.ingest.fetch import FetchOutcome, fetch_source, linked_files
from finhak.ingest.http import FetchError, PoliteClient, RateLimiter
from finhak.ingest.manifest import ManifestMismatch, build_entry
from finhak.ingest.scrape import ScrapeError

pytestmark = pytest.mark.unit

FIXED_NOW = datetime(2026, 10, 23, 15, 0, tzinfo=UTC)
LISTING_PATH = "/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Banka+Hakkinda/Mevzuat/"


def _fetch(tmp_path: Path, **overrides: httpx.Response) -> tuple[FetchOutcome, TcmbServer]:
    server = TcmbServer(overrides=dict(overrides))
    client = PoliteClient(
        transport=httpx.MockTransport(server),
        limiter=RateLimiter(1.0, clock=lambda: 0.0, sleep=lambda _: None),
        sleep=lambda _: None,
        now=lambda: FIXED_NOW,
    )
    return fetch_source(SPEC_TALIMAT, client, tmp_path), server


# --- fetch -------------------------------------------------------------------------


def test_listing_page_and_pdf_are_downloaded(tmp_path: Path) -> None:
    outcome, server = _fetch(tmp_path)

    assert outcome.downloaded == ("page.html", "source.pdf")
    assert (tmp_path / "tcmb-ucret-talimat" / "source.pdf").read_bytes() == PDF_BYTES
    assert server.paths[0] == "/robots.txt"
    assert any(path.startswith(TALIMAT_PREFIX) for path in server.paths)


def test_second_run_sends_no_requests(tmp_path: Path) -> None:
    _fetch(tmp_path)

    outcome, server = _fetch(tmp_path)

    assert server.paths == []
    assert outcome.cached == ("page.html", "source.pdf")


def test_pdf_with_wrong_bytes_is_fatal_because_it_is_the_only_text(tmp_path: Path) -> None:
    error_page = httpx.Response(200, content=b"<html>Sayfa bulunamadi</html>")

    with pytest.raises(FetchError, match="pdf"):
        _fetch(tmp_path, **{TALIMAT_PREFIX: error_page})

    assert not (tmp_path / "tcmb-ucret-talimat" / "source.pdf").exists()


def test_listing_without_the_link_is_not_cached(tmp_path: Path) -> None:
    other_page = httpx.Response(200, content="<html><a href='/x.pdf'>Başka</a></html>".encode())

    with pytest.raises(ScrapeError):
        _fetch(tmp_path, **{LISTING_PATH: other_page})

    assert not (tmp_path / "tcmb-ucret-talimat" / "page.html").exists()


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


def test_a_newer_version_on_the_site_fails_loudly(tmp_path: Path) -> None:
    _fetch(tmp_path)
    expecting_older = SPEC_TALIMAT.model_copy(update={"expected_version_date": date(2025, 1, 10)})

    with pytest.raises(ManifestMismatch, match="version_date"):
        build_entry(expecting_older, tmp_path)


def test_a_renamed_link_fails_loudly(tmp_path: Path) -> None:
    _fetch(tmp_path)
    other_title = SPEC_TALIMAT.model_copy(update={"expected_title": "Başka Talimat"})

    with pytest.raises(ManifestMismatch, match="title"):
        build_entry(other_title, tmp_path)
