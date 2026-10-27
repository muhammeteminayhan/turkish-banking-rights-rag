"""DDL of the retrieval index. A database (or schema) holds one index at a time.

Full-text input is case-folded in Python (finhak.textnorm.tr_casefold) before it reaches
to_tsvector, because PostgreSQL lowercases with the database locale, which maps I→i.
Weights: A article title, B text, C notes, D document label.
"""

HNSW_MAX_DIM = 2000  # pgvector cannot build an HNSW index on wider `vector` columns
INDEX_TABLES = ("chunks", "documents", "index_meta")  # dropped by build_index, qualified


def table_statements(dim: int) -> tuple[str, ...]:
    if not isinstance(dim, int) or not 0 < dim <= HNSW_MAX_DIM:
        raise ValueError(f"embedding dim must be 1..{HNSW_MAX_DIM} for HNSW, got {dim!r}")
    return (
        "CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public",
        """
        CREATE TABLE documents (
            id           text PRIMARY KEY,
            label        text NOT NULL,
            title        text NOT NULL,
            doc_type     text NOT NULL,
            origin       text NOT NULL,
            source_url   text NOT NULL,
            rg_date      date,
            version_date date,
            collected_on date NOT NULL
        )
        """,
        f"""
        CREATE TABLE chunks (
            id         text PRIMARY KEY,
            doc_id     text NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
            ordinal    integer NOT NULL UNIQUE,
            unit       text NOT NULL,
            madde      text,
            madde_kind text,
            fikra      integer,
            fikra_last integer,
            data       jsonb NOT NULL,
            tsv        tsvector NOT NULL,
            embedding  vector({dim}) NOT NULL
        )
        """,
        "CREATE TABLE index_meta (key text PRIMARY KEY, value text NOT NULL)",
    )


INDEX_STATEMENTS = (
    "CREATE INDEX chunks_tsv_idx ON chunks USING gin (tsv)",
    "CREATE INDEX chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops)",
    "CREATE INDEX chunks_article_idx ON chunks (doc_id, madde)",
)

# Parameters: title, body, notes, label — each already tr_casefold-ed.
TSV_EXPRESSION = (
    "setweight(to_tsvector('turkish', %(fts_title)s), 'A')"
    " || setweight(to_tsvector('turkish', %(fts_body)s), 'B')"
    " || setweight(to_tsvector('turkish', %(fts_notes)s), 'C')"
    " || setweight(to_tsvector('turkish', %(fts_label)s), 'D')"
)
