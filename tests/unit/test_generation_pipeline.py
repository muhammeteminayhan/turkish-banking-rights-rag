"""The answer pipeline with a scripted provider and a fixed retriever: no model, no database."""

import json
from collections.abc import Sequence
from typing import Any

import pytest

from chunk_factory import make_chunk
from finhak.generation.pipeline import (
    OUT_OF_SCOPE_MESSAGE,
    UNVERIFIED_MESSAGE,
    AnswerResult,
    answer_question,
)
from finhak.generation.render import DISCLAIMER, INFERRED_FIKRA_NOTE
from finhak.llm.base import ChatMessage, LLMOutputError, LLMResult, LLMUnavailable, T, Usage
from finhak.retrieval.direct_ref import find_direct_refs
from finhak.retrieval.hybrid import RetrievedChunk, SearchConfig, SearchOutcome

pytestmark = pytest.mark.unit

CHUNKS = [
    make_chunk("6502:m22:f2", "Kredi kartı sözleşmeleri, ödemenin üç aydan daha uzun süre "
               "ertelenmesi hâlinde tüketici kredisi sözleşmesi sayılır.", madde="22", fikra=2),
    make_chunk("5411:m2:f2", "Bu Kanun, Türkiye'de kurulu bankaları kapsar ve uygulanır.",
               madde="2", fikra=2, fikra_inferred=True),
]  # fmt: skip


class FixedRetriever:
    def __init__(self, chunks: Sequence[Any] = CHUNKS) -> None:
        self.chunks = list(chunks)
        self.calls: list[tuple[str, str, int]] = []

    def search(self, query: str, config: SearchConfig | str, limit: int = 10) -> SearchOutcome:
        self.calls.append((query, str(config), limit))
        results = tuple(RetrievedChunk(c, 1.0, "rerank") for c in self.chunks[:limit])
        refs = find_direct_refs(query)
        known = {(c.doc_id, c.madde) for c in self.chunks}
        unmatched = tuple(r for r in refs if (r.doc_id, r.madde) not in known)
        return SearchOutcome(results, refs, unmatched)


