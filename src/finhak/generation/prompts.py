"""The prompts. The system prompt is fixed (cache-friendly); passages and question go in the
user message, the question last."""

from collections.abc import Sequence

from finhak.generation.render import snapshot_note
from finhak.generation.verify import CitationError
from finhak.parsing.chunker import Chunk
from finhak.retrieval.direct_ref import DirectRef

SYSTEM_PROMPT = """\
Türk bankacılık ve tüketici mevzuatı hakkındaki soruları yalnızca sana verilen kaynak \
metinlere dayanarak cevaplıyorsun. Cevabın, kaynakları okuyamayan biri tarafından \
atıflar üzerinden kontrol edilecek.

Kurallar:
1. Yalnızca "Kaynaklar" bölümündeki metinleri kullan. Kendi bilgini, tahmini veya orada \
olmayan bir mevzuatı ekleme.
2. Her iddiayı en az bir atıfla destekle. chunk_id alanına kaynağın "chunk_id:" \
satırındaki değeri aynen yaz (ör. 6502:m22:f1; yalnızca belge kimliği değil). doc_id, \
madde ve fıkra değerlerini de o kaynağın satırından aynen kopyala; fıkra "null" ise null ver.
3. quote alanına kaynak metinden, iddiayı destekleyen bölümü birebir kopyala: en az \
birkaç kelime, kelime değiştirmeden, kısaltmadan, özetlemeden.
4. Kaynaklar soruyu cevaplamıyorsa out_of_scope true olsun, citations boş liste olsun ve \
answer alanında bunu tek cümleyle söyle.
5. Sorunun varsayımı kaynaklarla çelişiyorsa false_premise true yap ve cevapta varsayımı \
kaynakla düzelt.
6. Kaynaklar birbirleriyle çelişiyorsa ikisini de atıfla göster; hangisinin uygulanacağı \
kaynakta yazmıyorsa karar verme, bunu belirt.
7. Tutarları, oranları ve süreleri kaynakta yazdığı gibi ver; hesaplayıp yeni rakam üretme. \
Bir kaynağın Notlar bölümündeki dipnot, metindeki tutarın belirli bir tarihten itibaren \
geçerli güncel hâlini veriyorsa güncel tutarı ve o tarihi ver.
8. Kaynak bir şeyi yasaklıyorsa ("reddedilemez", "alınamaz", "artıramaz", "geçemez"), \
cevapta bunu ters çevirme: yasak olanı "yapılabilir" diye yazma.
9. Her hükmü yalnızca kendi konusu için kullan: konut finansmanına, kredi kartına veya \
mesafeli sözleşmeye ait bir kuralı başka bir ürüne uygulama.
10. Kişinin ne yapması gerektiğini değil, metnin ne dediğini anlat. Cevaba sorumluluk \
reddi, uyarı veya "hukuki tavsiye değildir" türünden bir cümle yazma.
11. Cevabı Türkçe, kısa ve sade yaz.
"""

# Eight passages of at most this length plus the instructions stay under ~6k tokens, inside
# Ollama's 8k context. Only a few annex tables are longer (chunk p95: 1,151 characters).
MAX_PASSAGE_CHARS = 1800
MAX_PROMPT_CHARS = 16000  # passages that do not fit are left out (and cannot be cited)
_KIND_NAMES = {"gecici": "geçici madde", "ek": "ek madde"}

INVALID_OUTPUT_RETRY = (
    "Önceki cevabın şemaya uygun geçerli JSON değildi. Aynı soruyu, istenen JSON şemasına "
    "uygun olarak yeniden cevapla."
)


def passage_block(chunk: Chunk) -> str:
    lines = [
        f"chunk_id: {chunk.id}",
        f"Belge: {chunk.doc_label}",
        f"doc_id: {chunk.doc_id} | madde: {chunk.madde or 'null'} | fıkra: {_fikra(chunk)}",
    ]
    if chunk.madde_kind in _KIND_NAMES:
        lines.append(f"madde türü: {_KIND_NAMES[chunk.madde_kind]}")
    if chunk.bents and chunk.unit == "bent":
        lines.append(f"bent: {', '.join(chunk.bents)}")
    if chunk.mulga:
        lines.append("Durum: MÜLGA (yürürlükten kaldırılmış hüküm; güncel kural olarak sunma)")
    if chunk.madde_title:
        lines.append(f"Başlık: {chunk.madde_title}")
    lines += [f"Sürüm: {snapshot_note(chunk)}", "Metin:", _cut(chunk.text)]
    if chunk.notes:
        lines += ["Notlar:", _cut("\n".join(chunk.notes))]
    return "\n".join(lines)


def _cut(text: str) -> str:
    """At most MAX_PASSAGE_CHARS of a passage; quotes are still checked on the full text."""
    if len(text) <= MAX_PASSAGE_CHARS:
        return text
    return text[:MAX_PASSAGE_CHARS].rsplit(" ", 1)[0] + " … [metin kısaltıldı]"


def build_prompt(
    question: str,
    chunks: Sequence[Chunk],
    unmatched: Sequence[DirectRef],
    budget: int = MAX_PROMPT_CHARS,
) -> tuple[str, list[Chunk]]:
    """The user message and the chunks it shows, best-ranked first, within `budget` chars."""
    blocks: list[str] = []
    shown: list[Chunk] = []
    used = len(question)
    for chunk in chunks:
        block = passage_block(chunk)
        if shown and used + len(block) > budget:
            break
        blocks.append(block)
        shown.append(chunk)
        used += len(block)
    parts = ["Kaynaklar:", *blocks]
    if unmatched:
        missing = ", ".join(ref.label for ref in unmatched)
        parts.append(f"Not: Sorudaki {missing} kaynaklarda bulunamadı; bunu cevapta belirt.")
    parts.append(f"Soru: {question}")
    return "\n\n".join(parts) + "\n", shown


def retry_message(errors: Sequence[CitationError]) -> str:
    listed = "\n".join(f"- {error.message}" for error in errors)
    return (
        f"Önceki cevabındaki atıflar doğrulanamadı:\n{listed}\n"
        "Yalnızca verilen kaynaklara dayanarak, aynı JSON şemasında düzeltilmiş cevabı ver."
    )


def _fikra(chunk: Chunk) -> str:
    if chunk.fikra is None:
        return "null"
    if chunk.fikra_last:
        value = f"{chunk.fikra}-{chunk.fikra_last} (bu aralıktan tek bir sayı yaz)"
    else:
        value = str(chunk.fikra)
    if chunk.fikra_inferred:  # the model wrote null for "not printed" in the first smoke run
        return (
            f"{value} (numara metinde yazmıyor, paragraflar sayılarak bulundu; "
            f"atıfta {chunk.fikra} yaz)"
        )
    return value
