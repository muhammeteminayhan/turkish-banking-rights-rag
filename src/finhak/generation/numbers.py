"""Numbers in Turkish legal text, written as digits or as words.

Legal texts write most numbers as words ("otuz gün", "yüzde ikisini", "ikiyüzelli Türk
Lirası", "onbeş"), a model often answers with digits; both sides are reduced to canonical
digit strings ("30", "2", "250", "15", "8300", "7.97") so they can be compared.

"bir", "altı" and "yüz" are also ordinary words ("bir defa", "8.300 TL ve altı", "yüz"),
so on their own they count only when a unit follows ("bir yıl"). "yüzde"/"binde" mark a
percentage or a per-mille rate and are not numbers themselves.
"""

import re
from decimal import Decimal, InvalidOperation

from finhak.textnorm import tr_casefold

_UNITS = {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7,
          "sekiz": 8, "dokuz": 9}  # fmt: skip
_TENS = {"on": 10, "yirmi": 20, "otuz": 30, "kırk": 40, "elli": 50, "altmış": 60,
         "yetmiş": 70, "seksen": 80, "doksan": 90}  # fmt: skip
_SCALES = {"yüz": 100, "bin": 1000}
_MORPHEMES = sorted({**_UNITS, **_TENS, **_SCALES}.items(), key=lambda kv: -len(kv[0]))
_AMBIGUOUS = {"bir", "altı", "yüz"}
_RATE_PREFIXES = ("yüzde", "binde")
_UNIT_PREFIXES = ("gün", "ay", "yıl", "hafta", "saat", "dakika", "lira", "tl", "kuruş",
                  "adet", "taksit", "kat")  # fmt: skip

_DIGITS = re.compile(r"\d+(?:[.,]\d+)*")
_TOKEN = re.compile(r"\d+(?:[.,]\d+)*|[^\W\d_]+")  # digit groups and words, in text order


_DATE = re.compile(r"\d{1,2}[./]\d{1,2}[./]\d{4}")


def numbers_in(text: str) -> set[str]:
    folded = tr_casefold(text)
    digits: set[str] = set()
    for raw in _DIGITS.findall(folded):
        # "06.01.2026" is a date (compared by day, month, year), not one decimal number
        parts = re.split(r"[./]", raw) if _DATE.fullmatch(raw) else [raw]
        digits.update(_canonical(part) for part in parts)
    return digits | _word_numbers(folded)


def _canonical(raw: str) -> str:
    if "," in raw:  # decimal comma; dots group thousands
        whole, _, fraction = raw.rpartition(",")
        raw = f"{whole.replace('.', '')}.{fraction}"
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
        raw = raw.replace(".", "")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return raw
    return str(value.to_integral()) if value == value.to_integral() else str(value.normalize())


def _word_numbers(folded: str) -> set[str]:
    tokens = _TOKEN.findall(folded)
    found: set[str] = set()
    current: list[tuple[str, int]] = []
    after_rate = False  # "yüzde birini": a word after a rate word is a number
    for index, token in enumerate(tokens):
        is_rate = token.startswith(_RATE_PREFIXES)  # before splitting: "yüzde" ≠ yüz + de
        parts, rest = ([], token) if token[0].isdigit() or is_rate else _split(token)
        if not parts:
            _flush(current, found, tokens, index, after_rate)
            current, after_rate = [], is_rate
            continue
        current += parts
        if rest:  # an inflected number ("birini", "otuzu") ends here
            _flush(current, found, tokens, index + 1, after_rate)
            current, after_rate = [], False
    _flush(current, found, tokens, len(tokens), after_rate)
    return found


def _split(word: str) -> tuple[list[tuple[str, int]], str]:
    """Greedy split into number morphemes: "ikiyüzelli" → iki, yüz, elli; "birini" → bir + "ini"."""
    parts: list[tuple[str, int]] = []
    rest = word
    while rest:
        match = next(((m, v) for m, v in _MORPHEMES if rest.startswith(m)), None)
        if match is None:
            break
        parts.append(match)
        rest = rest[len(match[0]) :]
    return parts, rest


def _flush(
    current: list[tuple[str, int]],
    found: set[str],
    tokens: list[str],
    next_index: int,
    after_rate: bool,
) -> None:
    if not current:
        return
    alone_and_ambiguous = len(current) == 1 and current[0][0] in _AMBIGUOUS
    unit_follows = next_index < len(tokens) and tokens[next_index].startswith(_UNIT_PREFIXES)
    if not alone_and_ambiguous or unit_follows or after_rate:
        found.add(str(_value([value for _, value in current])))


def _value(values: list[int]) -> int:
    total, current = 0, 0
    for value in values:
        if value == 100:
            current = (current or 1) * 100
        elif value == 1000:
            total += (current or 1) * 1000
            current = 0
        else:
            current += value
    return total + current
