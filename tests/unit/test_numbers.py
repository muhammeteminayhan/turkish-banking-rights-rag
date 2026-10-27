import pytest

from finhak.generation.numbers import numbers_in

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("otuz gün içinde", {"30"}),
        ("on beş gün", {"15"}),
        ("onbeş gün sonrasına kadar", {"15"}),
        ("yüzseksen gün süreyle", {"180"}),
        ("ikiyüzelli Türk Lirasına kadar", {"250"}),
        ("kalan vadesi otuz altı ayı aşmayan", {"36"}),
        ("yüzde birini, yüzde ikisini", {"1", "2"}),
        ("binde beşini geçemez", {"5"}),
        ("8.300 TL ve altı, 7,97 TL", {"8300", "7.97"}),
        ("6/1/2026 tarihinden itibaren", {"6", "1", "2026"}),
        ("06.01.2026 tarihinden itibaren", {"6", "1", "2026"}),  # a date, by its parts
        ("%40 ve üzeri", {"40"}),
        ("bir defaya mahsus", set()),  # "bir" alone is an article, not a count
        ("bir yıl içinde", {"1"}),  # … but next to a unit it is a number
    ],
)
def test_numbers_in_turkish_legal_text(text: str, expected: set[str]) -> None:
    assert numbers_in(text) == expected
