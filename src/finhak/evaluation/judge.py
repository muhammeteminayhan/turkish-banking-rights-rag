"""Scores end-to-end answers against the approved golden answers (M5).

Refusals, withheld answers and errors are scored by rule. Only answers that reached the user
go to a judge model, which compares them with the expected answer and its evidence quotes,
not with its own knowledge of the law. Any provider can judge: a local Ollama model or a free
API tier.
"""

import hashlib
import json
import logging
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence, Set
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from finhak.evaluation.golden import GoldenQuestion
from finhak.evaluation.smoke import SmokeRow
from finhak.generation.render import DISCLAIMER
from finhak.llm.base import (
    ChatMessage,
    LLMError,
    LLMOutputError,
    LLMProvider,
    LLMRateLimited,
    LLMUnavailable,
    json_schema,
)

logger = logging.getLogger("finhak.judge")

JUDGE_ATTEMPTS = 2  # an invalid verdict is asked again once
RULE = "rule"

Outcome = Literal["dogru", "kismen", "yanlis", "dogru_red", "yersiz_red", "geri_tutuldu", "hata"]
_REFUSED = ("out_of_scope", "no_sources")

JUDGE_SYSTEM = """\
Bir mevzuat soru-cevap sisteminin cevaplarını puanlıyorsun. Her soru için beklenen cevap ve \
onu destekleyen kaynak alıntıları verilir. Modelin cevabını YALNIZCA bunlarla karşılaştır; \
kendi hukuk bilgini kullanma.

Puanlar:
- dogru: Beklenen cevabın ana sonucu ve önemli unsurları cevapta var; beklenenle çelişen, \
dayanağı olmayan veya yanıltıcı bir iddia yok. Başka kelimeler, kısalık ya da kaynağa dayanan \
fazladan doğru ayrıntı puanı düşürmez.
- kismen: Ana sonuç doğru, ama önemli bir unsur eksik; ya da cevapta beklenen cevapta ve \
alıntılarda dayanağı olmayan bir iddia var (doğru olabileceğini düşünsen bile: bunu kendi \
bilginle tartma); ya da cevap kendi içinde çelişiyor.
- yanlis: Ana sonuç beklenenle çelişiyor (ör. yasak olanı serbest sayıyor); bir tutar, oran \
veya süre yanlış (ör. tablonun başka satırı ya da sütunu); başka bir ürünün kuralı uygulanmış; \
ya da sorudaki yanlış varsayım onaylanmış.

Kurallar:
1. Önce analysis alanında cevabı beklenen cevapla unsur unsur karşılaştır, sonra puanı ver.
2. missing_points: beklenen cevapta olup modelin cevabında olmayan önemli unsurlar.
3. unsupported_claims: modelin cevabında olup beklenen cevapta ve alıntılarda dayanağı \
olmayan iddialar, cevaptaki ifadesiyle. Böyle bir iddia varsa puan en fazla kismen olur.
4. contradicts_expected: cevap beklenen cevapla çelişiyorsa true.
5. premise_corrected: yalnızca "varsayımı yanlış" notu olan sorularda; cevap varsayımı \
düzeltiyorsa true, düzeltmiyorsa false. Diğer sorularda null.
6. Beklenen cevap bir davranış istiyorsa ("iki metni de göster", "rakam uydurma"), o \
davranışa göre puanla.
7. Kaynak listesinin biçimi ve uyarı cümleleri puanı etkilemez.
"""

CATEGORY_NAMES = {
    "dogrudan": "doğrudan bilgi",
    "cok_maddeli": "birden fazla madde",
    "sayisal": "sayısal (tutar, oran, süre)",
    "degisiklik": "değişiklik görmüş hüküm",
    "yanlis_onerme": "yanlış önermeli",
    "kapsam_disi": "kapsam dışı",
}


class JudgeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis: str  # first, so the verdict follows from the comparison
    missing_points: list[str]
    unsupported_claims: list[str]
    contradicts_expected: bool
    premise_corrected: bool | None
    verdict: Literal["dogru", "kismen", "yanlis"]


# Applied to every verdict (see _consistent); part of the version below.
CONSISTENCY_RULE = "dogru with an unsupported or contradicting claim -> kismen"

