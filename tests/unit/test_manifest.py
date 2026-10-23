import hashlib
import json
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest

from finhak.ingest.fetch import FETCH_LOG_NAME
from finhak.ingest.manifest import (
    ManifestError,
    ManifestMismatch,
    build_entry,
    build_manifest,
    manifest_json_schema,
    read_manifest,
    verify_manifest,
    write_manifest,
)
from finhak.ingest.sources import SourceSpec

pytestmark = pytest.mark.unit

Fixture = Callable[[str], bytes]
PDF_BYTES = b"%PDF-1.7\n%fake\n"
DOC_BYTES = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 32
# The 6502 and 34343 fixture pages both link a .doc and a .pdf file.
LINKED_FILES = {"source.doc": DOC_BYTES, "source.pdf": PDF_BYTES}

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
SPEC_TEBLIG = SourceSpec(
    id="tcmb-ucret-teblig",
    label="Ücret Tebliği",
    expected_title=(
        "Finansal Tüketicilerden Alınacak Ücretlere İlişkin Usûl ve Esaslar Hakkında Tebliğ"
    ),
    doc_type="teblig",
    mevzuat_no=34343,
    mevzuat_tur=9,
    number="2020/7",
    issuer="TCMB",
    expected_rg_date=date(2020, 3, 7),
    expected_rg_number="31061",
)


def _make_raw_dir(
    raw_dir: Path, spec: SourceSpec, page: bytes, text: bytes, files: dict[str, bytes]
) -> Path:
    doc_dir = raw_dir / spec.id
    doc_dir.mkdir(parents=True)
    (doc_dir / FETCH_LOG_NAME).write_text(json.dumps({"files": {}}), encoding="utf-8")
    for name, content in {"page.html": page, "text.html": text, **files}.items():
        _replace_file(raw_dir, spec.id, name, content)
    return raw_dir


def _replace_file(raw_dir: Path, source_id: str, name: str, content: bytes) -> None:
    """Write a raw file and a matching fetch-log record, as the fetcher would."""
    doc_dir = raw_dir / source_id
    (doc_dir / name).write_bytes(content)
    log = json.loads((doc_dir / FETCH_LOG_NAME).read_text(encoding="utf-8"))
    log["files"][name] = {
        "url": f"https://www.mevzuat.gov.tr/{name}",
        "fetched_at": "2026-10-23T13:00:00Z",
        "content_type": "text/html",
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }
    (doc_dir / FETCH_LOG_NAME).write_text(json.dumps(log), encoding="utf-8")


@pytest.fixture
def raw_6502(tmp_path: Path, mevzuat_fixture: Fixture) -> Path:
    return _make_raw_dir(
        tmp_path / "raw",
        SPEC_6502,
        mevzuat_fixture("page_kanun_6502.html"),
        mevzuat_fixture("text_kanun_6502.html"),
        LINKED_FILES,
    )


def test_entry_combines_curated_and_scraped_fields(raw_6502: Path) -> None:
    entry = build_entry(SPEC_6502, raw_6502)

    assert entry.id == "6502"
    assert entry.title == "TÜKETİCİNİN KORUNMASI HAKKINDA KANUN"
    assert entry.doc_type == "kanun"
    assert entry.number == "6502"
    assert entry.issuer == "TBMM"
    assert entry.rg_date == date(2013, 11, 28)
    assert entry.rg_number == "28835"
    assert entry.source_page_url == SPEC_6502.page_url
    assert entry.status == "in_force"


def test_entry_lists_files_with_sha256_and_relative_paths(raw_6502: Path) -> None:
    entry = build_entry(SPEC_6502, raw_6502)

    by_format = {f.format: f for f in entry.files}
    assert set(by_format) == {"html_page", "html_text", "doc", "pdf"}
    assert by_format["pdf"].path == "6502/source.pdf"
    assert by_format["pdf"].sha256 == hashlib.sha256(PDF_BYTES).hexdigest()
    assert by_format["pdf"].bytes == len(PDF_BYTES)
    assert by_format["pdf"].fetched_at.isoformat() == "2026-10-23T13:00:00+00:00"


def test_word_html_doc_is_labelled_doc_html(raw_6502: Path) -> None:
    word_html = '<html><head><meta name=Generator content="Microsoft Word 15">'
    _replace_file(raw_6502, "6502", "source.doc", word_html.encode("utf-8"))

    entry = build_entry(SPEC_6502, raw_6502)

    assert {f.format for f in entry.files} == {"html_page", "html_text", "doc_html", "pdf"}


def test_rejected_linked_file_is_listed_separately(raw_6502: Path) -> None:
    doc_dir = raw_6502 / "6502"
    (doc_dir / "source.doc").unlink()
    log = json.loads((doc_dir / FETCH_LOG_NAME).read_text(encoding="utf-8"))
    del log["files"]["source.doc"]
    log["rejected"] = {
        "source.doc": {
            "url": "https://www.mevzuat.gov.tr/MevzuatMetin/1.5.6502.doc",
            "fetched_at": "2026-10-23T13:00:00Z",
            "reason": "source.doc: content is not a doc file",
        }
    }
    (doc_dir / FETCH_LOG_NAME).write_text(json.dumps(log), encoding="utf-8")

    entry = build_entry(SPEC_6502, raw_6502)

    assert {f.format for f in entry.files} == {"html_page", "html_text", "pdf"}
    assert [(r.name, r.url, r.reason) for r in entry.rejected_files] == [
        (
            "source.doc",
            "https://www.mevzuat.gov.tr/MevzuatMetin/1.5.6502.doc",
            "source.doc: content is not a doc file",
        )
    ]


