from datetime import date
from pathlib import Path

import pytest

from finhak.ingest.sources import SourcesError, load_sources

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


def _write_sources(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "sources.yaml"
    path.write_text("sources:\n" + body, encoding="utf-8")
    return path


def test_repo_sources_file_lists_fifteen_unique_documents() -> None:
    specs = load_sources(REPO_SOURCES)

    assert len(specs) == 15
    assert len({spec.id for spec in specs}) == 15


def test_page_url_uses_the_verified_mevzuat_pattern() -> None:
    spec = next(s for s in load_sources(REPO_SOURCES) if s.id == "tcmb-ucret-teblig")

    assert spec.page_url == (
        "https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=34343&MevzuatTur=9&MevzuatTertip=5"
    )


def test_expected_rg_date_is_parsed_as_a_date(tmp_path: Path) -> None:
    (spec,) = load_sources(_write_sources(tmp_path, VALID_ENTRY))

    assert spec.expected_rg_date == date(2013, 11, 28)
    assert spec.expected_rg_number == "28835"


def test_duplicate_ids_are_rejected(tmp_path: Path) -> None:
    path = _write_sources(tmp_path, VALID_ENTRY + VALID_ENTRY)

    with pytest.raises(SourcesError, match="duplicate"):
        load_sources(path)


def test_doc_type_must_match_mevzuat_tur(tmp_path: Path) -> None:
    path = _write_sources(tmp_path, VALID_ENTRY.replace("mevzuat_tur: 1", "mevzuat_tur: 7"))

    with pytest.raises(SourcesError, match="mevzuat_tur"):
        load_sources(path)


def test_unknown_fields_are_rejected_to_catch_typos(tmp_path: Path) -> None:
    path = _write_sources(tmp_path, VALID_ENTRY + "    expected_rg_nubmer: '1'\n")

    with pytest.raises(SourcesError, match="expected_rg_nubmer"):
        load_sources(path)


@pytest.mark.parametrize("reserved", ["con", "nul", "com1", "lpt9"])
def test_windows_reserved_names_are_rejected_as_ids(tmp_path: Path, reserved: str) -> None:
    path = _write_sources(tmp_path, VALID_ENTRY.replace('id: "6502"', f"id: {reserved}"))

    with pytest.raises(SourcesError, match="reserved"):
        load_sources(path)


def test_invalid_yaml_is_a_sources_error(tmp_path: Path) -> None:
    path = tmp_path / "sources.yaml"
    path.write_text("sources: [unclosed\n", encoding="utf-8")

    with pytest.raises(SourcesError):
        load_sources(path)


def test_missing_file_is_a_sources_error(tmp_path: Path) -> None:
    with pytest.raises(SourcesError, match="cannot read"):
        load_sources(tmp_path / "nope.yaml")


def test_missing_sources_key_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "sources.yaml"
    path.write_text("documents: []\n", encoding="utf-8")

    with pytest.raises(SourcesError, match="sources"):
        load_sources(path)
