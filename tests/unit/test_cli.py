import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from mevzuat_stub import SOURCES_YAML_6502, TEXT_PATH, MevzuatServer, make_client

from finhak.ingest import cli
from finhak.ingest.http import PoliteClient

pytestmark = pytest.mark.unit


def _paths(tmp_path: Path) -> dict[str, Path]:
    sources = tmp_path / "sources.yaml"
    sources.write_text(SOURCES_YAML_6502, encoding="utf-8")
    return {
        "sources": sources,
        "raw": tmp_path / "raw",
        "manifest": tmp_path / "manifest.json",
        "schema": tmp_path / "manifest.schema.json",
    }


def _argv(paths: dict[str, Path], *extra: str) -> list[str]:
    return [
        "--sources",
        str(paths["sources"]),
        "--raw-dir",
        str(paths["raw"]),
        "--manifest",
        str(paths["manifest"]),
        "--schema",
        str(paths["schema"]),
        *extra,
    ]


def _factory(server: MevzuatServer) -> Callable[[float], PoliteClient]:
    return lambda interval: make_client(server, interval)


def test_full_run_writes_a_verified_manifest_and_schema(tmp_path: Path) -> None:
    paths = _paths(tmp_path)

    code = cli.main(_argv(paths), client_factory=_factory(MevzuatServer()))

    assert code == 0
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert [d["id"] for d in manifest["documents"]] == ["6502"]
    assert "ManifestEntry" in json.loads(paths["schema"].read_text(encoding="utf-8"))["$defs"]


def test_second_run_sends_no_requests(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    cli.main(_argv(paths), client_factory=_factory(MevzuatServer()))
    second = MevzuatServer()

    assert cli.main(_argv(paths), client_factory=_factory(second)) == 0
    assert second.paths == []


def test_failed_document_means_exit_1_and_no_manifest(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    server = MevzuatServer(overrides={TEXT_PATH: httpx.Response(404)})

    assert cli.main(_argv(paths), client_factory=_factory(server)) == 1
    assert not paths["manifest"].exists()


def test_dry_run_sends_no_requests_and_writes_nothing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    paths = _paths(tmp_path)
    server = MevzuatServer()

    with caplog.at_level("INFO"):
        code = cli.main(_argv(paths, "--dry-run"), client_factory=_factory(server))

    assert code == 0
    assert server.paths == []
    assert not paths["manifest"].exists()
    assert "would fetch" in caplog.text


def test_dry_run_after_a_full_run_reports_nothing_to_fetch(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    paths = _paths(tmp_path)
    cli.main(_argv(paths), client_factory=_factory(MevzuatServer()))

    with caplog.at_level("INFO"):
        cli.main(_argv(paths, "--dry-run"), client_factory=_factory(MevzuatServer()))

    assert "6502: up to date" in caplog.text


def test_dry_run_with_refresh_plans_every_file(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    paths = _paths(tmp_path)
    cli.main(_argv(paths), client_factory=_factory(MevzuatServer()))

    with caplog.at_level("INFO"):
        cli.main(_argv(paths, "--dry-run", "--refresh"), client_factory=_factory(MevzuatServer()))

    assert "6502: --refresh would fetch everything again" in caplog.text


def test_dry_run_notices_a_file_deleted_from_disk(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    paths = _paths(tmp_path)
    cli.main(_argv(paths), client_factory=_factory(MevzuatServer()))
    (paths["raw"] / "6502" / "source.pdf").unlink()

    with caplog.at_level("INFO"):
        cli.main(_argv(paths, "--dry-run"), client_factory=_factory(MevzuatServer()))

    assert "would fetch ['source.pdf']" in caplog.text


def test_unknown_only_id_exits_2(tmp_path: Path) -> None:
    paths = _paths(tmp_path)

    assert cli.main(_argv(paths, "--only", "9999"), client_factory=_factory(MevzuatServer())) == 2


@pytest.mark.parametrize("value", ["0.5", "nan", "abc"])
def test_unsafe_interval_from_the_environment_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, value: str
) -> None:
    monkeypatch.setenv("FETCH_MIN_INTERVAL_SECONDS", value)
    server = MevzuatServer()

    code = cli.main(_argv(_paths(tmp_path)), client_factory=_factory(server))

    assert code == 2
    assert server.paths == []
    assert "FETCH_MIN_INTERVAL_SECONDS" in caplog.text


def test_verify_without_a_manifest_exits_1(tmp_path: Path) -> None:
    assert cli.main(_argv(_paths(tmp_path), "--verify")) == 1


def test_verify_detects_a_changed_file(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    cli.main(_argv(paths), client_factory=_factory(MevzuatServer()))
    (paths["raw"] / "6502" / "source.pdf").write_bytes(b"%PDF-1.7 edited")

    assert cli.main(_argv(paths, "--verify")) == 1


def test_corrupt_fetch_log_exits_1_without_a_traceback(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    paths = _paths(tmp_path)
    cli.main(_argv(paths), client_factory=_factory(MevzuatServer()))
    (paths["raw"] / "6502" / "_fetch.json").write_text("{oops", encoding="utf-8")

    assert cli.main(_argv(paths), client_factory=_factory(MevzuatServer())) == 1
    assert "_fetch.json" in caplog.text


def test_invalid_sources_file_exits_2(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    paths["sources"].write_text("sources: [unclosed\n", encoding="utf-8")

    assert cli.main(_argv(paths), client_factory=_factory(MevzuatServer())) == 2