def test_entry_without_rejections_has_an_empty_list(raw_6502: Path) -> None:
    assert build_entry(SPEC_6502, raw_6502).rejected_files == ()


def test_downloaded_file_with_unexpected_bytes_is_reported(raw_6502: Path) -> None:
    _replace_file(raw_6502, "6502", "source.pdf", b"<html>Hata</html>")

    with pytest.raises(ManifestError, match="not a pdf"):
        build_entry(SPEC_6502, raw_6502)


def test_file_changed_since_download_is_reported(raw_6502: Path) -> None:
    (raw_6502 / "6502" / "source.pdf").write_bytes(b"%PDF-1.7 edited by hand")

    with pytest.raises(ManifestError, match="changed since download"):
        build_entry(SPEC_6502, raw_6502)


def test_corrupt_fetch_log_is_reported_as_a_manifest_error(raw_6502: Path) -> None:
    (raw_6502 / "6502" / FETCH_LOG_NAME).write_text("{oops", encoding="utf-8")

    with pytest.raises(ManifestError, match=FETCH_LOG_NAME):
        build_entry(SPEC_6502, raw_6502)


def test_entry_records_the_latest_amendment_note(raw_6502: Path) -> None:
    entry = build_entry(SPEC_6502, raw_6502)

    assert entry.last_amendment is not None
    assert entry.last_amendment.date == date(2022, 3, 24)
    assert entry.last_amendment.reference == "7392/2"
    assert entry.amendment_note_count == 1


def test_title_comparison_ignores_case_and_circumflex(
    tmp_path: Path, mevzuat_fixture: Fixture
) -> None:
    raw_dir = _make_raw_dir(
        tmp_path / "raw",
        SPEC_TEBLIG,
        mevzuat_fixture("page_teblig_34343.html"),
        mevzuat_fixture("text_teblig_34343.html"),
        LINKED_FILES,
    )

    entry = build_entry(SPEC_TEBLIG, raw_dir)

    # sources.yaml has "Usûl ve Esaslar" in title case, the page prints it in capitals.
    assert entry.title == (
        "FİNANSAL TÜKETİCİLERDEN ALINACAK ÜCRETLERE İLİŞKİN USÛL VE ESASLAR HAKKINDA TEBLİĞ"
    )
    assert entry.number == "2020/7"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("expected_rg_number", "99999"),
        ("expected_rg_date", date(2014, 1, 1)),
        ("expected_title", "Bankacılık Kanunu"),
        ("number", "5411"),
    ],
)
def test_disagreement_with_the_official_page_fails_loudly(
    raw_6502: Path, field: str, value: object
) -> None:
    spec = SPEC_6502.model_copy(update={field: value})

    with pytest.raises(ManifestMismatch, match=field.removeprefix("expected_")):
        build_entry(spec, raw_6502)


def test_unverified_expectations_take_the_page_values(raw_6502: Path) -> None:
    spec = SPEC_6502.model_copy(
        update={"expected_title": None, "expected_rg_date": None, "expected_rg_number": None}
    )

    entry = build_entry(spec, raw_6502)

    assert entry.rg_number == "28835"


def test_missing_fetch_log_is_reported(raw_6502: Path) -> None:
    (raw_6502 / "6502" / FETCH_LOG_NAME).unlink()

    with pytest.raises(ManifestError, match=FETCH_LOG_NAME):
        build_entry(SPEC_6502, raw_6502)


def test_manifest_round_trips_through_json(raw_6502: Path, tmp_path: Path) -> None:
    manifest = build_manifest([SPEC_6502], raw_6502)
    path = tmp_path / "manifest.json"

    write_manifest(manifest, path)

    assert read_manifest(path) == manifest
    assert "TÜKETİCİNİN" in path.read_text(encoding="utf-8")


def test_verify_passes_for_untouched_files(raw_6502: Path, tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    write_manifest(build_manifest([SPEC_6502], raw_6502), path)

    assert verify_manifest(path, raw_6502) == []


def test_verify_detects_a_changed_file(raw_6502: Path, tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    write_manifest(build_manifest([SPEC_6502], raw_6502), path)
    (raw_6502 / "6502" / "source.pdf").write_bytes(b"%PDF-1.7 tampered")

    problems = verify_manifest(path, raw_6502)

    assert len(problems) == 1
    assert "6502/source.pdf" in problems[0]


def test_verify_detects_a_missing_file(raw_6502: Path, tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    write_manifest(build_manifest([SPEC_6502], raw_6502), path)
    (raw_6502 / "6502" / "source.pdf").unlink()

    assert verify_manifest(path, raw_6502) == ["missing: 6502/source.pdf"]


def test_verify_without_a_manifest_raises(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="manifest"):
        verify_manifest(tmp_path / "manifest.json", tmp_path)


def test_json_schema_describes_the_brief_fields() -> None:
    schema = manifest_json_schema()

    entry_props = schema["$defs"]["ManifestEntry"]["properties"]
    file_props = schema["$defs"]["FileEntry"]["properties"]
    for field in ("doc_type", "number", "rg_date", "rg_number", "source_page_url"):
        assert field in entry_props
    for field in ("url", "sha256", "fetched_at"):
        assert field in file_props
