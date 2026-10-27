"""Citation verification: no unchecked citation reaches the user.

A citation passes when
- its chunk is one of the chunks shown to the model for this question,
- its document, article and fıkra match that chunk's metadata, and
- its quote, after case and whitespace are normalised, is a substring of the chunk's text
  or of one of its notes (talimat footnotes carry the current fee caps), and is long
  enough to mean something. The user is shown the matching span of the source, not the
  model's spelling of it.
The answer text is checked too: it must not be empty, and every number in it must occur
in a cited chunk (its text, notes, label, article or fıkra) or in the question. An answer
that is not out of scope needs at least one citation; an out-of-scope answer has none. The
error messages are written for the model: they go back in the retry prompt.
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from finhak.generation.numbers import numbers_in
from finhak.generation.schema import AnswerOut, CitationOut
from finhak.parsing.chunker import Chunk
from finhak.textnorm import tr_casefold

MIN_QUOTE_CHARS = 15

ErrorKind = Literal[
    "no_citations",
    "citation_when_out_of_scope",
    "empty_answer",
    "unsupported_number",
    "unknown_chunk",
    "doc_mismatch",
    "madde_mismatch",
    "fikra_mismatch",
    "quote_too_short",
    "quote_not_found",
]

_PUNCTUATION = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-"})
_TURKISH_I = str.maketrans({"I": "ı", "İ": "i"})
_CIRCUMFLEX = str.maketrans({"â": "a", "î": "i", "û": "u"})
_SOFT_HYPHEN = "­"


@dataclass(frozen=True)
class CitationError:
    kind: ErrorKind
    citation: int | None  # index in AnswerOut.citations; None for answer-level errors
    message: str


@dataclass(frozen=True)
class VerificationReport:
    errors: tuple[CitationError, ...]
    cited_chunks: tuple[Chunk, ...]  # each cited chunk once, in citation order (when ok)
    quotes: tuple[str, ...] = ()  # the source span of each citation, in order (when ok)
    unsupported_numbers: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors


def normalize(text: str) -> str:
    """Casefolded (Turkish rules), one space per whitespace run, unified quotes/dashes."""
    return tr_casefold(text.replace(_SOFT_HYPHEN, "").translate(_PUNCTUATION))


def verify_answer(
    answer: AnswerOut, retrieved: Sequence[Chunk], question: str = ""
) -> VerificationReport:
    by_id = {chunk.id: chunk for chunk in retrieved}
    if answer.out_of_scope:
        scope_errors = (
            (CitationError("citation_when_out_of_scope", None, _OUT_OF_SCOPE_MESSAGE),)
            if answer.citations
            else ()
        )
        return VerificationReport(scope_errors, ())
    if not answer.citations:
        return VerificationReport((CitationError("no_citations", None, _NO_CITATION),), ())

    errors: list[CitationError] = []
    spans: list[str] = []
    for index, citation in enumerate(answer.citations):
        outcome = _check(index, citation, by_id)
        if isinstance(outcome, CitationError):
            errors.append(outcome)
        else:
            spans.append(outcome)
    if not answer.answer.strip():
        errors.append(CitationError("empty_answer", None, _EMPTY_ANSWER))
    cited = tuple(
        {c.chunk_id: by_id[c.chunk_id] for c in answer.citations if c.chunk_id in by_id}.values()
    )
    unsupported = _unsupported_numbers(answer.answer, cited, question)
    if unsupported:
        errors.append(
            CitationError(
                "unsupported_number",
                None,
                "Cevaptaki şu sayılar atıf yapılan kaynaklarda geçmiyor: "
                f"{', '.join(unsupported)}. Yalnızca kaynakta yazan sayıları kullan; "
                "hesaplama yapma.",
            )
        )
    if errors:
        return VerificationReport(tuple(errors), (), (), unsupported)
    return VerificationReport((), cited, tuple(spans), ())


_OUT_OF_SCOPE_MESSAGE = "out_of_scope true iken citations boş olmalı."
_NO_CITATION = (
    "Cevapta hiç atıf yok. Her iddia için verilen kaynaklardan en az bir atıf ekle; "
    "kaynaklar soruyu cevaplamıyorsa out_of_scope true yap."
)
_EMPTY_ANSWER = "answer alanı boş. Soruyu kaynaklara dayanarak kısa bir cümleyle cevapla."


def _check(index: int, citation: CitationOut, by_id: dict[str, Chunk]) -> CitationError | str:
    """The citation's error, or the matching span of the source."""
    chunk = by_id.get(citation.chunk_id)
    where = f"Atıf {index + 1} ({citation.chunk_id})"
    if chunk is None:
        return CitationError(
            "unknown_chunk",
            index,
            f"{where}: bu kimlikte bir kaynak verilmedi. "
            "Yalnızca köşeli parantezdeki kimlikleri kullan.",
        )
    if citation.doc_id != chunk.doc_id:
        return CitationError(
            "doc_mismatch", index, f"{where}: belge {chunk.doc_id}, {citation.doc_id} değil."
        )
    if _madde_key(citation.madde) != _madde_key(chunk.madde):
        return CitationError(
            "madde_mismatch", index, f"{where}: madde {chunk.madde}, {citation.madde} değil."
        )
    if not _fikra_matches(citation.fikra, chunk):
        return CitationError(
            "fikra_mismatch",
            index,
            f"{where}: fıkra {_fikra_label(chunk)}, {citation.fikra} değil.",
        )
    quote = normalize(citation.quote)
    if len(quote) < MIN_QUOTE_CHARS:
        return CitationError(
            "quote_too_short",
            index,
            f"{where}: alıntı en az {MIN_QUOTE_CHARS} karakter olmalı ve iddiayı desteklemeli.",
        )
    for source in (chunk.text, *chunk.notes):  # one source at a time: no quote across them
        span = _find_span(source, quote)
        if span is not None:
            return span
    return CitationError(
        "quote_not_found",
        index,
        f"{where}: alıntı kaynak metinde birebir geçmiyor. Metinden kelimesi kelimesine kopyala.",
    )


