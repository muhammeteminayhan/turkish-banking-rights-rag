"""Text embedders. bge-m3 for the real index; a hashing embedder for tests and CI.

Both return float32 rows of unit length, so cosine similarity is a dot product. bge-m3
needs no query/document prefixes.
"""

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import numpy as np
from numpy.typing import NDArray

from finhak.textnorm import tr_casefold

Vectors = NDArray[np.float32]


class ModelLoadError(RuntimeError):
    """A model could not be loaded: sentence-transformers or the weights are missing."""


LOAD_HINT = "install the models extra (pip install -e .[models]) and download the model first"


@dataclass(frozen=True)
class ModelRef:
    name: str
    revision: str  # Hugging Face commit, pinned so the index can be rebuilt identically


BGE_M3 = ModelRef("BAAI/bge-m3", "5617a9f61b028005a4858fdac845db406aefb181")
EmbedderKind = Literal["bge-m3", "hashing"]


class Embedder(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def dim(self) -> int: ...

    def embed(self, texts: Sequence[str]) -> Vectors: ...


_WORD = re.compile(r"\w+")


class HashingEmbedder:
    """Bag of words and letter trigrams hashed into `dim` buckets. No model, deterministic."""

    def __init__(self, dim: int = 256) -> None:
        if dim <= 0:
            raise ValueError(f"dim must be positive, got {dim}")
        self._dim = dim

    @property
    def name(self) -> str:
        return f"hashing-{self._dim}"

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: Sequence[str]) -> Vectors:
        out = np.zeros((len(texts), self._dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for feature in self._features(text):
                digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
                bucket = int.from_bytes(digest[:4], "little") % self._dim
                out[row, bucket] += 1.0 if digest[4] & 1 else -1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return np.divide(out, norms, out=np.zeros_like(out), where=norms > 0)

    @staticmethod
    def _features(text: str) -> list[str]:
        words = _WORD.findall(tr_casefold(text))
        trigrams = [f"#{w[i : i + 3]}" for w in words for i in range(max(1, len(w) - 2))]
        return words + trigrams


class SentenceTransformerEmbedder:
    """bge-m3 through sentence-transformers; fp16 on a CUDA GPU, fp32 on CPU."""

    def __init__(
        self,
        model: ModelRef = BGE_M3,
        device: str | None = None,
        batch_size: int = 16,
        max_seq_length: int = 1024,
        show_progress: bool = False,
    ) -> None:
        try:
            import torch
            from sentence_transformers import SentenceTransformer

            self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
            kwargs: dict[str, Any] = (
                {"torch_dtype": torch.float16} if self._device == "cuda" else {}
            )
            self._model = SentenceTransformer(
                model.name, revision=model.revision, device=self._device, model_kwargs=kwargs
            )
        except (ImportError, OSError, ValueError) as exc:
            raise ModelLoadError(f"cannot load {model.name}: {exc}; {LOAD_HINT}") from exc
        self._model.max_seq_length = max_seq_length
        self._ref = model
        self._batch_size = batch_size
        self._show_progress = show_progress
        # sentence-transformers 6 renamed get_sentence_embedding_dimension.
        get_dim = getattr(self._model, "get_embedding_dimension", None) or (
            self._model.get_sentence_embedding_dimension
        )
        dim = get_dim()
        if dim is None:
            raise ValueError(f"{model.name} does not report an embedding dimension")
        self._dim = int(dim)

    @property
    def name(self) -> str:
        return f"{self._ref.name}@{self._ref.revision[:8]}"

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def device(self) -> str:
        return self._device

    def embed(self, texts: Sequence[str]) -> Vectors:
        if not texts:
            return np.zeros((0, self._dim), dtype=np.float32)
        vectors = self._model.encode(
            list(texts),
            batch_size=self._batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=self._show_progress,
        )
        return np.asarray(vectors, dtype=np.float32)


def make_embedder(
    kind: EmbedderKind, device: str | None = None, show_progress: bool = False
) -> Embedder:
    if kind == "hashing":
        return HashingEmbedder()
    return SentenceTransformerEmbedder(device=device, show_progress=show_progress)
