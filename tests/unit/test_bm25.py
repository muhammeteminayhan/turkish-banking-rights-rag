import pytest

from chunk_factory import make_chunk
from finhak.retrieval.bm25 import Bm25Index, analyze

pytestmark = pytest.mark.unit


def test_snowball_analyzer_casefolds_turkish_letters_and_stems() -> None:
    assert analyze("Kredi KARTI aidatları İŞLETİM") == ("kredi", "kar", "aidat", "işlet")


def test_prefix_analyzer_keeps_the_first_five_letters() -> None:
    assert analyze("Kredi KARTI aidatları İŞLETİM", stemmer="prefix5") == (
        "kredi",
        "kartı",
        "aidat",
        "işlet",
    )


def test_prefix_analyzer_puts_inflected_forms_on_one_term() -> None:
    assert set(analyze("aidat aidatı aidatları aidatımı", stemmer="prefix5")) == {"aidat"}
    # Its limit: a short stem plus a suffix crosses the fifth letter.
    assert analyze("kartı kartları", stemmer="prefix5") == ("kartı", "kartl")


def test_stopwords_and_punctuation_are_dropped() -> None:
    assert analyze("Bu ve şu bir mi? Nasıl, nedir!") == ()


def test_numbers_are_kept() -> None:
    assert analyze("EFT 8.300 TL", stemmer="prefix5") == ("eft", "8", "300", "tl")


def test_circumflex_is_ignored() -> None:
    assert analyze("Usûl", stemmer="prefix5") == analyze("usul", stemmer="prefix5")


def _index(stemmer: str = "snowball") -> Bm25Index:
    chunks = [
        make_chunk("6502:m1:f1", "Mevduat hesapları zamanaşımına uğrar.", madde_title="Zamanaşımı"),
        make_chunk("5464:m10:f1", "Kart çıkaran kuruluş yıllık aidat talep edebilir.", madde="10"),
        make_chunk("6502:m22:f1", "Faiz oranı sözleşmede yazılır.", madde="22"),
        make_chunk("kart-yon:m5:f1", "Bu ücret sözleşmede yer alır.", madde_title="Üyelik ücreti"),
    ]
    return Bm25Index.from_chunks(chunks, stemmer=stemmer)  # type: ignore[arg-type]


def test_search_puts_the_matching_chunk_first() -> None:
    hits = _index().search("kart aidatı iadesi", k=3)

    assert hits[0].chunk_id == "5464:m10:f1"
    assert hits[0].score > 0


def test_article_titles_are_searchable() -> None:
    assert _index().search("üyelik", k=3)[0].chunk_id == "kart-yon:m5:f1"


def test_search_drops_chunks_with_no_matching_term_and_respects_k() -> None:
    index = _index(stemmer="prefix5")

    assert index.search("sözleşme faiz ücret", k=1) == index.search("sözleşme faiz ücret", k=4)[:1]
    assert [h.chunk_id for h in index.search("faiz", k=4)] == ["6502:m22:f1"]
    # prefix5 limit: "faizler" → "faizl" does not meet "faiz" (four letters).
    assert index.search("faizler", k=4) == []
    assert index.search("kripto borsası", k=4) == []


def test_empty_query_gives_nothing() -> None:
    assert _index().search("ve bir", k=5) == []


def test_unknown_stemmer_is_rejected() -> None:
    with pytest.raises(ValueError, match="stemmer"):
        analyze("kart", stemmer="porter")  # type: ignore[arg-type]
