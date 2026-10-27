"""What the language model must return: an answer with citations, as strict JSON.

Every field is required and no extra keys are allowed, so the same JSON schema works for
Anthropic structured outputs and for Ollama's `format` (finhak.llm.base.json_schema).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_STRICT = ConfigDict(frozen=True, extra="forbid")


class CitationOut(BaseModel):
    model_config = _STRICT

    chunk_id: str = Field(description="Kaynağın kimliği, köşeli parantezde verildiği gibi")
    doc_id: str = Field(description="Kaynağın belge kimliği (ör. 6502, kart-yon)")
    madde: str | None = Field(description="Madde numarası, kaynakta yazıldığı gibi; yoksa null")
    fikra: int | None = Field(description="Fıkra numarası; yoksa null")
    quote: str = Field(description="Kaynak metinden birebir kopyalanmış alıntı")


class AnswerOut(BaseModel):
    """Field order matters: constrained decoding writes keys in this order, so the model
    decides scope and quotes its sources before it writes the answer."""

    model_config = _STRICT

    out_of_scope: bool = Field(description="Kaynaklar soruyu cevaplamıyorsa true")
    false_premise: bool = Field(description="Sorunun varsayımı kaynaklarla çelişiyorsa true")
    citations: list[CitationOut]
    answer: str = Field(description="Türkçe kısa cevap; yalnızca alıntılanan kaynaklara dayanır")
    confidence: Literal["high", "medium", "low"]
