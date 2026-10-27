"""The text of a chunk as the retrievers and the reranker see it."""

from finhak.parsing.chunker import Chunk

_KIND_LABELS = {"madde": "Madde", "gecici": "Geçici Madde", "ek": "Ek Madde", None: "Madde"}


def madde_label(chunk: Chunk) -> str | None:
    """ "Madde 22", "Geçici Madde 1", "Madde 9 (c)" for a talimat bent; None for annexes."""
    if chunk.madde is None:
        return None
    label = f"{_KIND_LABELS[chunk.madde_kind]} {chunk.madde}"
    if chunk.unit == "bent" and chunk.bents:
        label += f" ({', '.join(chunk.bents)})"
    return label


def heading(chunk: Chunk) -> str:
    """Document label, article and article title: what a reader scans first."""
    parts = [chunk.doc_label, madde_label(chunk), chunk.madde_title]
    return " — ".join(part for part in parts if part)


def passage(chunk: Chunk) -> str:
    """Heading, text and resolved notes (talimat footnotes carry the current fee caps)."""
    return "\n".join([heading(chunk), chunk.text, *chunk.notes])
