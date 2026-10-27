import pytest

from finhak.retrieval.direct_ref import DirectRef, find_direct_refs

pytestmark = pytest.mark.unit


def _refs(query: str) -> list[tuple[str, str, str, int | None]]:
    return [(r.doc_id, r.madde_kind, r.madde, r.fikra) for r in find_direct_refs(query)]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        # Law number + "sayılı" + ordinal article, in the usual spellings.
        ("6502 sayılı Kanunun 22. maddesi neyi düzenliyor?", [("6502", "madde", "22", None)]),
        ("6502 sayılı kanunun 22 nci maddesi", [("6502", "madde", "22", None)]),
        ("6502 sayılı Kanun'un 3 üncü maddesine göre", [("6502", "madde", "3", None)]),
        ("6698 sayılı Kanunun 11 inci maddesi", [("6698", "madde", "11", None)]),
        ("6493 sayılı Kanunun 12'nci maddesi", [("6493", "madde", "12", None)]),
        ("5464 m.10", [("5464", "madde", "10", None)]),
        # Abbreviations and short forms.
        ("TKHK m.22", [("6502", "madde", "22", None)]),
        ("TKK md. 22/3 ne diyor", [("6502", "madde", "22", 3)]),
        ("KVKK 11. madde hangi hakları sayıyor?", [("6698", "madde", "11", None)]),
        # Full names, inflected.
        (
            "Tüketicinin Korunması Hakkında Kanun'un 48 inci maddesi",
            [("6502", "madde", "48", None)],
        ),
        ("Bankacılık Kanunu madde 73/4", [("5411", "madde", "73", 4)]),
        (
            "5411 sayılı Bankacılık Kanunu'nun 73 üncü maddesinin dördüncü fıkrası",
            [("5411", "madde", "73", 4)],
        ),
        ("6502 sayılı Kanunun 22 nci maddesinin 3. fıkrası", [("6502", "madde", "22", 3)]),
        # Regulations, the communiqué and the TCMB instruction.
        (
            "Tüketici Kredisi Sözleşmeleri Yönetmeliği 5. madde",
            [("tuketici-kredisi-yon", "madde", "5", None)],
        ),
        ("tuketici kredisi yonetmeligi 5. madde", [("tuketici-kredisi-yon", "madde", "5", None)]),
        (
            "Banka Kartları ve Kredi Kartları Hakkında Yönetmeliğin 28/A maddesi",
            [("kart-yon", "madde", "28/A", None)],
        ),
        ("Kart Yönetmeliği 10. madde", [("kart-yon", "madde", "10", None)]),
        (
            "Konut Finansmanı Sözleşmeleri Yönetmeliğinin 8 inci maddesi",
            [("konut-finansmani-yon", "madde", "8", None)],
        ),
        (
            "Tüketici Hakem Heyetleri Yönetmeliği madde 6",
            [("hakem-heyetleri-yon", "madde", "6", None)],
        ),
        ("Ödeme Hizmetleri Yönetmeliği 40. madde", [("odeme-hizmetleri-yon", "madde", "40", None)]),
        (
            "Finansal Hizmetlere İlişkin Mesafeli Sözleşmeler Yönetmeliği 9 uncu madde",
            [("mesafeli-finansal-yon", "madde", "9", None)],
        ),
        ("Haksız Şartlar Yönetmeliği 5 inci madde", [("haksiz-sartlar-yon", "madde", "5", None)]),
        ("Mevduat Yönetmeliği 6. madde", [("mevduat-yon", "madde", "6", None)]),
        ("Erişilebilirlik Yönetmeliği madde 4", [("erisilebilirlik-yon", "madde", "4", None)]),
        ("Ücret Tebliği 7. madde", [("tcmb-ucret-teblig", "madde", "7", None)]),
        ("2020/7 sayılı Tebliğin 9 uncu maddesi", [("tcmb-ucret-teblig", "madde", "9", None)]),
        ("Uygulama Talimatının 9. maddesi", [("tcmb-ucret-talimat", "madde", "9", None)]),
        # Temporary and additional articles.
        ("6502 sayılı Kanunun geçici 1 inci maddesi", [("6502", "gecici", "1", None)]),
        ("Bankacılık Kanunu ek madde 1", [("5411", "ek", "1", None)]),
        ("Bankacılık Kanunu geçici madde 2", [("5411", "gecici", "2", None)]),
        # Several articles, several documents.
        (
            "6502 sayılı Kanunun 49 ve 50 nci maddeleri",
            [("6502", "madde", "49", None), ("6502", "madde", "50", None)],
        ),
        (
            "KVKK m.11 ile TKHK m.22 arasındaki fark",
            [("6698", "madde", "11", None), ("6502", "madde", "22", None)],
        ),
    ],
)
def test_finds_article_references(
    query: str, expected: list[tuple[str, str, str, int | None]]
) -> None:
    assert _refs(query) == expected


