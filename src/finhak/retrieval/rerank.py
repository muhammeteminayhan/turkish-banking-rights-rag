"""Cross-encoder reranking with bge-reranker-v2-m3."""

from collections.abc import Sequence
from typing import Any, Protocol

from finhak.index.embed import LOAD_HINT, ModelLoadError, ModelRef

BGE_RERANKER = ModelRef("BAAI/bge-reranker-v2-m3", "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e")


class Reranker(Protocol):
    def scores(self, query: str, passages: Sequence[str]) -> list[float]: ...


class CrossEncoderReranker:
    """Relevance in 0..1 (sigmoid of the model's logit); fp16 on a CUDA GPU."""

    def __init__(
        self,
        model: ModelRef = BGE_RERANKER,
        device: str | None = None,
        max_length: int = 1024,
        batch_size: int = 16,
    ) -> None:
        try:
            import torch
            from sentence_transformers import CrossEncoder

            self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
            kwargs: dict[str, Any] = (
                {"torch_dtype": torch.float16} if self._device == "cuda" else {}
            )
            self._model = CrossEncoder(
                model.name,
                revision=model.revision,
                device=self._device,
                max_length=max_length,
                model_kwargs=kwargs,
            )
        except (ImportError, OSError, ValueError) as exc:
            raise ModelLoadError(f"cannot load {model.name}: {exc}; {LOAD_HINT}") from exc
        self._batch_size = batch_size
        self.name = f"{model.name}@{model.revision[:8]}"

    def scores(self, query: str, passages: Sequence[str]) -> list[float]:
        if not passages:
            return []
        out = self._model.predict(
            [(query, p) for p in passages], batch_size=self._batch_size, show_progress_bar=False
        )
        return [float(x) for x in out]
