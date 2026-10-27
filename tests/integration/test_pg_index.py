"""Index and search against a real PostgreSQL + pgvector (docker compose up -d db).

Runs in the dedicated test database of conftest.py. Skipped when it is not reachable.
"""

import psycopg
import pytest

from chunk_factory import make_chunk
from finhak.index.embed import HashingEmbedder
from finhak.index.indexer import IndexMismatch, build_index, check_index
from finhak.index.passages import passage
from finhak.retrieval.direct_ref import find_direct_refs
from finhak.retrieval.lexical import fts_search
from finhak.retrieval.store import PgChunkStore
from finhak.retrieval.types import Scored
from finhak.retrieval.vector import vector_search

pytestmark = pytest.mark.integration

EMBEDDER = HashingEmbedder(dim=64)
CHUNKS = [
    make_chunk("6502:m22:f1", "Faiz oranı sözleşmede yazılır.", madde="22", fikra=1),
    make_chunk("6502:m22:f2", "Değişken faiz tüketiciye bildirilir.", madde="22", fikra=2),
    make_chunk("6502:gm22:f1", "Geçiş hükmü.", madde="22", madde_kind="gecici"),
    make_chunk(
        "5464:m10:f1",
        "Kart çıkaran kuruluş yıllık aidatı sözleşmede belirtir.",
        madde="10",
        notes=("(Değişik:16/7/2020-7247/43 md.)",),
    ),
    make_chunk("6502:m30:f1", "Hesaplar hakkında hükümler.", madde="30", madde_title="Zamanaşımı"),
    make_chunk("6502:m31:f1", "Zamanaşımı hakkında hükümler.", madde="31"),
    make_chunk("6493:m38-39:f1", "Değiştirilen hükümler.", madde="38-39"),
    make_chunk("kart-yon:m28A:f1", "İntibak hükmü.", madde="28/A", madde_title="İntibak"),
    make_chunk("kart-yon:m27A:f1", "Üye işyeri e-POS cihazını kullanır.", madde="27/A"),
    make_chunk(
        "tcmb-ucret-talimat:s9:bc",
        "EFT işlemlerinden alınacak ücret.",
        madde="9",
        madde_kind=None,
        unit="bent",
        fikra=None,
        bents=("c",),
        version_date="2026-01-13",
    ),
]


@pytest.fixture
def indexed(conn: psycopg.Connection) -> psycopg.Connection:
    build_index(conn, CHUNKS, EMBEDDER, source_sha256="0" * 64)
    return conn


def _ids(hits: list[Scored]) -> list[str]:
    return [h.chunk_id for h in hits]


def test_build_index_stores_documents_chunks_and_metadata(conn: psycopg.Connection) -> None:
    stats = build_index(conn, CHUNKS, EMBEDDER, source_sha256="ab" * 32)

    assert (stats.documents, stats.chunks) == (5, len(CHUNKS))
    assert conn.execute("SELECT count(*) FROM chunks").fetchone() == (len(CHUNKS),)
    meta = dict(conn.execute("SELECT key, value FROM index_meta").fetchall())
    assert meta["embedder"] == "hashing-64"
    assert meta["dim"] == "64"
    assert meta["source_sha256"] == "ab" * 32


def test_building_in_another_schema_leaves_the_first_index_alone(
    conn: psycopg.Connection,
) -> None:
    # Regression: an unqualified DROP followed the search path into public's index.
    build_index(conn, CHUNKS, EMBEDDER, source_sha256="0" * 64)
    conn.execute("CREATE SCHEMA other")
    conn.execute("SET search_path TO other, public")

    build_index(conn, CHUNKS[:2], EMBEDDER, source_sha256="1" * 64)

    assert conn.execute("SELECT count(*) FROM other.chunks").fetchone() == (2,)
    assert conn.execute("SELECT count(*) FROM public.chunks").fetchone() == (len(CHUNKS),)


def test_rebuilding_replaces_the_previous_index(conn: psycopg.Connection) -> None:
    build_index(conn, CHUNKS, EMBEDDER, source_sha256="0" * 64)
    build_index(conn, CHUNKS[:2], EMBEDDER, source_sha256="1" * 64)

    assert conn.execute("SELECT count(*) FROM chunks").fetchone() == (2,)
    assert conn.execute("SELECT count(*) FROM documents").fetchone() == (1,)


