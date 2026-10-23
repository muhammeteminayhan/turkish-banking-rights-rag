import hashlib
import json
from pathlib import Path

import httpx
import pytest
from mevzuat_stub import (
    DOC_PATH,
    PDF_BYTES,
    PDF_PATH,
    PDF_URL,
    SPEC_6502,
    TEXT_PATH,
    WORD_HTML,
    MevzuatServer,
    make_client,
)

from finhak.ingest.fetch import (
    FETCH_LOG_NAME,
    CorruptFetchLog,
    FetchOutcome,
    detect_file_format,
    fetch_source,
    read_fetch_log,
)
from finhak.ingest.http import FetchError
from finhak.ingest.scrape import ScrapeError

pytestmark = pytest.mark.unit


def _fetch(
    tmp_path: Path, refresh: bool = False, **overrides: httpx.Response
) -> tuple[FetchOutcome, MevzuatServer]:
    server = MevzuatServer(overrides=dict(overrides))
    return fetch_source(SPEC_6502, make_client(server), tmp_path, refresh=refresh), server


def _log(tmp_path: Path) -> dict[str, dict[str, dict[str, object]]]:
    return json.loads((tmp_path / "6502" / FETCH_LOG_NAME).read_text(encoding="utf-8"))


# --- happy path and cache ------------------------------------------------------------


def test_fetch_downloads_page_text_and_every_linked_file(tmp_path: Path) -> None:
    outcome, _ = _fetch(tmp_path)

    doc_dir = tmp_path / "6502"
    assert sorted(p.name for p in doc_dir.iterdir()) == sorted(
        [FETCH_LOG_NAME, "page.html", "text.html", "source.doc", "source.pdf"]
    )
    assert (doc_dir / "source.pdf").read_bytes() == PDF_BYTES
    assert outcome.downloaded == ("page.html", "text.html", "source.doc", "source.pdf")
    assert outcome.cached == ()
    assert outcome.rejected == ()
    assert outcome.failed == ()


def test_fetch_log_records_url_time_size_and_checksum(tmp_path: Path) -> None:
    _fetch(tmp_path)

    assert _log(tmp_path)["files"]["source.pdf"] == {
        "url": PDF_URL,
        "final_url": None,
        "fetched_at": "2026-10-23T13:00:00Z",
        "content_type": None,
        "bytes": len(PDF_BYTES),
        "sha256": hashlib.sha256(PDF_BYTES).hexdigest(),
    }
    assert _log(tmp_path)["files"]["page.html"]["url"] == SPEC_6502.page_url


def test_second_run_is_served_from_cache_with_zero_requests(tmp_path: Path) -> None:
    _fetch(tmp_path)

    outcome, server = _fetch(tmp_path)

    assert server.paths == []
    assert outcome.downloaded == ()
    assert outcome.cached == ("page.html", "text.html", "source.doc", "source.pdf")


def test_refresh_downloads_everything_again(tmp_path: Path) -> None:
    _fetch(tmp_path)

    outcome, server = _fetch(tmp_path, refresh=True)

    assert outcome.downloaded == ("page.html", "text.html", "source.doc", "source.pdf")
    assert server.paths == ["/robots.txt", "/mevzuat", TEXT_PATH, DOC_PATH, PDF_PATH]


def test_cached_file_changed_on_disk_is_downloaded_again(tmp_path: Path) -> None:
    _fetch(tmp_path)
    (tmp_path / "6502" / "source.pdf").write_bytes(b"%PDF-1.7 edited by hand")

    outcome, server = _fetch(tmp_path)

    assert outcome.downloaded == ("source.pdf",)
    assert PDF_PATH in server.paths
    assert (tmp_path / "6502" / "source.pdf").read_bytes() == PDF_BYTES


def test_cached_page_for_a_different_url_is_not_reused(tmp_path: Path) -> None:
    _fetch(tmp_path)
    moved = SPEC_6502.model_copy(update={"mevzuat_no": 6503})

    server = MevzuatServer()
    outcome = fetch_source(moved, make_client(server), tmp_path)

    assert outcome.downloaded[0] == "page.html"
    assert "/mevzuat" in server.paths


def test_redirected_file_is_cached_under_the_url_that_was_requested(tmp_path: Path) -> None:
    moved = {
        PDF_PATH: httpx.Response(302, headers={"location": "/MevzuatMetin/moved.pdf"}),
        "/MevzuatMetin/moved.pdf": httpx.Response(200, content=PDF_BYTES),
    }
    _fetch(tmp_path, **moved)

    outcome, server = _fetch(tmp_path)

    record = read_fetch_log(tmp_path / "6502").files["source.pdf"]
    assert record.url == PDF_URL
    assert record.final_url == "https://www.mevzuat.gov.tr/MevzuatMetin/moved.pdf"
    assert server.paths == []
    assert "source.pdf" in outcome.cached


def test_no_temporary_files_are_left_behind(tmp_path: Path) -> None:
    _fetch(tmp_path)

    assert not list((tmp_path / "6502").glob("*.tmp"))


# --- required files ------------------------------------------------------------------


def test_page_that_is_not_a_document_page_is_not_cached(tmp_path: Path) -> None:
    error_page = httpx.Response(200, content=b"<html><body>Sistem bakimda</body></html>")

    with pytest.raises(ScrapeError):
        _fetch(tmp_path, **{"/mevzuat": error_page})

    assert not (tmp_path / "6502" / "page.html").exists()


