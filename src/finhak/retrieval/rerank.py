"""Cross-encoder reranking with bge-reranker-v2-m3."""

from collections.abc import Sequence
from typing import Any, Protocol

from finhak.index.embed import DEVICE_HINT, LOAD_HINT, ModelLoadError, ModelRef

BGE_RERANKER = ModelRef("BAAI/bge-reranker-v2-m3", "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e")
GPU_BATCH_SIZE = 16
# Small length-sorted batches pad less: 30 candidates took 4.9 s instead of 7.3 s on the CPU.
CPU_BATCH_SIZE = 4


class Reranker(Protocol):
    def scores(self, query: str, passages: Sequence[str]) -> list[float]: ...


class CrossEncoderReranker:
    """Relevance in 0..1 (sigmoid of the model's logit); fp16 on a CUDA GPU."""

    def __init__(
        self,
        model: ModelRef = BGE_RERANKER,
        device: str | None = None,
        max_length: int = 1024,
        batch_size: int | None = None,
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
        except (RuntimeError, AssertionError) as exc:  # no CUDA in torch, or the GPU is full
            raise ModelLoadError(
                f"cannot load {model.name} on {device or 'the default device'}: {exc}; "
                f"{DEVICE_HINT}"
            ) from exc
        self._batch_size = batch_size or (
            GPU_BATCH_SIZE if self._device == "cuda" else CPU_BATCH_SIZE
        )
        self.name = f"{model.name}@{model.revision[:8]}"

    def scores(self, query: str, passages: Sequence[str]) -> list[float]:
        if not passages:
            return []
        # Shortest first: a batch is padded to its longest pair, so batches of similar length
        # waste less work. Same scores up to float rounding (2e-9 on the CPU).
        order = sorted(range(len(passages)), key=lambda i: len(passages[i]))
        out = self._model.predict(
            [(query, passages[i]) for i in order],
            batch_size=self._batch_size,
            show_progress_bar=False,
        )
        by_index = dict(zip(order, out, strict=True))
        return [float(by_index[i]) for i in range(len(passages))]
