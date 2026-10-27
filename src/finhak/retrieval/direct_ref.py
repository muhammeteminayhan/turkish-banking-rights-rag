"""Explicit article citations in a question: "6502 sayılı Kanunun 22. maddesi", "TKHK m.22/3".

Matching runs on a folded copy of the question (lower case, ç→c ğ→g ı→i ö→o ş→s ü→u,
circumflex dropped) that has the same length as the NFC text, so questions typed without
Turkish letters match too and every match maps back to the original wording.

A citation needs both an article number and a document named right before it: nothing
but a short suffix or word may stand between them ("KVKK'nın 11. maddesi", "6502 sayılı
kanuna göre 22. madde"). "22. madde ne diyor?" and "sözleşmemin 7. maddesi" name no
document and give no reference; the caller falls back to ordinary search. A further
article joined by "ve"/"ile"/"," to a paired one shares its document ("TKHK madde 22 ve
madde 23"). Known limit: a bare second number ("madde 22 ve 23") is not taken, because it
cannot be told from an amount or a day count.
"""

import re
from dataclasses import dataclass
from typing import Literal, TypeVar

from finhak.textnorm import normalize_space

RefKind = Literal["madde", "gecici", "ek"]

_FOLD = str.maketrans("çğıöşüâîûÇĞIİÖŞÜÂÎÛ’", "cgiosuaiucgiiosuaiu'")

_K = r"kanun\w*"
_Y = r"yonetmeli\w*"
_T = r"tebli\w*"

# (doc_id, pattern on the folded text). Overlapping matches keep the shortest, so a
# specific name wins over a loose one that runs across it ("mevduat … Kart Yönetmeliği").
_DOCUMENTS: tuple[tuple[str, str], ...] = (
    ("6502", r"\b(?:tkhk|tkk)\b"),
    ("6502", rf"\btuketicinin\s+korunmasi\s+(?:hakkinda\s+)?{_K}"),
    ("6502", rf"\btuketici\s+{_K}"),
    ("5411", rf"\bbankacilik\s+{_K}"),
    ("5464", rf"\bbanka\s+kartlari\s+ve\s+kredi\s+kartlari\s+{_K}"),
    (
        "6493",
        r"\bodeme\s+(?:ve\s+menkul\s+kiymet\s+mutabakat\s+sistemleri,?\s+)?(?:odeme\s+)?"
        rf"hizmetleri\s+ve\s+elektronik\s+para\s+kuruluslari\s+(?:hakkinda\s+)?{_K}",
    ),
    ("6698", r"\bkvkk\b"),
    ("6698", rf"\bkisisel\s+verilerin\s+korunmasi\s+{_K}"),
    # Not a bare "talimat": "ödeme talimatım" is an everyday payment order.
    (
        "tcmb-ucret-talimat",
        r"\b(?:(?:tcmb|ucret\w*)\s+)?uygulama\s+talimat\w*|\b(?:tcmb|ucret\w*)\s+talimat\w*",
    ),
    ("tcmb-ucret-teblig", rf"\b2020/7\s+(?:sayili\s+)?{_T}"),
    (
        "tcmb-ucret-teblig",
        r"\b(?:finansal\s+tuketicilerden\s+alinacak\s+)?ucret\w*\s+"
        rf"(?:iliskin\s+usul\s+ve\s+esaslar\s+hakkinda\s+)?{_T}",
    ),
    ("tuketici-kredisi-yon", rf"\btuketici\s+kredisi\s+(?:sozlesmeleri\s+)?{_Y}"),
    (
        "kart-yon",
        rf"\b(?:banka\s+kartlari\s+ve\s+)?(?:kredi\s+)?kart\w*\s+(?:hakkinda\s+)?{_Y}",
    ),
    ("konut-finansmani-yon", rf"\bkonut\s+finansmani\s+(?:sozlesmeleri\s+)?{_Y}"),
    (
        "odeme-hizmetleri-yon",
        r"\bodeme\s+hizmetleri\s+(?:ve\s+elektronik\s+para\s+ihraci\s+"
        rf"(?:ile\s+odeme\s+hizmeti\s+saglayicilari\s+hakkinda\s+)?)?{_Y}",
    ),
    ("hakem-heyetleri-yon", rf"\b(?:tuketici\s+)?hakem\s+heyet\w*\s+{_Y}"),
    (
        "mesafeli-finansal-yon",
        rf"\b(?:finansal\s+hizmetlere\s+iliskin\s+)?mesafeli\s+(?:sozlesmeler\s+)?{_Y}",
    ),
    (
        "haksiz-sartlar-yon",
        rf"\b(?:tuketici\s+sozlesmelerindeki\s+)?haksiz\s+sartlar\s+(?:hakkinda\s+)?{_Y}",
    ),
    ("mevduat-yon", rf"\bmevduat\w*\s+(?:[\w,]+\s+){{0,24}}?{_Y}"),
    (
        "erisilebilirlik-yon",
        rf"\b(?:bankacilik\s+hizmetlerinin\s+)?erisilebilirli\w*\s+(?:dair\s+)?{_Y}",
    ),
    # A law number, with "sayılı Kanun…" when given, unless it is an amount or a duration.
    (
        "",
        r"\b(?P<law>6502|5411|5464|6493|6698)\b"
        r"(?!\s*(?:tl|lira\w*|gun\w*|ay|aylik|yil\w*|adet)\b)(?:\s+sayili)?(?:\s+kanun\w*)?",
    ),
)
_DOCUMENT_PATTERNS = tuple((doc_id, re.compile(p)) for doc_id, p in _DOCUMENTS)