def test_text_without_a_title_is_not_cached(tmp_path: Path) -> None:
    error_page = httpx.Response(200, content=b"<html><body>Hata olustu</body></html>")

    with pytest.raises(ScrapeError):
        _fetch(tmp_path, **{TEXT_PATH: error_page})

    assert not (tmp_path / "6502" / "text.html").exists()


def test_missing_text_iframe_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(FetchError, match="404"):
        _fetch(tmp_path, **{TEXT_PATH: httpx.Response(404)})


# --- optional files ------------------------------------------------------------------


def _bad_pdf() -> httpx.Response:
    return httpx.Response(200, content=b"<html>Hata</html>")


def test_linked_file_with_wrong_bytes_is_rejected_and_not_saved(tmp_path: Path) -> None:
    outcome, _ = _fetch(tmp_path, **{PDF_PATH: _bad_pdf()})

    assert outcome.rejected == ("source.pdf",)
    assert outcome.downloaded == ("page.html", "text.html", "source.doc")
    assert not (tmp_path / "6502" / "source.pdf").exists()


def test_rejection_is_recorded_with_url_and_reason(tmp_path: Path) -> None:
    _fetch(tmp_path, **{PDF_PATH: _bad_pdf()})

    log = _log(tmp_path)

    assert log["rejected"]["source.pdf"] == {
        "url": PDF_URL,
        "fetched_at": "2026-10-23T13:00:00Z",
        "reason": "source.pdf: content is not a pdf file",
    }
    assert "source.pdf" not in log["files"]


def test_rejected_file_is_not_downloaded_again_without_refresh(tmp_path: Path) -> None:
    _fetch(tmp_path, **{PDF_PATH: _bad_pdf()})

    outcome, server = _fetch(tmp_path)

    assert server.paths == []
    assert outcome.rejected == ("source.pdf",)


def test_refresh_retries_a_rejected_file(tmp_path: Path) -> None:
    _fetch(tmp_path, **{PDF_PATH: _bad_pdf()})

    outcome, _ = _fetch(tmp_path, refresh=True)

    assert outcome.rejected == ()
    assert (tmp_path / "6502" / "source.pdf").read_bytes() == PDF_BYTES
    assert _log(tmp_path)["rejected"] == {}


def test_refresh_keeps_the_previous_good_copy_when_the_new_one_is_bad(tmp_path: Path) -> None:
    _fetch(tmp_path)

    outcome, _ = _fetch(tmp_path, refresh=True, **{PDF_PATH: _bad_pdf()})

    assert (tmp_path / "6502" / "source.pdf").read_bytes() == PDF_BYTES
    assert "source.pdf" in _log(tmp_path)["files"]
    assert outcome.kept_previous == ("source.pdf",)


def test_optional_file_network_failure_is_reported_and_others_continue(
    tmp_path: Path,
) -> None:
    outcome, server = _fetch(tmp_path, **{DOC_PATH: httpx.Response(404)})

    assert len(outcome.failed) == 1
    assert "source.doc" in outcome.failed[0]
    assert "404" in outcome.failed[0]
    assert PDF_PATH in server.paths
    assert (tmp_path / "6502" / "source.pdf").exists()


def test_word_html_saved_as_doc_is_accepted(tmp_path: Path) -> None:
    # mevzuat.gov.tr serves some .doc files as Word "web page" HTML in UTF-16LE with a BOM.
    outcome, _ = _fetch(tmp_path, **{DOC_PATH: httpx.Response(200, content=WORD_HTML)})

    assert outcome.rejected == ()
    assert (tmp_path / "6502" / "source.doc").read_bytes() == WORD_HTML


@pytest.mark.parametrize(
    "content",
    [b"Service Unavailable", b"<html><body>Hata</body></html>", "\ufeff<html>".encode("utf-16-le")],
)
def test_doc_that_is_neither_ole2_nor_word_html_is_rejected(tmp_path: Path, content: bytes) -> None:
    outcome, _ = _fetch(tmp_path, **{DOC_PATH: httpx.Response(200, content=content)})

    assert outcome.rejected == ("source.doc",)
    assert (tmp_path / "6502" / "source.pdf").exists()


# --- detect_file_format and the log ------------------------------------------------


@pytest.mark.parametrize(
    ("name", "content", "expected"),
    [
        ("source.pdf", b"%PDF-1.4 ...", "pdf"),
        ("source.docx", b"PK\x03\x04...", "docx"),
        ("source.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1...", "doc"),
        ("source.doc", WORD_HTML, "doc_html"),
        (
            "source.doc",
            b'\xef\xbb\xbf<html><head><meta name="Generator" content="Microsoft Word 14">',
            "doc_html",
        ),
    ],
)
def test_detect_file_format(name: str, content: bytes, expected: str) -> None:
    assert detect_file_format(name, content) == expected


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("source.pdf", b"<html>error</html>"),
        ("source.doc", b"<html><head><title>Hata</title></head></html>"),
        ("source.exe", b"MZ..."),
    ],
)
def test_detect_file_format_rejects_mismatches(name: str, content: bytes) -> None:
    with pytest.raises(FetchError):
        detect_file_format(name, content)


@pytest.mark.parametrize("content", ["{not json", "[]", '{"files": {"page.html": {"url": 1}}}'])
def test_corrupt_fetch_log_raises_a_typed_error(tmp_path: Path, content: str) -> None:
    (tmp_path / FETCH_LOG_NAME).write_text(content, encoding="utf-8")

    with pytest.raises(CorruptFetchLog):
        read_fetch_log(tmp_path)


def test_missing_fetch_log_reads_as_empty(tmp_path: Path) -> None:
    log = read_fetch_log(tmp_path)

    assert log.files == {}
    assert log.rejected == {}