def test_full_text_search_matches_inflected_turkish_forms(indexed: psycopg.Connection) -> None:
    assert _ids(fts_search(indexed, "aidatlar", k=5)) == ["5464:m10:f1"]


def test_full_text_search_does_not_need_every_word(indexed: psycopg.Connection) -> None:
    hits = fts_search(indexed, "Kredi kartı aidatımı geri alabilir miyim?", k=5)

    assert _ids(hits)[0] == "5464:m10:f1"


def test_full_text_search_weights_the_article_title(indexed: psycopg.Connection) -> None:
    assert _ids(fts_search(indexed, "zamanaşımı", k=5))[:2] == ["6502:m30:f1", "6502:m31:f1"]


@pytest.mark.parametrize("query", ["aidat' | !:* & (", "aidat\\ OR 1=1; --", "AİDAT"])
def test_full_text_query_syntax_is_not_injectable(indexed: psycopg.Connection, query: str) -> None:
    assert _ids(fts_search(indexed, query, k=5)) == ["5464:m10:f1"]


def test_full_text_search_matches_hyphenated_words(indexed: psycopg.Connection) -> None:
    assert _ids(fts_search(indexed, "e-pos", k=5))[0] == "kart-yon:m27A:f1"


def test_a_very_long_question_is_cut_rather_than_failing(indexed: psycopg.Connection) -> None:
    # Uncut, 120,000 words exceed PostgreSQL's tsvector size limit.
    assert _ids(fts_search(indexed, "aidat " * 120_000, k=5)) == ["5464:m10:f1"]


def test_full_text_search_without_words_gives_nothing(indexed: psycopg.Connection) -> None:
    # "ve" and "ile" are stopwords of the turkish configuration ("bir" is not).
    assert fts_search(indexed, "?! ve ile", k=5) == []


def test_vector_search_returns_the_nearest_passage_first(indexed: psycopg.Connection) -> None:
    target = CHUNKS[3]
    (query,) = EMBEDDER.embed([passage(target)])

    hits = vector_search(indexed, query, k=3)

    assert hits[0].chunk_id == target.id
    assert hits[0].score == pytest.approx(1.0, abs=1e-4)
    assert len(hits) == 3


def test_store_round_trips_chunks(indexed: psycopg.Connection) -> None:
    store = PgChunkStore(indexed)

    found = store.by_ids(["5464:m10:f1", "tcmb-ucret-talimat:s9:bc", "nope"])

    assert found == {c.id: c for c in CHUNKS if c.id in found}
    assert set(found) == {"5464:m10:f1", "tcmb-ucret-talimat:s9:bc"}
    assert [c.id for c in store.all()] == [c.id for c in CHUNKS]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("TKHK m.22", ["6502:m22:f1", "6502:m22:f2"]),
        ("6502 sayılı Kanunun geçici 22 nci maddesi", ["6502:gm22:f1"]),
        ("6493 sayılı Kanunun 38 inci maddesi", ["6493:m38-39:f1"]),
        ("6493 sayılı Kanunun 39 uncu maddesi", ["6493:m38-39:f1"]),
        ("Kart Yönetmeliği 28/A maddesi", ["kart-yon:m28A:f1"]),
        ("Uygulama Talimatının 9. maddesi", ["tcmb-ucret-talimat:s9:bc"]),
        ("TKHK m.99", []),
    ],
)
def test_store_finds_cited_articles(
    indexed: psycopg.Connection, query: str, expected: list[str]
) -> None:
    (ref,) = find_direct_refs(query)

    assert [c.id for c in PgChunkStore(indexed).by_ref(ref)] == expected


def test_check_index_rejects_a_different_embedder(indexed: psycopg.Connection) -> None:
    check_index(indexed, EMBEDDER)

    with pytest.raises(IndexMismatch, match="hashing-32"):
        check_index(indexed, HashingEmbedder(dim=32))


def test_check_index_reports_a_missing_index(conn: psycopg.Connection) -> None:
    with pytest.raises(IndexMismatch, match="build_index"):
        check_index(conn, EMBEDDER)
