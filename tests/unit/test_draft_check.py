from pathlib import Path

import pytest

from chunk_factory import make_chunk
from finhak.evaluation import draft_cli
from finhak.evaluation.draft_check import check_draft
from finhak.evaluation.golden import GoldenQuestion

pytestmark = pytest.mark.unit

CHUNKS = {
    c.id: c
    for c in [
        make_chunk(
            "6502:m22:f3",
            "Tüketici kredisi sözleşmesi yazılı veya mesafeli olarak kurulmadıkça geçerli olmaz.",
            madde="22",
            fikra=3,
        ),
        make_chunk(
            "5464:m9:f1",
            "Kart çıkaran kuruluşlar, kart hamilleri talep etmedikçe kart limitlerini "
            "artıramazlar.",
            madde="9",
            fikra=1,
            notes=("[Dipnot 1] Değişik: RG-1/1/2020",),
        ),
    ]
}


def _question(**fields: object) -> GoldenQuestion:
    data: dict[str, object] = {
        "id": "b2-001",
        "category": "dogrudan",
        "question": "Bankam ben istemeden kart limitimi yükseltebilir mi?",
        "expected_chunks": ["5464:m9:f1"],
        "expected_answer": "Hayır; talep etmedikçe limit artırılamaz.",
        "evidence": [{"chunk": "5464:m9:f1", "quote": "talep etmedikçe kart limitlerini"}],
        "confidence": "high",
    }
    return GoldenQuestion.model_validate({**data, **fields})


def _messages(*questions: GoldenQuestion, existing: tuple[GoldenQuestion, ...] = ()) -> list[str]:
    return [p.message for p in check_draft(questions, CHUNKS, existing)]


def test_a_well_formed_draft_has_no_problems() -> None:
    out_of_scope = _question(id="b2-002", category="kapsam_disi", question="Kripto vergisi?",
                             expected_chunks=[], evidence=[])  # fmt: skip

    assert _messages(_question(), out_of_scope) == []


def test_a_quote_must_be_literal_in_the_chunk_text_or_a_note() -> None:
    from_note = _question(evidence=[{"chunk": "5464:m9:f1", "quote": "Değişik: RG-1/1/2020"}])
    paraphrase = _question(evidence=[{"chunk": "5464:m9:f1", "quote": "limitleri artıramaz"}])

    assert _messages(from_note) == []
    assert _messages(paraphrase) == ["quote not found in 5464:m9:f1: 'limitleri artıramaz'"]


def test_unknown_chunks_and_expected_chunks_without_a_quote_are_reported() -> None:
    unknown = _question(expected_chunks=["5464:m9:f1", "5464:m99:f1"])

    assert _messages(unknown) == [
        "unknown chunk 5464:m99:f1",
        "expected chunk 5464:m99:f1 has no evidence quote",
    ]


def test_a_question_must_not_copy_five_words_from_its_article() -> None:
    four = _question(question="Kart hamilleri talep etmedikçe ne olur?")
    seven = _question(question="Kart çıkaran kuruluşlar kart hamilleri talep etmedikçe ne yapar?")

    assert _messages(four) == []
    assert _messages(seven) == [
        "question copies 'kart çıkaran kuruluşlar kart hamilleri talep etmedikçe' from 5464:m9:f1"
    ]


def test_ids_and_questions_already_in_the_golden_set_are_reported() -> None:
    approved = _question(id="b1-011", status="approved")
    again = _question(id="b1-011", question="Başka bir soru metni burada?")
    same_text = _question(
        id="b2-009", question=" bankam BEN istemeden kart limitimi yükseltebilir mi?"
    )

    assert _messages(again, existing=(approved,)) == ["id b1-011 is already used"]
    assert _messages(same_text, existing=(approved,)) == ["the same question as b1-011"]


def test_the_command_lists_problems_and_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    draft = tmp_path / "batch2.jsonl"
    bad = _question(evidence=[{"chunk": "5464:m9:f1", "quote": "uydurma alıntı"}])
    draft.write_text(bad.model_dump_json() + "\n", encoding="utf-8")
    chunks = tmp_path / "chunks.jsonl"
    chunks.write_text(
        "".join(c.model_dump_json() + "\n" for c in CHUNKS.values()), encoding="utf-8"
    )
    golden = tmp_path / "golden.jsonl"
    golden.write_text("", encoding="utf-8")
    args = [str(draft), "--chunks", str(chunks), "--golden", str(golden)]

    code = draft_cli.main(args)

    out = capsys.readouterr().out
    assert code == draft_cli.EXIT_PROBLEMS
    assert "b2-001: quote not found in 5464:m9:f1" in out
    assert "dogrudan 1" in out  # category counts, for the approval table

    draft.write_text(_question().model_dump_json() + "\n", encoding="utf-8")
    assert draft_cli.main(args) == draft_cli.EXIT_OK
