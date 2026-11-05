"""The owner's hand scores of an end-to-end run, and how far each judge agrees with them (M5).

A sample of the answers that reached the user goes to <run>/hand_scores.md without any judge's
verdict, so none can anchor the reading. The owner writes doğru / kısmen / yanlış under each
answer; `agreement` compares those scores with a judge's: percent agreement and Cohen's kappa,
on the three labels and on correct-or-not.
"""

import random
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from finhak.evaluation.golden import GoldenQuestion
from finhak.evaluation.judge import CATEGORY_NAMES
from finhak.evaluation.smoke import SmokeRow
from finhak.generation.render import DISCLAIMER
from finhak.textnorm import tr_casefold

LABELS = ("dogru", "kismen", "yanlis")
SAMPLE_SIZE = 30
SEED = 42
SCORE_LINE = "**Puanın:**"
NOTE_LINE = "**Not:**"
_ALIASES = {
    "doğru": "dogru", "dogru": "dogru", "d": "dogru",
    "kısmen": "kismen", "kismen": "kismen", "k": "kismen",
    "yanlış": "yanlis", "yanlis": "yanlis", "y": "yanlis",
}  # fmt: skip
_HEADER = re.compile(r"^## (\S+)")

SHEET_HELP = """\
Her cevabın altındaki "Puanın:" satırına `doğru`, `kısmen` veya `yanlış` yaz (kısaca d / k \
/ y); istersen "Not:" satırına kısa bir gerekçe. Ölçüt hakeminkiyle aynı:

- **doğru:** beklenen cevabın ana sonucu ve önemli unsurları cevapta var; beklenenle çelişen \
ya da kaynağı olmayan bir iddia yok.
- **kısmen:** ana sonuç doğru, ama önemli bir unsur eksik, kaynağı olmayan bir iddia var ya da \
cevap kendi içinde çelişiyor.
- **yanlış:** ana sonuç beklenenle çelişiyor; bir tutar, oran veya süre yanlış; başka bir \
ürünün kuralı uygulanmış ya da sorudaki yanlış varsayım onaylanmış.

Beklenen cevabı ve alıntıları ölçü al: hakem de yalnızca bunları görüyor. Boş bıraktığın \
cevaplar sayılmaz.
"""


@dataclass(frozen=True)
class HandScores:
    scores: dict[str, str]  # question id → dogru | kismen | yanlis
    notes: dict[str, str]
    problems: list[str]


@dataclass(frozen=True)
class Agreement:
    n: int  # answers both scored
    agreed: int
    binary_agreed: int  # on correct (dogru) vs not
    kappa: float | None
    binary_kappa: float | None
    confusion: dict[tuple[str, str], int] = field(default_factory=dict)  # (hand, judge) → count
    disagreements: list[tuple[str, str, str]] = field(default_factory=list)  # (id, hand, judge)


def eligible(rows: Sequence[SmokeRow], questions: Mapping[str, GoldenQuestion]) -> list[SmokeRow]:
    """The answers a judge model scores: shown to the user, to an answerable question."""
    return [r for r in rows if r.status == "answered" and questions[r.question_id].answerable]


def pick_sample(
    rows: Sequence[SmokeRow],
    questions: Mapping[str, GoldenQuestion],
    n: int = SAMPLE_SIZE,
    seed: int = SEED,
) -> list[SmokeRow]:
    """A sample of the eligible answers, stratified by category (largest remainder), in id
    order; the same for the same rows and seed."""
    pool = eligible(rows, questions)
    if len(pool) <= n:
        return sorted(pool, key=lambda r: r.question_id)
    groups: dict[str, list[SmokeRow]] = {}
    for row in sorted(pool, key=lambda r: r.question_id):
        groups.setdefault(questions[row.question_id].category, []).append(row)
    quotas = _quotas({category: len(group) for category, group in groups.items()}, n)
    rng = random.Random(seed)
    picked = [
        row for category in sorted(groups) for row in rng.sample(groups[category], quotas[category])
    ]
    return sorted(picked, key=lambda r: r.question_id)


