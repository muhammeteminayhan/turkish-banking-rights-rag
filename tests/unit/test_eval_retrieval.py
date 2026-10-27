import json
from pathlib import Path

import pytest

from finhak.evaluation.golden import GoldenError, GoldenQuestion, load_golden, unknown_chunk_ids
from finhak.evaluation.retrieval import (
    madde_key,
    recall_at_k,
    reciprocal_rank,
    score_question,
    summarize,
)

pytestmark = pytest.mark.unit


def _question(qid: str = "b1-001", category: str = "dogrudan", **fields: object) -> GoldenQuestion:
    data: dict[str, object] = {
        "id": qid,
        "category": category,
        "question": "Kart aidatı geri alınır mı?",
        "expected_chunks": ["5464:m10:f1"],
        "expected_answer": "…",
        "evidence": [{"chunk": "5464:m10:f1", "quote": "aidat"}],
        "confidence": "high",
        "comment": "",
    }
    return GoldenQuestion.model_validate({**data, **fields})


@pytest.mark.parametrize(
    ("chunk_id", "key"),
    [
        ("6502:m22:f1", "6502:m22"),
        ("6502:m3:f1:p2", "6502:m3"),
        ("6493:m38-39:f1", "6493:m38-39"),
        ("tcmb-ucret-talimat:s9:bc", "tcmb-ucret-talimat:s9"),
        ("tcmb-ucret-talimat:ek1:g3:2.1", "tcmb-ucret-talimat:ek1"),
        ("6502:ek1:p1", "6502:ek1"),
        ("tcmb-ucret-talimat:giris", "tcmb-ucret-talimat:giris"),
        ("6502:m5~2:f1", "6502:m5"),  # duplicate-id suffix from chunker._unique
    ],
)
def test_madde_key_is_document_and_article(chunk_id: str, key: str) -> None:
    assert madde_key(chunk_id) == key


def test_recall_counts_expected_items_in_the_top_k() -> None:
    assert recall_at_k(["a", "b", "c"], [{"b"}, {"x"}], k=2) == 0.5
    assert recall_at_k(["a", "b", "c"], [{"b"}, {"x"}], k=1) == 0.0
    assert recall_at_k(["x", "b"], [{"b"}, {"x"}], k=5) == 1.0


def test_an_equivalent_chunk_counts_for_its_expected_chunk() -> None:
    # Group {b, b2}: the same rule in two documents; finding either is enough.
    assert recall_at_k(["b2", "c"], [{"b", "b2"}, {"x"}], k=2) == 0.5


def test_recall_needs_expected_items() -> None:
    with pytest.raises(ValueError, match="expected"):
        recall_at_k(["a"], [], k=5)


def test_reciprocal_rank_of_the_first_hit_within_the_cutoff() -> None:
    assert reciprocal_rank(["a", "b", "c"], [{"c"}, {"b"}]) == 0.5
    assert reciprocal_rank(["a", "b"], [{"z"}]) == 0.0
    assert reciprocal_rank(["a", "b", "c"], [{"c"}], cutoff=2) == 0.0
    assert reciprocal_rank(["a", "c2"], [{"c", "c2"}]) == 0.5


def test_score_question_uses_equivalent_chunks() -> None:
    question = _question(
        expected_chunks=["tcmb-ucret-teblig:m11:f3", "6502:m31:f3"],
        evidence=[],
        equivalent_chunks={"tcmb-ucret-teblig:m11:f3": ["tcmb-ucret-talimat:s8:bd"]},
    )

    score = score_question(question, ["tcmb-ucret-talimat:s8:bd", "6502:m1:f1"], latency_ms=1.0)

    assert score.chunk["recall@5"] == 0.5
    assert score.chunk["mrr"] == 1.0
    assert score.madde["recall@1"] == 0.5


@pytest.mark.parametrize("found", ["5464:m12:f1", "kart-yon:m23:f1"])
def test_overlapping_equivalence_groups_merge_whichever_copy_is_found(found: str) -> None:
    # 5464 m12 ≡ kart-yon m23, both expected, plus a third rule: two groups, not three.
    question = _question(
        expected_chunks=["5464:m12:f1", "kart-yon:m23:f1", "odeme-hizmetleri-yon:m54:f4"],
        evidence=[],
        equivalent_chunks={"5464:m12:f1": ["kart-yon:m23:f1"]},
    )

    assert len(question.groups) == 2
    assert score_question(question, [found], latency_ms=1.0).chunk["recall@1"] == 0.5


def test_equivalence_is_transitive() -> None:
    question = _question(
        expected_chunks=["a:m1:f1", "b:m1:f1"],
        evidence=[],
        equivalent_chunks={"a:m1:f1": ["c:m1:f1"], "b:m1:f1": ["c:m1:f1"]},
    )

    assert question.groups == (frozenset({"a:m1:f1", "b:m1:f1", "c:m1:f1"}),)


def test_equivalents_must_belong_to_an_expected_chunk() -> None:
    with pytest.raises(ValueError, match="equivalent_chunks"):
        _question(equivalent_chunks={"6502:m1:f1": ["6502:m2:f1"]})