@pytest.mark.parametrize(
    "query",
    [
        "Kredi kartı aidatımı geri alabilir miyim?",
        "22. madde ne diyor?",  # no document named
        "Kanunun 5. maddesi",  # which law?
        "Yönetmelikte bu konuda bir madde var mı?",
        "Tüketici kredisinde erken ödeme indirimi nasıl hesaplanır?",
        "6502 TL kredi çektim, 3. taksidi ödemedim",
        "KVKK kapsamında hangi haklarım var?",  # a document but no article
    ],
)
def test_ignores_questions_without_a_specific_article(query: str) -> None:
    assert find_direct_refs(query) == ()


@pytest.mark.parametrize(
    "query",
    [
        # Everyday words that look like document names.
        "Otomatik ödeme talimatımı sözleşmenin 3. maddesine göre iptal ettim",
        # An article of the customer's own contract, with a law named later on.
        "Kredi sözleşmemin 7. maddesinde yazan faiz, Tüketici Kanunu'na uygun mu?",
        # A document named far before the article, and another one after it.
        "KVKK hakkında soruyorum, 10. madde Kart Yönetmeliği",
        # Amounts that are law numbers.
        "6698 liralık borç için 3. maddeye göre işlem yapıldı",
        "6502 lirayı geri istedim, 4. maddesi ne diyor",
    ],
)
def test_ignores_article_numbers_not_tied_to_a_named_document(query: str) -> None:
    assert find_direct_refs(query) == ()


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("6502 sayılı Kanunun 5. madde 100 TL", [("6502", "madde", "5", None)]),
        ("6502 sayılı kanuna göre 22. madde", [("6502", "madde", "22", None)]),
        (
            "Tüketici Hakem Heyeti Yönetmeliği madde 6",
            [("hakem-heyetleri-yon", "madde", "6", None)],
        ),
        (
            "Ücret Tebliği Uygulama Talimatının 9. maddesi",
            [("tcmb-ucret-talimat", "madde", "9", None)],
        ),
        (
            "TKHK madde 22 ve madde 23",
            [("6502", "madde", "22", None), ("6502", "madde", "23", None)],
        ),
    ],
)
def test_more_reference_shapes(
    query: str, expected: list[tuple[str, str, str, int | None]]
) -> None:
    assert _refs(query) == expected


@pytest.mark.parametrize(
    "query",
    ["6502 sayılı Kanunun 22 ila 24. maddeleri", "6502 sayılı Kanunun 22-24 üncü maddeleri"],
)
def test_article_ranges_are_expanded(query: str) -> None:
    assert [r.madde for r in find_direct_refs(query)] == ["22", "23", "24"]


def test_long_runs_of_whitespace_are_collapsed() -> None:
    assert _refs("TKHK" + " " * 8000 + "m.5") == [("6502", "madde", "5", None)]


def test_repeated_reference_is_returned_once() -> None:
    assert _refs("TKHK m.22 ve yine TKHK m.22") == [("6502", "madde", "22", None)]


def test_reference_keeps_the_matched_text() -> None:
    (ref,) = find_direct_refs("Lütfen 5464 sayılı Kanunun 10 uncu maddesini açıkla")

    assert isinstance(ref, DirectRef)
    assert ref.label == "5464 md. 10"
    assert "10 uncu madde" in ref.matched