# A digest of everything that shapes a verdict besides the answer and the golden entry: when
# the rubric, the verdict schema, the category names or the consistency rule change, earlier
# scores stop counting.
RUBRIC_VERSION = hashlib.sha256(
    "\n".join(
        [
            JUDGE_SYSTEM,
            json.dumps(json_schema(JudgeOut), sort_keys=True),
            json.dumps(CATEGORY_NAMES),
            CONSISTENCY_RULE,
        ]
    ).encode()
).hexdigest()[:12]
Key = tuple[str, str, str, str, str]


@dataclass(frozen=True)
class Judgment:
    question_id: str
    category: str
    status: str
    outcome: Outcome
    judged_by: str  # RULE, or "<provider>/<model>"
    rubric_version: str
    answer_sha: str
    golden_sha: str = ""  # the golden entry it was judged against
    judge_verdict: str = ""  # the judge's own verdict, before the consistency rule
    analysis: str = ""
    missing_points: tuple[str, ...] = ()
    unsupported_claims: tuple[str, ...] = ()
    contradicts_expected: bool | None = None
    premise_corrected: bool | None = None
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def key(self) -> Key:
        """The same answer against the same golden entry, judged the same way: a rerun skips it."""
        return (
            self.question_id,
            self.answer_sha,
            self.golden_sha,
            self.judged_by,
            self.rubric_version,
        )


def rule_outcome(question: GoldenQuestion, row: SmokeRow) -> Outcome | None:
    """The outcome when no judge is needed; None when the answer reached the user."""
    if row.status == "error":
        return "hata"
    if row.status == "unverified":
        return "geri_tutuldu"  # the user saw "doğrulanamadı", neither right nor wrong
    refused = row.status in _REFUSED
    if not question.answerable:
        return "dogru_red" if refused else "yanlis"
    return "yersiz_red" if refused else None


def judge_prompt(question: GoldenQuestion, row: SmokeRow) -> str:
    lines = [f"Soru: {question.question}", f"Kategori: {CATEGORY_NAMES[question.category]}"]
    if question.category == "yanlis_onerme":
        lines.append(
            "Not: Sorunun varsayımı yanlış; iyi bir cevap bu varsayımı kaynağa dayanarak düzeltir."
        )
    if question.comment:
        lines.append(f"Beklenen cevabı yazanın notu: {question.comment}")
    lines += ["", "Beklenen cevap:", question.expected_answer, "", "Kaynak alıntıları:"]
    lines += [f"- [{e.chunk}] {e.quote}" for e in question.evidence]
    shown = row.rendered.replace(DISCLAIMER, "").strip() or row.answer
    lines += ["", "Modelin cevabı (kullanıcının gördüğü hâliyle, atıflarıyla):", shown]
    return "\n".join(lines)


def judge_rows(
    rows: Iterable[SmokeRow],
    questions: Mapping[str, GoldenQuestion],
    provider: LLMProvider,
    done: Set[Key] = frozenset(),
) -> Iterator[Judgment]:
    """A judgment per row not judged before: the rule-scored ones first, then the judge's.

    Raises LLMRateLimited when the quota runs out and LLMUnavailable when the judge cannot be
    used; what was yielded before stays valid."""
    pending = [(row, questions[row.question_id]) for row in rows]
    for row, question in pending:
        outcome = rule_outcome(question, row)
        judgment = _judgment(question, row, outcome, provider)
        if outcome and judgment.key not in done:
            yield judgment
    for row, question in pending:
        judgment = _judgment(question, row, None, provider)
        if rule_outcome(question, row) or judgment.key in done:
            continue
        verdict = _ask_judge(provider, question, row)
        if verdict is not None:
            yield replace(judgment, **verdict)


def _judgment(
    question: GoldenQuestion, row: SmokeRow, outcome: Outcome | None, provider: LLMProvider
) -> Judgment:
    return Judgment(
        question_id=row.question_id,
        category=question.category,
        status=row.status,
        outcome=outcome or "hata",
        judged_by=_judged_by(outcome, provider),
        rubric_version=RUBRIC_VERSION,
        answer_sha=answer_sha(row),
        golden_sha=golden_sha(question),
    )