_ORDINAL_WORDS = {
    "birinci": 1, "ikinci": 2, "ucuncu": 3, "dorduncu": 4, "besinci": 5, "altinci": 6,
    "yedinci": 7, "sekizinci": 8, "dokuzuncu": 9, "onuncu": 10, "on birinci": 11,
    "on ikinci": 12, "on ucuncu": 13, "on dorduncu": 14, "on besinci": 15,
}  # fmt: skip

_NUM = r"\d{1,3}(?!\d)(?:\s*/\s*[a-z]\b)?"
# "22.", "22 nci", "12'nci", "3 üncü" (folded "3 uncu"), "40 ıncı" (folded "40 inci").
_ORD = r"(?:\s*\.|\s*'?\s*(?:inci|nci|uncu|ncu|unci))?"
_KIND = r"(?:(?P<kind>gecici|ek)\s+)?"
_FIKRA_PHRASE = (
    r"(?:\s+(?:(?P<fnum>\d{1,2})"
    + _ORD
    + r"|(?P<fword>"
    + "|".join(sorted(_ORDINAL_WORDS, key=len, reverse=True)).replace(" ", r"\s+")
    + r"))\s+fikra\w*)?"
)
_AMOUNT = r"(?!\s*(?:tl|lira\w*)\b)"
# In order of preference when two matches overlap ("5. madde 100 TL" is article 5).
_MADDE_PATTERNS = (
    # "22. maddesi", "49 ve 50 nci maddeleri", "22 ila 24. maddeler", "geçici 1 inci
    # maddesinin üçüncü fıkrası"
    re.compile(
        rf"\b{_KIND}(?P<nums>{_NUM}{_ORD}(?:\s*(?:,|ve|ile|ila|-)\s*{_NUM}{_ORD})*)"
        rf"\s*madde\w*{_FIKRA_PHRASE}"
    ),
    # "madde 22", "md. 22/3", "m.22", "ek madde 1"
    re.compile(
        rf"\b{_KIND}(?:madde|md\.?|m\.)\s*(?P<num>{_NUM}){_AMOUNT}"
        rf"(?:\s*/\s*(?P<slash>\d{{1,2}})\b)?"
    ),
)
_NUMBER_OR_RANGE = re.compile(rf"(?P<number>{_NUM})|(?P<range>ila|-)")
_MAX_RANGE = 20  # "22 ila 24" expands; a longer span is probably not a citation list
_DOC_GAP = re.compile(r"[\s']*(?:\w{1,4}[\s']*)?")  # "'nın ", " göre ", "'nun "
_LIST_GAP = re.compile(r"\s*(?:,|ve|ile|veya)?\s*")
MAX_QUESTION_CHARS = 2000  # longer input is cut before matching (regex cost)


@dataclass(frozen=True)
class DirectRef:
    doc_id: str
    madde_kind: RefKind
    madde: str  # as in Chunk.madde: "22", "28/A"
    fikra: int | None
    matched: str  # the article part of the question, as written

    @property
    def label(self) -> str:
        kind = {"madde": "md.", "gecici": "geçici md.", "ek": "ek md."}[self.madde_kind]
        fikra = "" if self.fikra is None else f"/{self.fikra}"
        return f"{self.doc_id} {kind} {self.madde}{fikra}"


@dataclass(frozen=True)
class _Span:
    start: int
    end: int


@dataclass(frozen=True)
class _DocMention(_Span):
    doc_id: str


@dataclass(frozen=True)
class _MaddeMention(_Span):
    kind: RefKind
    numbers: tuple[str, ...]
    fikra: int | None


_S = TypeVar("_S", bound=_Span)