def _find_span(source: str, normalized_quote: str) -> str | None:
    """The part of `source` whose normalised form is `normalized_quote`, if any."""
    text = unicodedata.normalize("NFC", source)
    folded: list[str] = []
    origin: list[int] = []  # index in `text` of each folded character
    for position, char in enumerate(text):
        if char == _SOFT_HYPHEN:
            continue
        if char.isspace():
            if folded and folded[-1] != " ":
                folded.append(" ")
                origin.append(position)
            continue
        for out in (
            char.translate(_PUNCTUATION).translate(_TURKISH_I).lower().translate(_CIRCUMFLEX)
        ):
            folded.append(out)
            origin.append(position)
    start = "".join(folded).find(normalized_quote)
    if start < 0:
        return None
    end = start + len(normalized_quote) - 1
    return text[origin[start] : origin[end] + 1]


def _unsupported_numbers(answer: str, cited: Sequence[Chunk], question: str) -> tuple[str, ...]:
    allowed = numbers_in(question)
    for chunk in cited:
        sources = [chunk.text, *chunk.notes, chunk.doc_label, chunk.madde or ""]
        allowed |= numbers_in(" ".join(sources))
        allowed |= {str(n) for n in (chunk.fikra, chunk.fikra_last) if n is not None}
    return tuple(sorted(numbers_in(answer) - allowed, key=lambda n: (len(n), n)))


def _madde_key(madde: str | None) -> str | None:
    """ "28/A", "28A" and "28 a" are one article; "2/8" and "28" are not."""
    if madde is None:
        return None
    key = re.sub(r"\s+", "", tr_casefold(madde))
    return re.sub(r"(?<=\d)[/.-](?=[^\W\d_])", "", key)


def _fikra_matches(cited: int | None, chunk: Chunk) -> bool:
    if chunk.fikra is None:
        return cited is None
    if cited is None:
        return False
    return chunk.fikra <= cited <= (chunk.fikra_last or chunk.fikra)


def _fikra_label(chunk: Chunk) -> str:
    if chunk.fikra is None:
        return "yok (null)"
    return f"{chunk.fikra}-{chunk.fikra_last}" if chunk.fikra_last else str(chunk.fikra)
