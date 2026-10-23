"""End to end on a fake mevzuat.gov.tr: fetch → manifest → parse → chunks.jsonl + report."""

import json
from pathlib import Path

import pytest
from mevzuat_stub import SPEC_6502, MevzuatServer, make_client

from finhak.ingest.fetch import fetch_source
from finhak.ingest.manifest import build_manifest, write_manifest
from finhak.parsing import cli
from finhak.parsing.chunker import Chunk

pytestmark = pytest.mark.unit


def _prepare(tmp_path: Path) -> list[str]:
    raw = tmp_path / "raw"
    fetch_source(SPEC_6502, make_client(MevzuatServer()), raw)
    write_manifest(build_manifest([SPEC_6502], raw), tmp_path / "manifest.json")
    return [
        "--manifest",
        str(tmp_path / "manifest.json"),
        "--raw-dir",
        str(raw),
        "--out-dir",
        str(tmp_path / "processed"),
    ]


def test_parse_writes_chunks_and_a_report(tmp_path: Path) -> None:
    code = cli.main(_prepare(tmp_path))

    assert code == 0
    lines = (tmp_path / "processed" / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
    chunks = [Chunk.model_validate_json(line) for line in lines]
    assert chunks[0].id == "6502:m1:f1"
    assert chunks[0].madde_title == "Amaç"
    assert chunks[0].text.startswith("Bu Kanunun amacı;")
    report = json.loads((tmp_path / "processed" / "parse_report.json").read_text(encoding="utf-8"))
    (doc,) = report["documents"]
    assert doc["doc_id"] == "6502"
    assert doc["maddeler"]["madde"] >= 3
    assert doc["chunks"]["fikra"] == sum(1 for c in chunks if c.unit == "fikra")
    assert (tmp_path / "processed" / "parse_report.md").read_text(encoding="utf-8").startswith("#")


def test_unreadable_pdf_is_reported_not_fatal(tmp_path: Path) -> None:
    cli.main(_prepare(tmp_path))

    report = json.loads((tmp_path / "processed" / "parse_report.json").read_text(encoding="utf-8"))

    (doc,) = report["documents"]
    assert doc["page_coverage"] is None
    assert any(note.startswith("PDF not readable") for note in doc["notes"])


def test_changed_raw_file_stops_the_parse(tmp_path: Path) -> None:
    argv = _prepare(tmp_path)
    (tmp_path / "raw" / "6502" / "text.html").write_text("<html>edited</html>", encoding="utf-8")

    assert cli.main(argv) == 1
    assert not (tmp_path / "processed" / "chunks.jsonl").exists()


def test_chunk_ids_in_the_output_are_unique(tmp_path: Path) -> None:
    cli.main(_prepare(tmp_path))

    lines = (tmp_path / "processed" / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
    ids = [json.loads(line)["id"] for line in lines]
    assert len(ids) == len(set(ids))