def find_direct_refs(question: str) -> tuple[DirectRef, ...]:
    text = normalize_space(question)[:MAX_QUESTION_CHARS]  # NFC, one space per run
    folded = _fold(text)
    documents = _document_mentions(folded)
    if not documents:
        return ()
    refs: list[DirectRef] = []
    for mention, doc_id in _paired(_madde_mentions(folded), documents, folded):
        for number in mention.numbers:
            ref = DirectRef(
                doc_id=doc_id,
                madde_kind=mention.kind,
                madde=number,
                fikra=mention.fikra,
                matched=text[mention.start : mention.end],
            )
            if all(_key(ref) != _key(seen) for seen in refs):
                refs.append(ref)
    return tuple(refs)


def _fold(text: str) -> str:
    translated = text.translate(_FOLD)
    # lower() can lengthen a few exotic characters; keep those as they are.
    return "".join(c.lower() if len(c.lower()) == 1 else c for c in translated)


def _key(ref: DirectRef) -> tuple[str, str, str, int | None]:
    return ref.doc_id, ref.madde_kind, ref.madde, ref.fikra


def _document_mentions(folded: str) -> list[_DocMention]:
    found = [
        _DocMention(m.start(), m.end(), doc_id or m.group("law"))
        for doc_id, pattern in _DOCUMENT_PATTERNS
        for m in pattern.finditer(folded)
    ]
    return sorted(_without_overlaps(found, prefer_short=True), key=lambda d: d.start)


def _madde_mentions(folded: str) -> list[_MaddeMention]:
    kept: list[_MaddeMention] = []
    for pattern in _MADDE_PATTERNS:
        found = [_mention(m) for m in pattern.finditer(folded)]
        kept += [m for m in _without_overlaps(found, prefer_short=False) if _free(m, kept)]
    return sorted(kept, key=lambda m: m.start)


def _mention(match: re.Match[str]) -> _MaddeMention:
    groups = match.groupdict()
    return _MaddeMention(
        match.start(),
        match.end(),
        kind=_madde_kind(groups.get("kind")),
        numbers=_numbers(groups.get("nums") or groups["num"]),
        fikra=_fikra(groups),
    )


def _numbers(listed: str) -> tuple[str, ...]:
    """ "49 ve 50" → 49, 50; "22 ila 24" / "22-24" → 22, 23, 24; "28/a" → 28/A."""
    numbers: list[str] = []
    pending_range = False
    for token in _NUMBER_OR_RANGE.finditer(listed):
        if token.group("range"):
            pending_range = bool(numbers)
            continue
        number = _madde_number(token.group("number"))
        if pending_range and numbers[-1].isdigit() and number.isdigit():
            first, last = int(numbers[-1]), int(number)
            if 0 < last - first <= _MAX_RANGE:
                numbers += [str(n) for n in range(first + 1, last)]
        numbers.append(number)
        pending_range = False
    return tuple(dict.fromkeys(numbers))


def _free(span: _Span, taken: list[_MaddeMention]) -> bool:
    return all(span.end <= other.start or span.start >= other.end for other in taken)


def _madde_kind(word: str | None) -> RefKind:
    return "gecici" if word == "gecici" else "ek" if word == "ek" else "madde"


def _madde_number(raw: str) -> str:
    number, _, letter = re.sub(r"\s+", "", raw).partition("/")
    return f"{number}/{letter.upper()}" if letter else number


def _fikra(groups: dict[str, str | None]) -> int | None:
    if groups.get("slash"):
        return int(groups["slash"] or 0)
    if groups.get("fnum"):
        return int(groups["fnum"] or 0)
    word = groups.get("fword")
    return _ORDINAL_WORDS[re.sub(r"\s+", " ", word)] if word else None


def _without_overlaps(spans: list[_S], prefer_short: bool) -> list[_S]:
    def length(span: _Span) -> int:
        return span.end - span.start

    order = sorted(spans, key=lambda s: (length(s) if prefer_short else -length(s), s.start))
    kept: list[_S] = []
    for span in order:
        if all(span.end <= other.start or span.start >= other.end for other in kept):
            kept.append(span)
    return kept


def _paired(
    mentions: list[_MaddeMention], documents: list[_DocMention], folded: str
) -> list[tuple[_MaddeMention, str]]:
    """Each article with the document named right before it, or with the document of the
    article it is listed after ("… madde 22 ve madde 23")."""
    paired: list[tuple[_MaddeMention, str]] = []
    previous: tuple[_MaddeMention, str] | None = None
    for mention in mentions:
        before = [d for d in documents if d.end <= mention.start]
        doc_id: str | None = None
        if before and _DOC_GAP.fullmatch(folded[before[-1].end : mention.start]):
            doc_id = before[-1].doc_id
        elif previous and _LIST_GAP.fullmatch(folded[previous[0].end : mention.start]):
            doc_id = previous[1]
        previous = (mention, doc_id) if doc_id else None
        if doc_id:
            paired.append((mention, doc_id))
    return paired
