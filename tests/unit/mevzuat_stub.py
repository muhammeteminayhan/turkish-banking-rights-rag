"""A fake mevzuat.gov.tr for fetcher and CLI tests: serves the 6502 fixtures, counts requests."""

from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from finhak.ingest.http import PoliteClient, RateLimiter
from finhak.ingest.sources import SourceSpec

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "mevzuat"
FIXED_NOW = datetime(2026, 10, 23, 13, 0, tzinfo=UTC)

DOC_BYTES = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 32
PDF_BYTES = b"%PDF-1.7\n%fake\n"
WORD_HTML = (
    '\ufeff<html>\r\n<head>\r\n<meta name=Generator content="Microsoft Word 15 (filtered)">'
).encode("utf-16-le")

PAGE_PATH = "/mevzuat"
TEXT_PATH = "/anasayfa/MevzuatFihristDetayIframe"
DOC_PATH = "/MevzuatMetin/1.5.6502.doc"
PDF_PATH = "/MevzuatMetin/1.5.6502.pdf"
PDF_URL = f"https://www.mevzuat.gov.tr{PDF_PATH}"

SPEC_6502 = SourceSpec(
    id="6502",
    label="6502 sayılı Kanun",
    expected_title="Tüketicinin Korunması Hakkında Kanun",
    doc_type="kanun",
    mevzuat_no=6502,
    mevzuat_tur=1,
    number="6502",
    issuer="TBMM",
    expected_rg_date=date(2013, 11, 28),
    expected_rg_number="28835",
)

SOURCES_YAML_6502 = """\
sources:
  - id: "6502"
    label: 6502 sayılı Kanun
    expected_title: Tüketicinin Korunması Hakkında Kanun
    doc_type: kanun
    mevzuat_no: 6502
    mevzuat_tur: 1
    number: "6502"
    issuer: TBMM
    expected_rg_date: "2013-11-28"
    expected_rg_number: "28835"
"""


class MevzuatServer:
    def __init__(self, overrides: dict[str, httpx.Response] | None = None) -> None:
        self.overrides = overrides or {}
        self.paths: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.paths.append(path)
        if path in self.overrides:
            return self.overrides[path]
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: Googlebot\nNoindex:/x\n")
        if path == PAGE_PATH:
            return httpx.Response(200, content=(FIXTURES / "page_kanun_6502.html").read_bytes())
        if path == TEXT_PATH:
            return httpx.Response(200, content=(FIXTURES / "text_kanun_6502.html").read_bytes())
        if path == DOC_PATH:
            return httpx.Response(200, content=DOC_BYTES)
        if path == PDF_PATH:
            return httpx.Response(200, content=PDF_BYTES)
        return httpx.Response(404)


def make_client(server: MevzuatServer, interval: float = 1.0) -> PoliteClient:
    return PoliteClient(
        transport=httpx.MockTransport(server),
        limiter=RateLimiter(interval, clock=lambda: 0.0, sleep=lambda _: None),
        sleep=lambda _: None,
        now=lambda: FIXED_NOW,
    )
