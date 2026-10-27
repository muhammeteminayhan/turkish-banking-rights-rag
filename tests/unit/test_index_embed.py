import numpy as np
import pytest

from chunk_factory import make_chunk
from finhak.index.embed import HashingEmbedder
from finhak.index.passages import heading, passage

pytestmark = pytest.mark.unit


def test_hashing_embedder_is_deterministic_and_unit_length() -> None:
    embedder = HashingEmbedder(dim=64)

    first = embedder.embed(["kredi kartı yıllık aidatı", "mevduat zamanaşımı"])
    second = embedder.embed(["kredi kartı yıllık aidatı", "mevduat zamanaşımı"])

    assert first.shape == (2, 64)
    assert first.dtype == np.float32
    np.testing.assert_array_equal(first, second)
    np.testing.assert_allclose(np.linalg.norm(first, axis=1), 1.0, rtol=1e-5)


def test_hashing_embedder_puts_overlapping_texts_closer() -> None:
    query, near, far = HashingEmbedder(dim=256).embed(
        ["kart aidatı", "yıllık kart aidatı ücreti", "mevduat zamanaşımı süresi"]
    )

    assert float(query @ near) > float(query @ far)


def test_hashing_embedder_handles_text_without_words() -> None:
    (vector,) = HashingEmbedder(dim=8).embed(["?!"])

    assert not np.isnan(vector).any()


def test_hashing_embedder_rejects_a_bad_dimension() -> None:
    with pytest.raises(ValueError, match="dim"):
        HashingEmbedder(dim=0)


def test_heading_names_document_article_and_title() -> None:
    chunk = make_chunk("6502:m22:f1", "metin", madde="22", madde_title="Faiz")

    assert heading(chunk) == "6502 sayılı Tüketicinin Korunması Hakkında Kanun — Madde 22 — Faiz"


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"madde": "1", "madde_kind": "gecici"}, "Geçici Madde 1"),
        ({"madde": "1", "madde_kind": "ek"}, "Ek Madde 1"),
        ({"madde": "9", "madde_kind": None, "unit": "bent", "bents": ("c",)}, "Madde 9 (c)"),
        ({"madde": None, "madde_kind": None, "unit": "ek", "fikra": None}, None),
    ],
)
def test_heading_labels_other_article_kinds(
    fields: dict[str, object], expected: str | None
) -> None:
    chunk = make_chunk("tcmb-ucret-talimat:s9:bc", "metin", madde_title="Başlık", **fields)

    parts = heading(chunk).split(" — ")
    assert parts[0] == chunk.doc_label
    assert parts[-1] == "Başlık"
    assert (parts[1] if len(parts) == 3 else None) == expected


def test_passage_adds_text_and_notes_under_the_heading() -> None:
    chunk = make_chunk(
        "tcmb-ucret-talimat:s9:bc",
        "EFT işlemlerinden alınacak ücret …",
        madde="9",
        madde_kind=None,
        unit="bent",
        bents=("c",),
        notes=("[Dipnot 1] 6/1/2026 tarihinden itibaren …",),
    )

    assert passage(chunk).split("\n") == [
        heading(chunk),
        "EFT işlemlerinden alınacak ücret …",
        "[Dipnot 1] 6/1/2026 tarihinden itibaren …",
    ]
