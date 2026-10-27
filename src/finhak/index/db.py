"""PostgreSQL connections with the pgvector types registered."""

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]


def connect(url: str, connect_timeout: int = 10, create_extension: bool = False) -> Connection:
    """Autocommit connection with the vector type registered; build_index opens its own
    transaction. Only the index builder creates the extension, so searches also work for
    a read-only role."""
    conn = psycopg.connect(url, autocommit=True, connect_timeout=connect_timeout)
    try:
        if create_extension:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")
        register_vector(conn)
    except BaseException:
        conn.close()
        raise
    return conn
