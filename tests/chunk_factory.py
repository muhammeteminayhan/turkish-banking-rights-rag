"""Build Chunk objects for tests, giving only the fields a test cares about."""

from datetime import date
from typing import Any

from finhak.parsing.chunker import Chunk

LABELS = {
    "6502": ("6502 sayılı Tüketicinin Korunması Hakkında Kanun", "kanun"),
    "5464": ("5464 sayılı Banka Kartları ve Kredi Kartları Kanunu", "kanun"),
    "kart-yon": ("Banka Kartları ve Kredi Kartları Hakkında Yönetmelik", "yonetmelik"),
    "6493": ("6493 sayılı Ödeme Hizmetleri ve Elektronik Para Kuruluşları Kanunu", "kanun"),
    "tcmb-ucret-talimat": ("Ücret Tebliği Uygulama Talimatı (TCMB, 13.01.2026)", "talimat"),
}


def make_chunk(chunk_id: str, text: str, **fields: Any) -> Chunk:
    doc_id = chunk_id.split(":", 1)[0]
    label, doc_type = LABELS.get(doc_id, (f"{doc_id} belgesi", "yonetmelik"))
    defaults: dict[str, Any] = {
        "doc_id": doc_id,
        "doc_title": label.upper(),
        "doc_label": label,
        "doc_type": doc_type,
        "origin": "tcmb" if doc_type == "talimat" else "mevzuat",
        "unit": "fikra",
        "madde": "1",
        "madde_kind": "madde",
        "madde_title": None,
        "fikra": 1,
        "fikra_last": None,
        "fikra_inferred": False,
        "bents": (),
        "part": None,
        "kisim": None,
        "bolum": None,
        "notes": (),
        "amendments": (),
        "mulga": False,
        "pages": (),
        "source_url": f"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo={doc_id}",
        "rg_date": date(2013, 11, 28),
        "version_date": None,
        "collected_on": date(2026, 10, 23),
    }
    return Chunk.model_validate({**defaults, "id": chunk_id, "text": text, **fields})