def _ask_judge(
    provider: LLMProvider, question: GoldenQuestion, row: SmokeRow
) -> dict[str, Any] | None:
    messages = [ChatMessage("user", judge_prompt(question, row))]
    for _ in range(JUDGE_ATTEMPTS):
        try:
            reply = provider.generate(JUDGE_SYSTEM, messages, JudgeOut)
        except (LLMRateLimited, LLMUnavailable):  # nothing else can be judged now
            raise
        except LLMOutputError as exc:
            logger.warning("%s: the judge's verdict was not valid (%s)", row.question_id, exc)
            continue
        except LLMError as exc:  # a refusal or a timeout: left unjudged for a rerun
            logger.warning("%s: the judge failed (%s)", row.question_id, exc)
            return None
        out = reply.parsed
        return {
            "outcome": _consistent(out),
            "judge_verdict": out.verdict,
            "analysis": out.analysis,
            "missing_points": tuple(out.missing_points),
            "unsupported_claims": tuple(out.unsupported_claims),
            "contradicts_expected": out.contradicts_expected,
            "premise_corrected": out.premise_corrected,
            "input_tokens": reply.usage.input_tokens,
            "output_tokens": reply.usage.output_tokens,
        }
    return None


def _consistent(out: JudgeOut) -> Outcome:
    """The rubric's own definition: a correct answer has no unsupported or contradicting
    claim. (Gemini Flash-Lite listed b1-060's unsupported addition and still said dogru.)"""
    if out.verdict == "dogru" and (out.unsupported_claims or out.contradicts_expected):
        return "kismen"
    return out.verdict


def answer_sha(row: SmokeRow) -> str:
    return hashlib.sha256(f"{row.status}\n{row.rendered}".encode()).hexdigest()[:16]


def golden_sha(question: GoldenQuestion) -> str:
    fields = {"question", "category", "expected_chunks", "expected_answer", "evidence", "comment"}
    return hashlib.sha256(question.model_dump_json(include=fields).encode()).hexdigest()[:16]


def judgment_key(question: GoldenQuestion, row: SmokeRow, provider: LLMProvider) -> Key:
    """The key of the judgment this row's current answer gets from `provider` (or by rule)."""
    return _judgment(question, row, rule_outcome(question, row), provider).key


def _judged_by(outcome: Outcome | None, provider: LLMProvider) -> str:
    return RULE if outcome else f"{provider.name}/{provider.model}"


def summarize_judgments(judgments: Sequence[Judgment]) -> dict[str, Any]:
    answerable = [j for j in judgments if j.category != "kapsam_disi"]
    out_of_scope = [j for j in judgments if j.category == "kapsam_disi"]
    counts = Counter(j.outcome for j in answerable)
    # every false-premise question: a withheld or refused one did not correct the premise. Only
    # these: a judge may fill premise_corrected for other categories too.
    premise = [j for j in answerable if j.category == "yanlis_onerme"]
    by_category: dict[str, Counter[str]] = {}
    for judgment in judgments:
        by_category.setdefault(judgment.category, Counter())[judgment.outcome] += 1
    n = len(answerable)
    refused = sum(j.outcome == "dogru_red" for j in out_of_scope)
    return {
        "answerable": n,
        "correct": f"{counts['dogru']}/{n}",
        "correct_or_partial": f"{counts['dogru'] + counts['kismen']}/{n}",
        "wrong": f"{counts['yanlis']}/{n}",
        "withheld": f"{counts['geri_tutuldu']}/{n}",
        "false_refusals": f"{counts['yersiz_red']}/{n}",
        "out_of_scope_refused": f"{refused}/{len(out_of_scope)}",
        "premise_corrected": f"{sum(bool(j.premise_corrected) for j in premise)}/{len(premise)}",
        "by_category": {k: dict(v) for k, v in sorted(by_category.items())},
    }


def load_rows(path: Path) -> list[SmokeRow]:
    return [SmokeRow(**_tuples(json.loads(line))) for line in _lines(path)]


def load_judgments(path: Path) -> list[Judgment]:
    return [Judgment(**_tuples(json.loads(line))) for line in _lines(path)] if path.exists() else []


def _lines(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _tuples(data: dict[str, Any]) -> dict[str, Any]:
    return {k: tuple(v) if isinstance(v, list) else v for k, v in data.items()}