class ScriptedProvider:
    """Returns (or raises) the scripted replies in order and records every prompt."""

    def __init__(self, *replies: dict[str, Any] | Exception) -> None:
        self.replies = list(replies)
        self.prompts: list[tuple[str, list[ChatMessage]]] = []

    @property
    def name(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "fake-1"

    def generate(
        self, system: str, messages: Sequence[ChatMessage], schema: type[T]
    ) -> LLMResult[T]:
        self.prompts.append((system, list(messages)))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        raw = json.dumps(reply, ensure_ascii=False)
        return LLMResult(schema.model_validate(reply), raw, Usage(100, 20), "fake", "fake-1", 0.5)


def _reply(citations: list[dict[str, Any]], out_of_scope: bool = False) -> dict[str, Any]:
    return {"answer": "Üç aydan uzun ertelemede tüketici kredisi sayılır.", "citations": citations,
            "out_of_scope": out_of_scope, "false_premise": False, "confidence": "high"}  # fmt: skip


GOOD = {"chunk_id": "6502:m22:f2", "doc_id": "6502", "madde": "22", "fikra": 2,
        "quote": "ödemenin üç aydan daha uzun süre ertelenmesi"}  # fmt: skip
INFERRED = {"chunk_id": "5411:m2:f2", "doc_id": "5411", "madde": "2", "fikra": 2,
            "quote": "Türkiye'de kurulu bankaları kapsar"}  # fmt: skip


def _ask(
    provider: ScriptedProvider, question: str = "Kart borcu ertelenirse?", **kw: Any
) -> AnswerResult:
    return answer_question(question, FixedRetriever(**kw), provider)


def test_a_verified_answer_comes_back_with_rendered_citations() -> None:
    result = _ask(ScriptedProvider(_reply([GOOD, INFERRED])))

    assert result.status == "answered"
    assert result.attempts == 1
    assert [c.chunk_id for c in result.citations] == ["6502:m22:f2", "5411:m2:f2"]
    assert result.citations[1].label.endswith(" md. 2/2")
    assert INFERRED_FIKRA_NOTE in result.citations[1].notes
    assert result.citations[0].snapshot.endswith("tarihinde alındı.")
    assert result.disclaimer == DISCLAIMER
    assert (result.usage, result.cost_usd) == (Usage(100, 20), 0.5)


def test_the_prompt_lists_each_passage_with_its_id_and_metadata() -> None:
    provider = ScriptedProvider(_reply([GOOD]))

    _ask(provider, question="Kart borcu ertelenirse?")

    system, (message,) = provider.prompts[0]
    assert "chunk_id" in system and "birebir" in system
    assert "[6502:m22:f2]" in message.content
    assert "doc_id: 6502 | madde: 22 | fıkra: 2" in message.content
    assert "fıkra: 2 (metinde yazmıyor, sayıldı)" in message.content
    assert message.content.rstrip().endswith("Soru: Kart borcu ertelenirse?")


def test_a_bad_citation_is_sent_back_once_and_a_fixed_answer_is_accepted() -> None:
    provider = ScriptedProvider(_reply([{**GOOD, "madde": "23"}]), _reply([GOOD]))

    result = _ask(provider)

    assert (result.status, result.attempts) == ("answered", 2)
    _, retry = provider.prompts[1]
    assert [m.role for m in retry] == ["user", "assistant", "user"]
    assert "madde 22, 23 değil" in retry[2].content
    assert result.usage == Usage(200, 40)
    assert result.cost_usd == pytest.approx(1.0)


def test_an_answer_that_fails_twice_is_withheld() -> None:
    bad = _reply([{**GOOD, "quote": "bu cümle kaynakta hiç geçmiyor ama uzun"}])

    result = _ask(ScriptedProvider(bad, bad))

    assert result.status == "unverified"
    assert result.answer == UNVERIFIED_MESSAGE
    assert result.citations == ()
    assert any("birebir geçmiyor" in e for e in result.verification_errors)


def test_invalid_json_counts_as_a_failed_attempt() -> None:
    provider = ScriptedProvider(LLMOutputError("not json"), _reply([GOOD]))

    result = _ask(provider)

    assert (result.status, result.attempts) == ("answered", 2)
    assert "JSON" in provider.prompts[1][1][-1].content


def test_an_out_of_scope_answer_has_the_standard_text_and_no_citations() -> None:
    result = _ask(ScriptedProvider(_reply([], out_of_scope=True)))

    assert result.status == "out_of_scope"
    assert result.answer == OUT_OF_SCOPE_MESSAGE
    assert result.citations == ()


def test_no_retrieved_passages_means_no_model_call() -> None:
    provider = ScriptedProvider()

    result = _ask(provider, chunks=[])

    assert result.status == "no_sources"
    assert provider.prompts == []


def test_an_unavailable_model_is_not_hidden() -> None:
    with pytest.raises(LLMUnavailable):
        _ask(ScriptedProvider(LLMUnavailable("ollama is not running")))


def test_a_cited_article_missing_from_the_corpus_is_noted() -> None:
    provider = ScriptedProvider(_reply([GOOD]))

    result = _ask(provider, question="TKHK m.999 ne diyor?")

    assert any("6502 md. 999" in note for note in result.notes)
    assert "6502 md. 999" in provider.prompts[0][1][0].content


def test_false_premise_and_confidence_are_passed_through() -> None:
    reply = {**_reply([GOOD]), "false_premise": True, "confidence": "medium"}

    result = _ask(ScriptedProvider(reply))

    assert (result.false_premise, result.confidence) == (True, "medium")


def test_a_long_passage_is_cut_in_the_prompt_but_verified_against_the_full_text() -> None:
    from finhak.generation.prompts import MAX_PASSAGE_CHARS, passage_block

    tail = "Bu son cümle yalnızca tam metinde bulunur ve kısaltılmış istemde görünmez."
    long_chunk = make_chunk("6502:ek1:p1", "a " * MAX_PASSAGE_CHARS + tail, madde=None,
                            madde_kind=None, unit="ek", fikra=None)  # fmt: skip

    block = passage_block(long_chunk)

    assert tail not in block
    assert "[metin kısaltıldı]" in block
    assert len(block) < MAX_PASSAGE_CHARS + 600


def test_a_refusal_is_not_retried_and_withholds_the_answer() -> None:
    from finhak.llm.base import LLMRefusal

    provider = ScriptedProvider(LLMRefusal("declined", usage=Usage(50, 0), cost_usd=0.1))

    result = _ask(provider)

    assert (result.status, result.attempts) == ("unverified", 1)
    assert len(provider.prompts) == 1
    assert result.usage == Usage(50, 0)
    assert "reddetti" in result.verification_errors[0]


def test_two_invalid_replies_are_withheld_and_both_are_counted() -> None:
    bad = LLMOutputError("not json", usage=Usage(100, 900), cost_usd=0.2)
    provider = ScriptedProvider(bad, LLMOutputError("still not json", usage=Usage(100, 900)))

    result = _ask(provider)

    assert (result.status, result.attempts) == ("unverified", 2)
    assert result.usage == Usage(200, 1800)
    assert result.cost_usd == pytest.approx(0.2)


def test_an_unknown_price_makes_the_cost_unknown() -> None:
    provider = ScriptedProvider(
        LLMOutputError("x", usage=Usage(1, 1), cost_usd=None), _reply([GOOD])
    )

    assert _ask(provider).cost_usd is None


def test_passages_over_the_prompt_budget_are_not_shown_and_cannot_be_cited() -> None:
    from finhak.generation.prompts import build_prompt

    big = [make_chunk(f"6502:m{n}:f1", "x " * 900, madde=str(n)) for n in range(1, 30)]

    prompt, shown = build_prompt("Soru?", big, [], budget=6000)

    assert 1 <= len(shown) < len(big)
    assert f"[{shown[-1].id}]" in prompt
    assert f"[{big[len(shown)].id}]" not in prompt


def test_the_prompt_marks_temporary_and_repealed_articles() -> None:
    from finhak.generation.prompts import passage_block

    block = passage_block(
        make_chunk("6502:gm1:f1", "Geçiş hükmü.", madde="1", madde_kind="gecici", mulga=True)
    )

    assert "madde türü: geçici madde" in block
    assert "MÜLGA" in block


def test_the_shown_quote_is_the_source_span() -> None:
    shouted = {**GOOD, "quote": "ÖDEMENİN ÜÇ AYDAN   DAHA UZUN süre ertelenmesi"}

    result = _ask(ScriptedProvider(_reply([shouted])))

    assert result.citations[0].quote == "ödemenin üç aydan daha uzun süre ertelenmesi"
