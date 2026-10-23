import pytest

from finhak.textnorm import normalize_space, tr_casefold

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("İSTANBUL", "istanbul"),
        ("IŞIK", "ışık"),
        ("USÛL VE ESASLAR", "usul ve esaslar"),
        ("Usûl ve Esaslar", "usul ve esaslar"),
        ("KÂR PAYI", "kar payı"),
    ],
)
def test_tr_casefold_handles_dotted_dotless_i_and_circumflex(raw: str, expected: str) -> None:
    assert tr_casefold(raw) == expected


def test_tr_casefold_makes_upper_case_page_title_equal_to_title_case() -> None:
    page = "FİNANSAL TÜKETİCİLERDEN ALINACAK ÜCRETLERE İLİŞKİN USÛL VE ESASLAR HAKKINDA TEBLİĞ"
    curated = "Finansal Tüketicilerden Alınacak Ücretlere İlişkin Usûl ve Esaslar Hakkında Tebliğ"
    assert tr_casefold(page) == tr_casefold(curated)


def test_tr_casefold_handles_decomposed_input() -> None:
    # "I" followed by COMBINING DOT ABOVE is the decomposed (NFD) spelling of "İ".
    assert tr_casefold("I\u0307STANBUL") == "istanbul"


def test_normalize_space_collapses_nbsp_tabs_and_newlines() -> None:
    assert normalize_space("  a\xa0 b\n\tc ") == "a b c"


def test_normalize_space_composes_characters() -> None:
    assert normalize_space("Resmi\u0302 Gazete") == "Resmî Gazete"