def test_score_question_at_chunk_and_article_level() -> None:
    question = _question(expected_chunks=["6502:m22:f2", "5464:m10:f1"])
    ranked = ["6502:m22:f1", "6502:m22:f3", "5464:m10:f1", "6502:m22:f2"]

    score = score_question(question, ranked, latency_ms=12.5)

    assert score.chunk["recall@5"] == 1.0
    assert score.chunk["recall@1"] == 0.0
    assert score.chunk["mrr"] == pytest.approx(1 / 3)
    # Articles: the first chunk is already in the expected article 6502:m22.
    assert score.madde["recall@1"] == 0.5
    assert score.madde["recall@5"] == 1.0
    assert score.madde["mrr"] == 1.0
    assert score.ranked[:2] == ("6502:m22:f1", "6502:m22:f3")
    assert score.latency_ms == 12.5


def test_article_recall_counts_within_the_top_k_chunks_not_distinct_articles() -> None:
    # Nine chunks of one article push the expected article to chunk rank 10. Generation reads
    # the top-k chunks, so this is a miss at k=5 and an MRR of 1/10.
    question = _question(expected_chunks=["6502:m30:f1"], evidence=[])
    ranked = [f"6502:m22:f{n}" for n in range(1, 10)] + ["6502:m30:f1"]

    score = score_question(question, ranked, latency_ms=1.0)

    assert score.madde["recall@5"] == 0.0
    assert score.madde["recall@10"] == 1.0
    assert score.madde["mrr"] == pytest.approx(0.1)


def test_questions_that_cite_an_article_are_reported_apart() -> None:
    cited = score_question(
        _question("q1", question="5464 m.10 ne diyor?"), ["5464:m10:f1"], latency_ms=1.0
    )
    plain = score_question(_question("q2"), ["x:m1:f1"], latency_ms=1.0)

    summary = summarize([cited, plain])

    assert (cited.cites_article, plain.cites_article) == (True, False)
    assert summary.by_citation["cites_article"]["madde_recall@5"] == 1.0
    assert summary.by_citation["no_citation"]["madde_recall@5"] == 0.0
    assert summary.by_citation["no_citation"]["n"] == 1


def test_score_question_rejects_out_of_scope_questions() -> None:
    question = _question(category="kapsam_disi", expected_chunks=[], evidence=[])

    with pytest.raises(ValueError, match="expected"):
        score_question(question, ["a"], latency_ms=1.0)


def test_summary_averages_overall_and_per_category() -> None:
    hit = score_question(_question("q1"), ["5464:m10:f1"], latency_ms=10.0)
    miss = score_question(_question("q2", "sayisal"), ["x:m1:f1"], latency_ms=30.0)

    summary = summarize([hit, miss])

    assert summary.n == 2
    assert summary.chunk["recall@5"] == 0.5
    assert summary.by_category["dogrudan"]["chunk_mrr"] == 1.0
    assert summary.by_category["sayisal"]["n"] == 1
    assert summary.latency_ms == {"p50": 20.0, "p95": 29.0}


def test_summary_of_nothing_is_rejected() -> None:
    with pytest.raises(ValueError, match="no scored"):
        summarize([])


def test_out_of_scope_questions_have_no_expected_chunks() -> None:
    with pytest.raises(ValueError, match="kapsam_disi"):
        _question(category="kapsam_disi")


def test_answerable_questions_need_expected_chunks() -> None:
    with pytest.raises(ValueError, match="expected_chunks"):
        _question(expected_chunks=[])


def test_evidence_must_point_at_an_expected_chunk() -> None:
    with pytest.raises(ValueError, match="evidence"):
        _question(evidence=[{"chunk": "6502:m1:f1", "quote": "x"}])


def _write(path: Path, rows: list[dict[str, object] | str]) -> Path:
    lines = [row if isinstance(row, str) else json.dumps(row, ensure_ascii=False) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_load_golden_reads_jsonl_and_skips_blank_lines(tmp_path: Path) -> None:
    row = _question().model_dump(mode="json")
    path = _write(tmp_path / "g.jsonl", [row, "", {**row, "id": "b1-002"}])

    assert [q.id for q in load_golden(path)] == ["b1-001", "b1-002"]


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        (["{not json"], "line 1"),
        ([{"id": "x"}], "line 1"),
        (["dup", "dup"], "duplicate"),
    ],
)
def test_load_golden_reports_bad_files(tmp_path: Path, rows: list[object], message: str) -> None:
    row = _question().model_dump(mode="json")
    resolved = [row if r == "dup" else r for r in rows]

    with pytest.raises(GoldenError, match=message):
        load_golden(_write(tmp_path / "g.jsonl", resolved))  # type: ignore[arg-type]


def test_load_golden_reports_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(GoldenError, match=r"missing\.jsonl"):
        load_golden(tmp_path / "missing.jsonl")


def test_unknown_chunk_ids_are_listed() -> None:
    questions = [
        _question(),
        _question("b1-002", expected_chunks=["6502:m999:f1"], evidence=[]),
        _question("b1-003", equivalent_chunks={"5464:m10:f1": ["kart-yon:m0:f1"]}),
    ]

    assert unknown_chunk_ids(questions, {"5464:m10:f1"}) == {
        "b1-002": ("6502:m999:f1",),
        "b1-003": ("kart-yon:m0:f1",),
    }
