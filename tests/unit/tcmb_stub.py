"""A fake www.tcmb.gov.tr: the "Bankacılık ile İlgili Mevzuat" listing and one talimat PDF."""

from datetime import date
from pathlib import Path

import httpx

from finhak.ingest.sources import TcmbSource

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "tcmb"
LISTING_URL = (
    "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu"
    "/Banka+Hakkinda/Mevzuat/Bankacilik/"
)
LINK_TEXT = (
    "Finansal Tüketicilerden Alınacak Ücretlere İlişkin Usûl ve Esaslar Hakkında Tebliğe "
    "(Sayı: 2020/7) İlişkin Uygulama Talimatı"
)
TALIMAT_PREFIX = "/wps/wcm/connect/9fcd654e-65a7-4c42-8292-06ec3846e751/"
PDF_BYTES = b"%PDF-1.7\n%talimat\n"

SPEC_TALIMAT = TcmbSource(
    id="tcmb-ucret-talimat",
    label="Ücret Tebliği Uygulama Talimatı (TCMB)",
    doc_type="talimat",
    origin="tcmb",
    listing_url=LISTING_URL,
    link_text=LINK_TEXT,
    number=None,
    issuer="TCMB",
    expected_version_date=date(2026, 1, 13),
)


def listing_html() -> bytes:
    return (FIXTURES / "listing_bankacilik.html").read_bytes()


class TcmbServer:
    def __init__(self, overrides: dict[str, httpx.Response] | None = None) -> None:
        self.overrides = overrides or {}
        self.paths: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.paths.append(path)
        for prefix, response in self.overrides.items():
            if path.startswith(prefix):
                return response
        if path == "/robots.txt":
            return httpx.Response(404)
        if path.startswith("/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Banka+Hakkinda/Mevzuat/"):
            return httpx.Response(200, content=listing_html())
        if path.startswith(TALIMAT_PREFIX):
            return httpx.Response(200, content=PDF_BYTES)
        return httpx.Response(404)
