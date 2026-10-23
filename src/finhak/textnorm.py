"""Turkish-aware text normalisation shared by ingestion, parsing and retrieval."""

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
# Python's str.lower() maps "I" to "i" and "İ" to "i̇"; Turkish needs I→ı and İ→i.
_TURKISH_UPPER_I = str.maketrans({"I": "ı", "İ": "i"})
_CIRCUMFLEX = str.maketrans({"â": "a", "î": "i", "û": "u"})


def normalize_space(text: str) -> str:
    """Compose characters (NFC), collapse every whitespace run (incl. NBSP) and trim."""
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", text)).strip()


def tr_casefold(text: str) -> str:
    """Case- and circumflex-insensitive form for comparing Turkish strings."""
    composed = normalize_space(text)
    lowered = composed.translate(_TURKISH_UPPER_I).lower()
    return lowered.translate(_CIRCUMFLEX)
