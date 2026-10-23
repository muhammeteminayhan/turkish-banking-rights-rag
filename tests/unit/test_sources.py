from datetime import date
from pathlib import Path

import pytest

from finhak.ingest.sources import MevzuatSource, SourcesError, TcmbSource, load_sources

pytestmark = pytest.mark.unit

REPO_SOURCES = Path(__file__).resolve().parents[2] / "data" / "sources.yaml"

VALID_ENTRY = """
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

LISTING = "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Banka+Hakkinda/Mevzuat/Bankacilik/"
TCMB_ENTRY = f"""
  - id: tcmb-ucret-talimat
    label: Ücret Tebliği Uygulama Talimatı
    doc_type: talimat
    origin: tcmb
    listing_url: {LISTING}
    link_text: Uygulama Talimatı
    number: null
    issuer: TCMB
    expected_version_date: "2026-01-13"
"""


def _write_sources(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "sources.yaml"
    path.write_text("sources:\n" + body, encoding="utf-8")
    return path


def _load(tmp_path: Path, body: str) -> tuple[MevzuatSource | TcmbSource, ...]:
    return load_sources(_write_sources(tmp_path, body))


# --- the curated file -------------------------------------------------------------


def test_repo_sources_file_lists_the_sixteen_curated_documents() -> None:
    specs = load_sources(REPO_SOURCES)

    assert len(specs) == 16
    assert len({spec.id for spec in specs}) == 16
    assert [spec.id for spec in specs if isinstance(spec, TcmbSource)] == ["tcmb-ucret-talimat"]


def test_page_url_uses_the_verified_mevzuat_pattern() -> None:
    spec = next(s for s in load_sources(REPO_SOURCES) if s.id == "tcmb-ucret-teblig")

    assert spec.page_url == (
        "https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=34343&MevzuatTur=9&MevzuatTertip=5"
    )


# --- mevzuat sources --------------------------------------------------------------


def test_entry_without_origin_is_a_mevzuat_source(tmp_path: Path) -> None:
    (spec,) = _load(tmp_path, VALID_ENTRY)

    assert isinstance(spec, MevzuatSource)
    assert spec.expected_rg_date == date(2013, 11, 28)
    assert spec.expected_rg_number == "28835"


@pytest.mark.parametrize(
    "line",
    [
        "    mevzuat_no: 6502\n",
        "    mevzuat_tur: 1\n",
        '    expected_rg_date: "2013-11-28"\n',
        '    expected_rg_number: "28835"\n',
        "    expected_title: Tüketicinin Korunması Hakkında Kanun\n",
    ],
)
def test_mevzuat_source_must_state_every_field(tmp_path: Path, line: str) -> None:
    # Unverified values must be written as an explicit null, never left out by accident.
    field = line.split(":")[0].strip()

    with pytest.raises(SourcesError, match=field):
        _load(tmp_path, VALID_ENTRY.replace(line, ""))


def test_unverified_mevzuat_expectations_can_be_explicit_nulls(tmp_path: Path) -> None:
    body = VALID_ENTRY.replace('"2013-11-28"', "null").replace('"28835"', "null")

    (spec,) = _load(tmp_path, body)

    assert spec.expected_rg_date is None


def test_doc_type_must_match_mevzuat_tur(tmp_path: Path) -> None:
    with pytest.raises(SourcesError, match="mevzuat_tur"):
        _load(tmp_path, VALID_ENTRY.replace("mevzuat_tur: 1", "mevzuat_tur: 7"))


def test_talimat_cannot_come_from_mevzuat(tmp_path: Path) -> None:
    with pytest.raises(SourcesError, match="doc_type"):
        _load(tmp_path, VALID_ENTRY.replace("doc_type: kanun", "doc_type: talimat"))


def test_mevzuat_source_rejects_tcmb_fields(tmp_path: Path) -> None:
    with pytest.raises(SourcesError, match="link_text"):
        _load(tmp_path, VALID_ENTRY + "    link_text: x\n")


def test_unknown_fields_are_rejected_to_catch_typos(tmp_path: Path) -> None:
    with pytest.raises(SourcesError, match="expected_rg_nubmer"):
        _load(tmp_path, VALID_ENTRY + "    expected_rg_nubmer: '1'\n")


def test_unknown_origin_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(SourcesError, match="origin"):
        _load(tmp_path, VALID_ENTRY + "    origin: bddk\n")


# --- tcmb sources -----------------------------------------------------------------


def test_tcmb_source_uses_its_listing_page_and_version_date(tmp_path: Path) -> None:
    (spec,) = _load(tmp_path, TCMB_ENTRY)

    assert isinstance(spec, TcmbSource)
    assert spec.page_url == LISTING
    assert spec.expected_version_date == date(2026, 1, 13)


@pytest.mark.parametrize(
    ("line", "field"),
    [
        ('    expected_version_date: "2026-01-13"\n', "expected_version_date"),
        ("    link_text: Uygulama Talimatı\n", "link_text"),
        (f"    listing_url: {LISTING}\n", "listing_url"),
    ],
)
def test_tcmb_source_must_state_every_field(tmp_path: Path, line: str, field: str) -> None:
    with pytest.raises(SourcesError, match=field):
        _load(tmp_path, TCMB_ENTRY.replace(line, ""))


def test_tcmb_link_text_cannot_be_blank(tmp_path: Path) -> None:
    with pytest.raises(SourcesError, match="link_text"):
        _load(tmp_path, TCMB_ENTRY.replace("link_text: Uygulama Talimatı", 'link_text: "   "'))


@pytest.mark.parametrize("field", ["mevzuat_no: 1", 'expected_rg_number: "1"', "expected_title: x"])
def test_tcmb_source_rejects_mevzuat_fields(tmp_path: Path, field: str) -> None:
    with pytest.raises(SourcesError, match=field.split(":")[0]):
        _load(tmp_path, TCMB_ENTRY + f"    {field}\n")


def test_tcmb_source_must_be_a_talimat(tmp_path: Path) -> None:
    with pytest.raises(SourcesError, match="doc_type"):
        _load(tmp_path, TCMB_ENTRY.replace("doc_type: talimat", "doc_type: teblig"))


@pytest.mark.parametrize(
    "listing",
    [
        "https://evil.example/wps/x/",
        "http://www.tcmb.gov.tr/wps/x/",
        "https://www.tcmb.gov.tr:8443/wps/x/",
        "https://user@www.tcmb.gov.tr/wps/x/",
        "https://www.tcmb.gov.tr.evil.example/wps/x/",
    ],
)
def test_tcmb_listing_must_be_https_on_the_tcmb_host(tmp_path: Path, listing: str) -> None:
    with pytest.raises(SourcesError, match=r"www\.tcmb\.gov\.tr"):
        _load(tmp_path, TCMB_ENTRY.replace(LISTING, listing))


# --- file-level errors ------------------------------------------------------------


def test_duplicate_ids_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(SourcesError, match="duplicate"):
        _load(tmp_path, VALID_ENTRY + VALID_ENTRY)


@pytest.mark.parametrize("reserved", ["con", "nul", "com1", "lpt9"])
def test_windows_reserved_names_are_rejected_as_ids(tmp_path: Path, reserved: str) -> None:
    with pytest.raises(SourcesError, match="reserved"):
        _load(tmp_path, VALID_ENTRY.replace('id: "6502"', f"id: {reserved}"))


def test_invalid_yaml_is_a_sources_error(tmp_path: Path) -> None:
    path = tmp_path / "sources.yaml"
    path.write_text("sources: [unclosed\n", encoding="utf-8")

    with pytest.raises(SourcesError, match="invalid YAML"):
        load_sources(path)


def test_missing_file_is_a_sources_error(tmp_path: Path) -> None:
    with pytest.raises(SourcesError, match="cannot read"):
        load_sources(tmp_path / "nope.yaml")


def test_missing_sources_key_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "sources.yaml"
    path.write_text("documents: []\n", encoding="utf-8")

    with pytest.raises(SourcesError, match="sources"):
        load_sources(path)