def _quotas(sizes: Mapping[str, int], n: int) -> dict[str, int]:
    total = sum(sizes.values())
    exact = {category: n * size / total for category, size in sizes.items()}
    quotas = {category: int(value) for category, value in exact.items()}
    by_remainder = sorted(exact, key=lambda c: (-(exact[c] - quotas[c]), c))
    for category in by_remainder[: n - sum(quotas.values())]:
        quotas[category] += 1
    return quotas


def render_sheet(
    sample: Sequence[SmokeRow], questions: Mapping[str, GoldenQuestion], run: str
) -> str:
    """The sheet: per answer what the judge sees (question, notes, expected answer, evidence,
    the answer as shown to the user), then the lines to fill in."""
    lines = [
        f"# Elle puanlama: {run}",
        "",
        f"Bu çalıştırmada kullanıcıya ulaşan cevaplardan {len(sample)} tanesi (kategoriye göre "
        f"tabakalı örneklem, seed {SEED}). Hakemlerin puanları bilerek gösterilmiyor.",
        "",
        SHEET_HELP,
        "Bitince: `python eval/hand_sheet.py score <bu klasör>`.",
        "",
    ]
    for row in sample:
        lines += _section(questions[row.question_id], row)
    return "\n".join(lines)


def _section(question: GoldenQuestion, row: SmokeRow) -> list[str]:
    lines = ["---", "", f"## {row.question_id} · {CATEGORY_NAMES[question.category]}", ""]
    lines += [f"**Soru:** {question.question}", ""]
    if question.category == "yanlis_onerme":
        lines += ["*Sorunun varsayımı yanlış; iyi bir cevap onu kaynağa dayanarak düzeltir.*", ""]
    if question.comment:
        lines += [f"*Beklenen cevabı yazanın notu:* {question.comment}", ""]
    lines += [f"**Beklenen cevap:** {question.expected_answer}", "", "**Kaynak alıntıları:**"]
    lines += [f"- `{e.chunk}`: “{e.quote}”" for e in question.evidence]
    shown = row.rendered.replace(DISCLAIMER, "").strip() or row.answer
    lines += ["", "**Modelin cevabı** (kullanıcının gördüğü hâliyle):", ""]
    # quoted, so no line of the answer can pass for a heading or a score line
    lines += [f"> {line}" if line.strip() else ">" for line in shown.splitlines()]
    return [*lines, "", f"{SCORE_LINE} ", f"{NOTE_LINE} ", ""]


def parse_sheet(text: str) -> HandScores:
    scores: dict[str, str] = {}
    notes: dict[str, str] = {}
    problems: list[str] = []
    current = ""
    for line in text.splitlines():
        header = _HEADER.match(line)
        if header:
            current = header.group(1)
        elif line.startswith(SCORE_LINE) and current:
            value = line[len(SCORE_LINE) :].strip()
            label = _ALIASES.get(tr_casefold(value)) if value else None
            if label:
                scores[current] = label
            elif value:
                problems.append(f"{current}: {value!r} is not doğru, kısmen or yanlış (d / k / y)")
        elif line.startswith(NOTE_LINE) and current:
            note = line[len(NOTE_LINE) :].strip()
            if note:
                notes[current] = note
    return HandScores(scores, notes, problems)


def cohen_kappa(pairs: Sequence[tuple[str, str]]) -> float | None:
    """Cohen's kappa of two raters over the labels they used; None without pairs."""
    if not pairs:
        return None
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    first, second = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(first[label] * second[label] for label in first.keys() | second.keys()) / n**2
    if expected == 1.0:  # both raters used one and the same label throughout
        return 1.0
    return (observed - expected) / (1.0 - expected)


def agreement(human: Mapping[str, str], judge: Mapping[str, str]) -> Agreement:
    common = sorted(human.keys() & judge.keys())
    pairs = [(human[q], judge[q]) for q in common]
    binary = [(a == "dogru", b == "dogru") for a, b in pairs]
    return Agreement(
        n=len(pairs),
        agreed=sum(a == b for a, b in pairs),
        binary_agreed=sum(a == b for a, b in binary),
        kappa=cohen_kappa(pairs),
        binary_kappa=cohen_kappa([(str(a), str(b)) for a, b in binary]),
        confusion=dict(Counter(pairs)),
        disagreements=[(q, human[q], judge[q]) for q in common if human[q] != judge[q]],
    )
