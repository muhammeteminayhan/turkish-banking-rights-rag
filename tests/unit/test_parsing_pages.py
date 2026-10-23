"""Best-effort PDF page lookup and the independent article count used by the parse report."""

import pytest

from finhak.parsing.pages import PageIndex, compact, count_madde_headings

pytestmark = pytest.mark.unit


def test_compact_ignores_case_spacing_punctuation_and_circumflex() -> None:
    assert compact("MADDE 3- (1) Bu  Kanunun\nuygulanmasında;") == compact(
        "madde 3 – (1) bu kanunun uygulanmasında"
    )


def test_compact_maps_turkish_dotted_capital_i() -> None:
    assert compact("İŞLEM") == "işlem"


def test_page_is_found_for_text_starting_on_that_page() -> None:
    index = PageIndex(
        ["Birinci sayfa metni.", "MADDE 3- (1) Bu Kanunun uygulanmasında; a) Bakan: Gümrük ve"]
    )

    assert index.locate("Bu Kanunun uygulanmasında;\na) Bakan: Gümrük") == 2


def test_text_split_across_pages_is_found_on_its_first_page() -> None:
    index = PageIndex(["… sonu: Bu Kanunun uygula", "nmasında; a) Bakan …"])

    assert index.locate("Bu Kanunun uygulanmasında; a) Bakan") == 1


def test_lookup_prefers_pages_at_or_after_the_previous_hit() -> None:
    index = PageIndex(["Yürürlük tarihi.", "Ara metin.", "Yürürlük tarihi."])

    assert index.locate("Yürürlük tarihi.", start=2) == 3


def test_unknown_text_has_no_page() -> None:
    assert PageIndex(["a b c"]).locate("bambaşka bir metin burada") is None


def test_count_madde_headings_counts_every_article_kind() -> None:
    text = (
        "MADDE 1- (1) Bir.\n"
        "Madde 2 — İki. Madde 5 kapsamında değil.\n"
        "GEÇİCİ MADDE 1 – (1) Geçici.\n"
        "Geçici Madde 32 [71] – (Ek:17/7/2019-7186/17 md.)\n"
        "MADDE 28/A – (1) Harfli.\n"
        "Geçici Madde 32    25/12/2025\n"
    )

    assert count_madde_headings(text) == 5
