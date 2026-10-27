import pytest

from chunk_factory import make_chunk
from finhak.generation.schema import AnswerOut, CitationOut
from finhak.generation.verify import verify_answer

pytestmark = pytest.mark.unit

RETRIEVED = [
    make_chunk(
        "6502:m22:f2",
        "Kredi kartı sözleşmeleri, ödemenin üç aydan daha uzun süre ertelenmesi hâlinde\n"
        "tüketici kredisi sözleşmesi olarak değerlendirilir.",
        madde="22",
        fikra=2,
    ),
    make_chunk(
        "5411:m2:f2",
        "Bu Kanun, Türkiye'de kurulu bankaları kapsar.",
        madde="2",
        fikra=2,
        fikra_inferred=True,
    ),
    make_chunk(
        "tcmb-ucret-talimat:s9:bc",
        "EFT işlemlerinden alınacak ücret …",
        madde="9",
        madde_kind=None,
        unit="bent",
        fikra=None,
        bents=("c",),
        notes=(
            "[Dipnot 1] 6/1/2026 tarihinden itibaren; EFT işlemlerinden alınabilecek azami ücret",
        ),
    ),
]


def _citation(**fields: object) -> CitationOut:
    data: dict[str, object] = {
        "chunk_id": "6502:m22:f2",
        "doc_id": "6502",
        "madde": "22",
        "fikra": 2,
        "quote": "ödemenin üç aydan daha uzun süre ertelenmesi",
    }
    return CitationOut.model_validate({**data, **fields})


def _answer(*citations: CitationOut, out_of_scope: bool = False) -> AnswerOut:
    return AnswerOut(
        answer="Kaynak bu durumu düzenler.",  # no numbers: the number check stays quiet
        citations=list(citations),
        out_of_scope=out_of_scope,
        false_premise=False,
        confidence="high",
    )


def _kinds(answer: AnswerOut) -> list[str]:
    return [e.kind for e in verify_answer(answer, RETRIEVED).errors]


def test_a_correct_citation_passes() -> None:
    report = verify_answer(_answer(_citation()), RETRIEVED)

    assert report.ok
    assert [c.id for c in report.cited_chunks] == ["6502:m22:f2"]


def test_the_quote_may_differ_in_case_whitespace_and_line_breaks() -> None:
    quote = (
        "KREDİ KARTI sözleşmeleri,   ödemenin üç aydan daha uzun süre ertelenmesi hâlinde tüketici"
    )

    assert _kinds(_answer(_citation(quote=quote))) == []


def test_a_quote_from_a_footnote_counts() -> None:
    citation = _citation(
        chunk_id="tcmb-ucret-talimat:s9:bc",
        doc_id="tcmb-ucret-talimat",
        madde="9",
        fikra=None,
        quote="6/1/2026 tarihinden itibaren; EFT işlemlerinden alınabilecek azami ücret",
    )

    assert _kinds(_answer(citation)) == []


@pytest.mark.parametrize(
    ("fields", "kind"),
    [
        ({"chunk_id": "6502:m99:f1"}, "unknown_chunk"),  # not among the retrieved chunks
        ({"doc_id": "5464"}, "doc_mismatch"),  # invented document
        ({"madde": "23"}, "madde_mismatch"),  # invented article
        ({"fikra": 3}, "fikra_mismatch"),
        ({"quote": "ödemenin altı aydan daha uzun süre ertelenmesi"}, "quote_not_found"),
        ({"quote": "kredi"}, "quote_too_short"),
    ],
)
def test_each_kind_of_bad_citation_is_caught(fields: dict[str, object], kind: str) -> None:
    assert _kinds(_answer(_citation(**fields))) == [kind]


def test_an_answer_needs_a_citation_unless_out_of_scope() -> None:
    assert _kinds(_answer()) == ["no_citations"]
    assert _kinds(_answer(out_of_scope=True)) == []


def test_an_out_of_scope_answer_must_not_cite() -> None:
    assert _kinds(_answer(_citation(), out_of_scope=True)) == ["citation_when_out_of_scope"]


