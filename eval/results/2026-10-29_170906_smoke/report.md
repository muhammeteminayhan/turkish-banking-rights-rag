# Smoke run (M4)

- Provider: `ollama`, model `qwen3:8b`; retrieval config `full`, retrieval models on cpu; thinking: True, num_ctx 8192, sampling {'temperature': 0.6, 'top_p': 0.95, 'top_k': 20, 'min_p': 0.0, 'seed': 42}.
- Questions: 20; status: {'answered': 17, 'out_of_scope': 3}.
- Verified answers that cite an expected article: 17/17 (retrieval had it: 17/17).
- Answers verified on the first try: 14/17; false refusals of answerable questions: 0/17.
- Out-of-scope questions refused: 3/3.
- Tokens: {'input': 77767, 'output': 18806}; cost: 0.0 USD.
- Latency p50 24340 ms, p95 52742 ms.

| Question | Category | Status | Attempts | Expected cited | Retrieved | Top score | Cited | Verification errors |
|---|---|---|---|---|---|---|---|---|
| b1-001 | dogrudan | answered | 1 | yes | yes | 0.956 | 6502:m22:f1, 6502:m22:f2, 6502:m22:f3 | – |
| b1-003 | dogrudan | answered | 1 | yes | yes | 0.862 | 5464:m10:f1 | – |
| b1-007 | dogrudan | answered | 1 | yes | yes | 0.864 | tcmb-ucret-talimat:s8:bc, tcmb-ucret-teblig:m11:f2 | – |
| b1-011 | dogrudan | answered | 1 | yes | yes | 0.751 | kart-yon:m22:f2, 5464:m9:f1, kart-yon:m17:f5:p1 | – |
| b1-016 | dogrudan | answered | 1 | yes | yes | 0.978 | mesafeli-finansal-yon:m8:f1, 6502:m49:f5, mesafeli-finansal-yon:m9:f2, 6502:m47:f5 | – |
| b1-021 | dogrudan | answered | 1 | yes | yes | 0.658 | 6698:m7:f1, 6698:m11:f1, 6698:m7:f3 | – |
| b1-024 | cok_maddeli | answered | 1 | yes | yes | 0.761 | 6502:m24:f1, 6502:m24:f3, tuketici-kredisi-yon:m24:f5 | – |
| b1-025 | cok_maddeli | answered | 1 | yes | yes | 0.993 | 6502:m37:f2, tcmb-ucret-talimat:s7:bd, tcmb-ucret-teblig:m10:f1 | – |
| b1-027 | cok_maddeli | answered | 1 | yes | yes | 0.967 | 5464:m8:f2, kart-yon:m22:f6 | – |
| b1-033 | sayisal | answered | 2 | yes | yes | 0.993 | tcmb-ucret-talimat:s9:bc, tcmb-ucret-talimat:s9:bc, tcmb-ucret-talimat:s9:bc | – |
| b1-036 | sayisal | answered | 2 | yes | yes | 0.959 | tcmb-ucret-talimat:s7:bf, tcmb-ucret-teblig:m10:f6, tcmb-ucret-talimat:s8:bl | – |
| b1-039 | sayisal | answered | 2 | yes | yes | 0.986 | tcmb-ucret-talimat:s8:bh, tcmb-ucret-teblig:m11:f6 | – |
| b1-045 | degisiklik | answered | 1 | yes | yes | 0.969 | 6502:m4:f3, 5411:m144:f1 | – |
| b1-046 | degisiklik | answered | 1 | yes | yes | 0.999 | kart-yon:m18:f2 | – |
| b1-051 | kapsam_disi | out_of_scope | 1 | – | – | 0.037 | – | – |
| b1-053 | kapsam_disi | out_of_scope | 1 | – | – | 0.060 | – | – |
| b1-056 | kapsam_disi | out_of_scope | 1 | – | – | 0.038 | – | – |
| b1-059 | yanlis_onerme | answered | 1 | yes | yes | 0.667 | 6502:m31:f3, tcmb-ucret-talimat:s8:bg, tcmb-ucret-talimat:s8:bd | – |
| b1-060 | yanlis_onerme | answered | 1 | yes | yes | 0.579 | 6502:m27:f1, 6502:m20:f1 | – |
| b1-064 | yanlis_onerme | answered | 1 | yes | yes | 0.990 | 5464:m24:f3, 5464:m26:f2, 5464:m26:f5 | – |
