"""A dedicated test database next to the real one, so tests never touch the real index.

The database `finhak_test` is created on first use and kept; each test starts with the
index tables dropped. Skipped when PostgreSQL is not reachable (docker compose up -d db).
"""

import os
from collections.abc import Iterator

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from finhak.config import database_url
from finhak.index.db import Connection, connect

TEST_DATABASE = "finhak_test"


@pytest.fixture(scope="session")
def test_db_url() -> str:
    base = os.environ.get("TEST_DATABASE_URL") or database_url()
    try:
        admin = psycopg.connect(base, autocommit=True, connect_timeout=3)
    except psycopg.OperationalError as exc:
        pytest.skip(f"PostgreSQL not reachable ({exc.__class__.__name__}); docker compose up -d db")
    with admin:
        exists = admin.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DATABASE,)
        ).fetchone()
        if not exists:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TEST_DATABASE)))
    return make_conninfo(base, dbname=TEST_DATABASE)


@pytest.fixture
def conn(test_db_url: str) -> Iterator[Connection]:
    connection = connect(test_db_url, connect_timeout=3, create_extension=True)
    try:
        connection.execute("DROP SCHEMA IF EXISTS other CASCADE")
        connection.execute("DROP TABLE IF EXISTS chunks, documents, index_meta")
        yield connection
    finally:
        connection.close()
