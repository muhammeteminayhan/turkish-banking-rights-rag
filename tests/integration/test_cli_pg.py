"""The build_index / search / run_retrieval commands against PostgreSQL, with the hashing
embedder (no model download) in the test database of conftest.py."""

import io
import json
from pathlib import Path

import psycopg
import pytest

from chunk_factory import make_chunk
from finhak.evaluation import cli as eval_cli
from finhak.index import cli as index_cli
from finhak.index.db import Connection
from finhak.retrieval import cli as search_cli

pytestmark = pytest.mark.integration

CHUNKS = [
    make_chunk(
        "5464:m10:f1", "Kart çıkaran kuruluş yıllık aidatı sözleşmede belirtir.", madde="10"
    ),
    make_chunk("6502:m22:f1", "Faiz oranı sözleşmede yazılır.", madde="22"),
    make_chunk("6502:m30:f1", "Mevduat hesapları zamanaşımına uğrar.", madde="30"),
]
QUESTIONS = [
    {
        "id": "t-001",
        "category": "dogrudan",
        "question": "Kart aidatı nerede yazar?",
        "expected_chunks": ["5464:m10:f1"],
        "expected_answer": "Sözleşmede.",
        "evidence": [{"chunk": "5464:m10:f1", "quote": "yıllık aidatı"}],
        "confidence": "high",
    },
    {
        "id": "t-002",
        "category": "dogrudan",
        "question": "TKHK m.22 faiz",
        "expected_chunks": ["6502:m22:f1"],
        "expected_answer": "Sözleşmede yazılır.",
        "evidence": [],
        "confidence": "high",
    },
    {
        "id": "t-003",
        "category": "kapsam_disi",
        "question": "Kira artışı ne kadar?",
        "expected_chunks": [],
        "expected_answer": "Korpusta yok.",
        "evidence": [],
        "confidence": "high",
    },
]


@pytest.fixture
def db(conn: Connection, test_db_url: str) -> str:
    """The test database's URL, with its index tables dropped (by the conn fixture)."""
    return test_db_url


@pytest.fixture
def chunks_file(tmp_path: Path) -> Path:
    path = tmp_path / "chunks.jsonl"
    path.write_text("".join(c.model_dump_json() + "\n" for c in CHUNKS), encoding="utf-8")
    return path


@pytest.fixture
def built(db: str, chunks_file: Path) -> str:
    args = ["--chunks", str(chunks_file), "--embedder", "hashing", "--database-url", db]
    assert index_cli.main(args) == index_cli.EXIT_OK
    return db


def test_search_prints_ranked_chunks(built: str) -> None:
    out = io.StringIO()

    code = search_cli.main(
        ["kart aidatı", "--config", "hybrid", "--embedder", "hashing", "--database-url", built],
        out=out,
    )

    assert code == search_cli.EXIT_OK
    assert out.getvalue().splitlines()[0].startswith(" 1. [fusion")
    assert "5464:m10:f1" in out.getvalue().splitlines()[0]


def test_search_json_lists_cited_articles(built: str) -> None:
    out = io.StringIO()
    args = [
        "faiz oranı TKHK m.22",
        "--config",
        "fts",
        "--embedder",
        "hashing",
        "--database-url",
        built,
    ]

    assert search_cli.main([*args, "--json"], out=out) == search_cli.EXIT_OK

    payload = json.loads(out.getvalue())
    assert payload["refs"] == []  # the fts config does not look for cited articles
    assert payload["results"][0]["id"] == "6502:m22:f1"


def test_search_with_another_embedder_than_the_index_fails(db: str, chunks_file: Path) -> None:
    built_args = ["--chunks", str(chunks_file), "--embedder", "hashing", "--database-url", db]
    assert index_cli.main(built_args) == index_cli.EXIT_OK

    def other(_: object) -> object:
        from finhak.index.embed import HashingEmbedder

        return HashingEmbedder(dim=32)

    code = index_cli.main(built_args, embedder_factory=other)  # type: ignore[arg-type]
    assert code == index_cli.EXIT_OK  # rebuilding with a new embedder is allowed
    out = io.StringIO()
    args = ["kart", "--config", "vector", "--embedder", "hashing", "--database-url", db]
    assert search_cli.main(args, out=out) == search_cli.EXIT_FAILED


def test_run_retrieval_writes_metrics_and_report(built: str, tmp_path: Path) -> None:
    golden = tmp_path / "batch.jsonl"
    golden.write_text("".join(json.dumps(q) + "\n" for q in QUESTIONS), encoding="utf-8")
    out_dir = tmp_path / "results"

    code = eval_cli.main(
        [
            "--golden", str(golden), "--configs", "fts,bm25,bm25_prefix5,vector,hybrid",
            "--embedder", "hashing", "--database-url", built, "--out-dir", str(out_dir),
        ]
    )  # fmt: skip

    assert code == eval_cli.EXIT_OK
    (result_dir,) = out_dir.iterdir()
    metrics = json.loads((result_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["scored"] == 2
    assert metrics["status"] == {"draft": 3, "approved": 0}
    assert set(metrics["configs"]) == {"fts", "bm25", "bm25_prefix5", "vector", "hybrid"}
    assert metrics["configs"]["fts"]["madde"]["recall@5"] == 1.0
    report = (result_dir / "report.md").read_text(encoding="utf-8")
    assert "Draft numbers" in report
    assert "| `hybrid` |" in report
    rows = (result_dir / "per_question.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 2 * 5


def test_run_retrieval_rejects_expected_chunks_missing_from_the_index(
    built: str, tmp_path: Path
) -> None:
    golden = tmp_path / "batch.jsonl"
    bad = {**QUESTIONS[0], "expected_chunks": ["6502:m999:f1"], "evidence": []}
    golden.write_text(json.dumps(bad) + "\n", encoding="utf-8")

    args = ["--golden", str(golden), "--configs", "fts", "--embedder", "hashing"]
    assert eval_cli.main([*args, "--database-url", built]) == eval_cli.EXIT_FAILED


def _unreachable(url: str, connect_timeout: int = 10, create_extension: bool = False) -> Connection:
    raise psycopg.OperationalError("connection refused")


@pytest.mark.parametrize("args", [["--configs", "nope"], ["--golden", "missing.jsonl"], []])
def test_run_retrieval_fails_cleanly(
    args: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(eval_cli, "connect", _unreachable)
    golden = tmp_path / "g.jsonl"
    golden.write_text(json.dumps(QUESTIONS[0]) + "\n", encoding="utf-8")

    assert eval_cli.main(["--golden", str(golden), *args]) == eval_cli.EXIT_FAILED


def test_build_index_fails_cleanly_without_chunks_or_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(index_cli, "connect", _unreachable)
    assert index_cli.main(["--chunks", str(tmp_path / "none.jsonl")]) == index_cli.EXIT_FAILED
    chunks = tmp_path / "c.jsonl"
    chunks.write_text(CHUNKS[0].model_dump_json() + "\n", encoding="utf-8")

    args = ["--chunks", str(chunks), "--embedder", "hashing"]
    assert index_cli.main(args) == index_cli.EXIT_FAILED


def test_search_fails_cleanly_without_a_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(search_cli, "connect", _unreachable)

    assert search_cli.main(["q", "--config", "fts"], out=io.StringIO()) == search_cli.EXIT_FAILED
