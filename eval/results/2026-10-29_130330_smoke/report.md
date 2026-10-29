# Smoke run (M4)

- Provider: `ollama`, model `qwen3:8b`; retrieval config `full`, retrieval models on cpu; thinking: False.
- Questions: 20; status: {'answered': 12, 'unverified': 6, 'out_of_scope': 2}.
- Verified answers that cite an expected article: 10/17 (retrieval had it: 17/17).
- Answers verified on the first try: 11/12; false refusals of answerable questions: 0/17.
- Out-of-scope questions refused: 2/3.
- Tokens: {'input': 92954, 'output': 12552}; cost: 0.0 USD.
- Latency p50 18307 ms, p95 39679 ms.

| Question | Category | Status | Attempts | Expected cited | Retrieved | Top score | Cited | Verification errors |
|---|---|---|---|---|---|---|---|---|
| b1-001 | dogrudan | answered | 1 | yes | yes | 0.956 | 6502:m22:f1, 6502:m22:f2, 6502:m22:f3 | – |
| b1-003 | dogrudan | unverified | 2 | no | yes | 0.862 | – | Atıf 1 (5464:m10:f1): fıkra 1, None değil. |
| b1-007 | dogrudan | answered | 1 | yes | yes | 0.864 | tcmb-ucret-talimat:s8:bc, tcmb-ucret-teblig:m11:f2 | – |
| b1-011 | dogrudan | answered | 1 | no | yes | 0.751 | kart-yon:m22:f2, kart-yon:m22:f2 | – |
| b1-016 | dogrudan | answered | 1 | yes | yes | 0.978 | mesafeli-finansal-yon:m8:f1, 6502:m49:f5 | – |
| b1-021 | dogrudan | unverified | 2 | no | yes | 0.658 | – | Atıf 2 (6698:m11:f1): alıntı kaynak metinde birebir geçmiyor. Metinden kelimesi kelimesine kopyala. |
| b1-024 | cok_maddeli | answered | 2 | yes | yes | 0.761 | 6502:m24:f1, tuketici-kredisi-yon:m24:f4, tuketici-kredisi-yon:m24:f5, mesafeli-finansal-yon:m11:f1 | – |
| b1-025 | cok_maddeli | answered | 1 | yes | yes | 0.993 | 6502:m37:f2, konut-finansmani-yon:m11:f4, tcmb-ucret-talimat:s7:ba, tcmb-ucret-teblig:m10:f1 | – |
| b1-027 | cok_maddeli | answered | 1 | yes | yes | 0.967 | 5464:m8:f2, kart-yon:m22:f6 | – |
| b1-033 | sayisal | answered | 1 | yes | yes | 0.993 | tcmb-ucret-talimat:s9:bc, tcmb-ucret-talimat:s9:bc | – |
| b1-036 | sayisal | answered | 1 | yes | yes | 0.959 | tcmb-ucret-talimat:s7:bf, tcmb-ucret-teblig:m10:f6 | – |
| b1-039 | sayisal | unverified | 2 | no | yes | 0.986 | – | Cevaptaki şu sayılar atıf yapılan kaynaklarda geçmiyor: 100. Yalnızca kaynakta yazan sayıları kullan; hesaplama yapma. |
| b1-045 | degisiklik | unverified | 2 | no | yes | 0.969 | – | Atıf 1 (6502:m4:f3): fıkra 3, None değil.; Atıf 2 (5411:m144:f1): fıkra 1, None değil.; Atıf 3 (odeme-hizmetleri-yon:m50:f1): fıkra 1, None değil.; Atıf 4 (6493:m12:f4): fıkra 4, None değil. |
| b1-046 | degisiklik | answered | 1 | yes | yes | 0.999 | kart-yon:m18:f2 | – |
| b1-051 | kapsam_disi | unverified | 2 | – | – | 0.037 | – | Atıf 1 (5411:m145:f1): fıkra 1, None değil.; Atıf 2 (tcmb-ucret-teblig:m7:f1): fıkra 1, None değil.; Atıf 3 (5464:m47:f1): fıkra 1, None değil. |
| b1-053 | kapsam_disi | out_of_scope | 1 | – | – | 0.060 | – | – |
| b1-056 | kapsam_disi | out_of_scope | 1 | – | – | 0.038 | – | – |
| b1-059 | yanlis_onerme | unverified | 2 | no | yes | 0.667 | – | Atıf 1 (6502:m31:f3): fıkra 3, None değil.; Atıf 3 (tcmb-ucret-teblig:m11:f1): fıkra 1, None değil. |
| b1-060 | yanlis_onerme | answered | 1 | yes | yes | 0.579 | 6502:m27:f1, 6502:m37:f2, konut-finansmani-yon:m11:f4 | – |
| b1-064 | yanlis_onerme | answered | 1 | no | yes | 0.990 | 5464:m26:f2, 5464:m26:f5 | – |
