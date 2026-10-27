"""PostgreSQL full-text search with the turkish configuration (the production lexical leg).

A question is turned into an OR of its stemmed words: plainto_tsquery would AND them, and
a natural question ("Kredi kartı aidatımı geri alabilir miyim?") rarely has every word in
one fıkra. ts_rank then prefers chunks that match more, and rarer, words.
"""

import re

from finhak.index.db import Connection
from finhak.retrieval.types import Scored
from finhak.textnorm import tr_casefold

# Only word characters and the separators inside numbers and dates reach the database;
# quotes and backslashes never do, so quote_literal below always yields a plain literal.
_UNSAFE = re.compile(r"[^\w\s./-]")
_RANK_NORMALIZATION = 1  # divide by 1 + log(document length)
MAX_QUERY_CHARS = 2000  # a longer question is cut (tsvector size limit, query cost)

_SQL = f"""
    WITH q AS (
        -- Cast, not to_tsquery: re-parsing would split "e-pos" into a phrase.
        SELECT string_agg(quote_literal(lexeme), ' | ')::tsquery AS query
        FROM unnest(to_tsvector('turkish', %(q)s))
    )
    SELECT c.id, ts_rank(c.tsv, q.query, {_RANK_NORMALIZATION}) AS score
    FROM chunks c, q
    WHERE c.tsv @@ q.query
    ORDER BY score DESC, c.ordinal
    LIMIT %(k)s
"""


def fts_search(conn: Connection, query: str, k: int) -> list[Scored]:
    cleaned = _UNSAFE.sub(" ", tr_casefold(query[:MAX_QUERY_CHARS]))
    rows = conn.execute(_SQL, {"q": cleaned, "k": k}).fetchall()
    return [Scored(str(chunk_id), float(score)) for chunk_id, score in rows]
