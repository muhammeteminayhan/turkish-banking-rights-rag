# Retrieval evaluation: `eval/drafts/batch1.jsonl`

> **Draft numbers.** 64 of 64 questions are not approved yet.

- Questions: 64; scored 56 (out-of-scope questions have no expected chunks and are skipped).
- Index: 2692 chunks, embedder `BAAI/bge-m3@5617a9f6`, built 2026-10-27T08:47:46+00:00.
- Reranker: `BAAI/bge-reranker-v2-m3@953dc6f6`; candidates per retriever 30; results kept 10.

## Overall

| Config | Chunk R@5 | Chunk R@10 | Chunk MRR | Madde R@5 | Madde R@10 | Madde MRR | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|
| `fts` | 0.250 | 0.339 | 0.244 | 0.304 | 0.393 | 0.283 | 6 | 8 |
| `bm25` | 0.554 | 0.634 | 0.474 | 0.688 | 0.786 | 0.547 | 9 | 16 |
| `bm25_prefix5` | 0.640 | 0.747 | 0.513 | 0.696 | 0.830 | 0.562 | 8 | 10 |
| `vector` | 0.735 | 0.839 | 0.646 | 0.821 | 0.875 | 0.680 | 20 | 24 |
| `hybrid` | 0.583 | 0.726 | 0.501 | 0.679 | 0.759 | 0.555 | 36 | 41 |
| `hybrid_rerank` | 0.833 | 0.878 | 0.813 | 0.875 | 0.920 | 0.828 | 297 | 569 |
| `full` | 0.851 | 0.896 | 0.831 | 0.893 | 0.938 | 0.845 | 310 | 652 |
| `hybrid_bm25` | 0.717 | 0.812 | 0.683 | 0.759 | 0.866 | 0.734 | 39 | 47 |
| `hybrid_bm25_rerank` | 0.863 | 0.934 | 0.843 | 0.911 | 0.973 | 0.858 | 325 | 648 |
| `full_bm25` | 0.869 | 0.941 | 0.843 | 0.911 | 0.973 | 0.858 | 318 | 629 |

## Madde Recall@5 by category

| Config | cok_maddeli (n=10) | degisiklik (n=8) | dogrudan (n=22) | sayisal (n=10) | yanlis_onerme (n=6) |
|---|---|---|---|---|---|
| `fts` | 0.350 | 0.125 | 0.318 | 0.400 | 0.250 |
| `bm25` | 0.550 | 0.500 | 0.773 | 0.900 | 0.500 |
| `bm25_prefix5` | 0.550 | 0.625 | 0.727 | 0.850 | 0.667 |
| `vector` | 0.700 | 0.750 | 0.909 | 1.000 | 0.500 |
| `hybrid` | 0.550 | 0.625 | 0.636 | 1.000 | 0.583 |
| `hybrid_rerank` | 0.800 | 0.875 | 0.864 | 1.000 | 0.833 |
| `full` | 0.800 | 0.875 | 0.909 | 1.000 | 0.833 |
| `hybrid_bm25` | 0.650 | 0.625 | 0.773 | 1.000 | 0.667 |
| `hybrid_bm25_rerank` | 0.800 | 0.875 | 0.955 | 1.000 | 0.833 |
| `full_bm25` | 0.800 | 0.875 | 0.955 | 1.000 | 0.833 |

## Madde Recall@5: questions that cite an article vs. the rest

| Config | cites_article (n=6) | no_citation (n=50) |
|---|---|---|
| `fts` | 0.000 | 0.340 |
| `bm25` | 0.833 | 0.670 |
| `bm25_prefix5` | 0.833 | 0.680 |
| `vector` | 0.833 | 0.820 |
| `hybrid` | 0.167 | 0.740 |
| `hybrid_rerank` | 0.833 | 0.880 |
| `full` | 1.000 | 0.880 |
| `hybrid_bm25` | 0.833 | 0.750 |
| `hybrid_bm25_rerank` | 1.000 | 0.900 |
| `full_bm25` | 1.000 | 0.900 |

## `full`: questions whose expected articles are not all in the top 5

| Question | Category | Expected articles | Top 3 retrieved |
|---|---|---|---|
| b1-015 | dogrudan | tcmb-ucret-teblig:m13 | odeme-hizmetleri-yon:m59:f8, 6502:m4:f3, odeme-hizmetleri-yon:m50:f4 |
| b1-020 | dogrudan | haksiz-sartlar-yon:ek1 | 5464:m24:f4, 6502:m5:f1, 6502:m5:f7 |
| b1-023 | cok_maddeli | 5464:m12, kart-yon:m23, odeme-hizmetleri-yon:m54 | kart-yon:m23:f1, 5464:m12:f1, kart-yon:m17:f4:p1 |
| b1-028 | cok_maddeli | hakem-heyetleri-yon:m20, hakem-heyetleri-yon:m24 | hakem-heyetleri-yon:m20:f4, 6502:m70:f1, 6502:m70:f3 |
| b1-029 | cok_maddeli | erisilebilirlik-yon:m4, erisilebilirlik-yon:m5 | erisilebilirlik-yon:m5:f6, tcmb-ucret-talimat:s11:ba, tcmb-ucret-talimat:s11:bc |
| b1-031 | cok_maddeli | konut-finansmani-yon:m13, tuketici-kredisi-yon:m18 | konut-finansmani-yon:m13:f1, 6502:m37:f1, 6502:m34:f1 |
| b1-050 | degisiklik | mesafeli-finansal-yon:m13 | 6502:m48:f4, mesafeli-finansal-yon:m8:f1, mesafeli-finansal-yon:m11:f1 |
| b1-062 | yanlis_onerme | mevduat-yon:m8 | odeme-hizmetleri-yon:m81:f2, odeme-hizmetleri-yon:m81:f3, odeme-hizmetleri-yon:m4:f1 |