def test_the_madde_is_compared_without_formatting_differences() -> None:
    chunk = make_chunk(
        "kart-yon:m28A:f1", "İntibak hükmü burada yer alır ve uygulanır.", madde="28/A"
    )
    citation = _citation(
        chunk_id="kart-yon:m28A:f1",
        doc_id="kart-yon",
        madde="28A",
        fikra=1,
        quote="İntibak hükmü burada yer alır",
    )

    assert verify_answer(_answer(citation), [chunk]).ok


def test_errors_say_what_is_wrong_for_the_retry_prompt() -> None:
    (error,) = verify_answer(_answer(_citation(madde="23")), RETRIEVED).errors

    assert "6502:m22:f2" in error.message
    assert "22" in error.message


def test_the_shown_quote_is_the_source_span_not_the_models_spelling() -> None:
    quote = "KREDİ KARTI   sözleşmeleri, ödemenin üç aydan"

    report = verify_answer(_answer(_citation(quote=quote)), RETRIEVED)

    assert report.quotes == ("Kredi kartı sözleşmeleri, ödemenin üç aydan",)


def test_a_quote_may_not_run_from_the_text_into_the_notes() -> None:
    chunk = make_chunk("6502:m5:f1", "Metnin son cümlesi burada biter.", madde="5",
                       notes=("(Değişik:RG-1/1/2020-12345) not metni",))  # fmt: skip
    citation = _citation(chunk_id="6502:m5:f1", madde="5", fikra=1,
                         quote="burada biter. (Değişik:RG-1/1/2020-12345)")  # fmt: skip

    assert [e.kind for e in verify_answer(_answer(citation), [chunk]).errors] == ["quote_not_found"]


@pytest.mark.parametrize(
    ("answer", "flagged"),
    [
        ("Üç aydan uzun ertelemede tüketici kredisi sayılır.", ()),
        ("3 aydan uzun ertelemede tüketici kredisi sayılır.", ()),  # "üç" in the source
        ("6502 sayılı Kanunun 22/2 hükmüne göre üç aydan uzun erteleme.", ()),  # the label
        ("6 aydan uzun ertelemede tüketici kredisi sayılır.", ("6",)),
        ("5411 md. 73 uyarınca faiz %5 artırılabilir.", ("5", "73", "5411")),
    ],
)
def test_numbers_that_no_cited_text_contains_are_an_error(
    answer: str, flagged: tuple[str, ...]
) -> None:
    reply = _answer(_citation()).model_copy(update={"answer": answer})

    report = verify_answer(reply, RETRIEVED)

    assert report.unsupported_numbers == flagged
    assert report.ok is (not flagged)
    if flagged:
        assert [e.kind for e in report.errors] == ["unsupported_number"]
        assert all(n in report.errors[0].message for n in flagged)


def test_numbers_from_the_question_are_not_flagged() -> None:
    reply = _answer(_citation()).model_copy(update={"answer": "5.000 TL için de geçerlidir."})

    report = verify_answer(reply, RETRIEVED, question="5.000 TL EFT yapacağım")

    assert report.ok


def test_an_empty_answer_is_an_error() -> None:
    reply = _answer(_citation()).model_copy(update={"answer": "  "})

    assert [e.kind for e in verify_answer(reply, RETRIEVED).errors] == ["empty_answer"]


@pytest.mark.parametrize(("cited", "ok"), [("28A", True), ("28/a", True), ("2/8", False)])
def test_madde_numbers_keep_their_letters_and_slashes_apart(cited: str, ok: bool) -> None:
    chunk = make_chunk("kart-yon:m28A:f1", "İntibak hükmü burada yer alır ve uygulanır.",
                       madde="28/A")  # fmt: skip
    citation = _citation(chunk_id="kart-yon:m28A:f1", doc_id="kart-yon", madde=cited, fikra=1,
                         quote="İntibak hükmü burada yer alır")  # fmt: skip

    assert verify_answer(_answer(citation), [chunk]).ok is ok


def test_the_quote_length_floor_is_inclusive() -> None:
    from finhak.generation.verify import MIN_QUOTE_CHARS

    exact = "ödemenin üç aydan daha uzun"[:MIN_QUOTE_CHARS]

    assert len(exact) == MIN_QUOTE_CHARS
    assert _kinds(_answer(_citation(quote=exact))) == []
    assert _kinds(_answer(_citation(quote=exact[:-1]))) == ["quote_too_short"]
