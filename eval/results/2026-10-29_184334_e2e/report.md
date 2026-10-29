# End-to-end run (M5)

- Provider: `ollama`, model `qwen3:8b`; retrieval config `full`, retrieval models on cpu; thinking: True, num_ctx 8192, sampling {'temperature': 0.6, 'top_p': 0.95, 'top_k': 20, 'min_p': 0.0, 'seed': 42}.
- Questions: 64; status: {'answered': 47, 'out_of_scope': 8, 'unverified': 9}.
- Verified answers that cite an expected article: 41/56 (retrieval had it: 53/56).
- Answers verified on the first try: 38/47; false refusals of answerable questions: 2/56.
- Out-of-scope questions refused: 6/8.
- Tokens: {'input': 273380, 'output': 78533}; cost: 0.0 USD.
- Latency p50 25525 ms, p95 74172 ms.

| Question | Category | Status | Attempts | Expected cited | Retrieved | Top score | Cited | Verification errors |
|---|---|---|---|---|---|---|---|---|
| b1-001 | dogrudan | answered | 1 | yes | yes | 0.956 | 6502:m22:f1, 6502:m22:f2, 6502:m22:f3 | – |
| b1-002 | dogrudan | answered | 1 | yes | yes | 1.000 | tuketici-kredisi-yon:m9:f1 | – |
| b1-003 | dogrudan | answered | 1 | yes | yes | 0.862 | 5464:m10:f1 | – |
| b1-004 | dogrudan | answered | 1 | yes | yes | 0.958 | 6698:m11:f1 | – |
| b1-005 | dogrudan | answered | 1 | yes | yes | 1.000 | haksiz-sartlar-yon:m7:f1, 6502:m5:f2 | – |
| b1-006 | dogrudan | answered | 1 | yes | yes | 0.966 | 5411:m76:f1 | – |
| b1-007 | dogrudan | answered | 1 | yes | yes | 0.864 | tcmb-ucret-talimat:s8:bc, tcmb-ucret-teblig:m11:f2 | – |
| b1-008 | dogrudan | answered | 1 | yes | yes | 0.610 | tcmb-ucret-talimat:s8:bd, tcmb-ucret-talimat:s8:be | – |
| b1-009 | dogrudan | out_of_scope | 1 | no | yes | 0.638 | – | – |
| b1-010 | dogrudan | answered | 1 | yes | yes | 0.968 | tcmb-ucret-talimat:s7:bc, tcmb-ucret-teblig:m10:f3 | – |
| b1-011 | dogrudan | answered | 1 | yes | yes | 0.751 | kart-yon:m22:f2, 5464:m9:f1, kart-yon:m17:f5:p1 | – |
| b1-012 | dogrudan | answered | 1 | yes | yes | 0.997 | hakem-heyetleri-yon:m11:f1, hakem-heyetleri-yon:m11:f4 | – |
| b1-013 | dogrudan | answered | 1 | yes | yes | 0.994 | erisilebilirlik-yon:m4:f11, erisilebilirlik-yon:m4:f4, erisilebilirlik-yon:m5:f6 | – |
| b1-014 | dogrudan | answered | 1 | yes | yes | 0.955 | erisilebilirlik-yon:m4:f7, erisilebilirlik-yon:m8:f4 | – |
| b1-015 | dogrudan | answered | 1 | no | no | 0.127 | odeme-hizmetleri-yon:m50:f4, 6502:m4:f3 | – |
| b1-016 | dogrudan | answered | 1 | yes | yes | 0.978 | mesafeli-finansal-yon:m8:f1, 6502:m49:f5, mesafeli-finansal-yon:m9:f2, 6502:m47:f5 | – |
| b1-017 | dogrudan | answered | 1 | yes | yes | 0.899 | 6502:m5:f4, haksiz-sartlar-yon:m6:f3 | – |
| b1-018 | dogrudan | answered | 1 | yes | yes | 0.904 | tcmb-ucret-talimat:s7:be, tcmb-ucret-teblig:m10:f5, 6502:m31:f1 | – |
| b1-019 | dogrudan | answered | 1 | yes | yes | 0.761 | odeme-hizmetleri-yon:m54:f3, odeme-hizmetleri-yon:m54:f1 | – |
| b1-020 | dogrudan | answered | 1 | no | no | 0.995 | 5464:m24:f4, 6502:m5:f2, haksiz-sartlar-yon:m5:f4 | – |
| b1-021 | dogrudan | answered | 1 | yes | yes | 0.658 | 6698:m7:f1, 6698:m11:f1, 6698:m7:f3 | – |
| b1-022 | dogrudan | answered | 2 | yes | yes | 0.565 | tuketici-kredisi-yon:m29:f2, konut-finansmani-yon:m18:f2, 6502:m31:f2, mevduat-yon:m4:f3 | – |
| b1-023 | cok_maddeli | answered | 2 | yes | yes | 0.913 | kart-yon:m23:f1, 5464:m12:f1 | – |
| b1-024 | cok_maddeli | answered | 1 | yes | yes | 0.761 | 6502:m24:f3, tuketici-kredisi-yon:m24:f5, 6502:m24:f1 | – |
| b1-025 | cok_maddeli | answered | 1 | yes | yes | 0.993 | 6502:m37:f2, tcmb-ucret-talimat:s7:bd, tcmb-ucret-teblig:m10:f1 | – |
| b1-026 | cok_maddeli | answered | 1 | no | yes | 0.707 | 5464:m25:f1, 6502:m26:f2, tcmb-ucret-teblig:m7:f1 | – |
| b1-027 | cok_maddeli | answered | 1 | yes | yes | 0.967 | 5464:m8:f2, kart-yon:m22:f6 | – |
| b1-028 | cok_maddeli | answered | 2 | no | yes | 0.868 | 6502:m70:f1, 6502:m70:f3, 6502:m70:f7 | – |
| b1-029 | cok_maddeli | answered | 1 | yes | yes | 0.984 | erisilebilirlik-yon:m5:f6, erisilebilirlik-yon:m4:f11 | – |
| b1-030 | cok_maddeli | unverified | 2 | no | yes | 0.758 | – | Atıf 1 (kart-yon:m19:f1): alıntı kaynak metinde birebir geçmiyor. Metinden kelimesi kelimesine kopyala. |
| b1-031 | cok_maddeli | answered | 1 | yes | yes | 0.581 | konut-finansmani-yon:m13:f1, 6502:m19:f1 | – |
| b1-032 | cok_maddeli | answered | 2 | yes | yes | 0.633 | 5411:m62:f1, mevduat-yon:m9:f1, mevduat-yon:m9:f3 | – |
| b1-033 | sayisal | answered | 2 | yes | yes | 0.993 | tcmb-ucret-talimat:s9:bc, tcmb-ucret-talimat:s9:bc, tcmb-ucret-talimat:s9:bc | – |
| b1-034 | sayisal | unverified | 2 | no | yes | 0.979 | – | Atıf 2 (tcmb-ucret-talimat:s9:bc): alıntı kaynak metinde birebir geçmiyor. Metinden kelimesi kelimesine kopyala. |
| b1-035 | sayisal | unverified | 2 | no | yes | 0.855 | – | Atıf 1 (tcmb-ucret-talimat:s9:bc): alıntı kaynak metinde birebir geçmiyor. Metinden kelimesi kelimesine kopyala. |
| b1-036 | sayisal | answered | 2 | yes | yes | 0.959 | tcmb-ucret-talimat:s7:bf, tcmb-ucret-teblig:m10:f6, tcmb-ucret-talimat:s8:bl | – |
| b1-037 | sayisal | unverified | 2 | no | yes | 0.364 | – | Cevaptaki şu sayılar atıf yapılan kaynaklarda geçmiyor: 0.05. Yalnızca kaynakta yazan sayıları kullan; hesaplama yapma. |
| b1-038 | sayisal | answered | 1 | yes | yes | 0.308 | tcmb-ucret-talimat:s8:be, tcmb-ucret-teblig:m11:f4 | – |
| b1-039 | sayisal | answered | 2 | yes | yes | 0.986 | tcmb-ucret-talimat:s8:bh, tcmb-ucret-teblig:m11:f6 | – |
| b1-040 | sayisal | answered | 2 | yes | yes | 0.864 | tuketici-kredisi-yon:m18:f2 | – |
| b1-041 | sayisal | answered | 1 | yes | yes | 0.998 | hakem-heyetleri-yon:m6:f2, 6502:m68:f1 | – |
| b1-042 | sayisal | answered | 1 | yes | yes | 0.918 | 6698:m13:f2 | – |
| b1-043 | degisiklik | unverified | 2 | no | yes | 0.990 | – | Atıf 2 (6502:m70:f3): alıntı kaynak metinde birebir geçmiyor. Metinden kelimesi kelimesine kopyala. |
| b1-044 | degisiklik | answered | 1 | yes | yes | 0.760 | tuketici-kredisi-yon:m10:f1, 6502:m22:f3 | – |
| b1-045 | degisiklik | answered | 1 | yes | yes | 0.969 | 6502:m4:f3, 5411:m144:f1 | – |
| b1-046 | degisiklik | answered | 1 | yes | yes | 0.999 | kart-yon:m18:f2 | – |
| b1-047 | degisiklik | unverified | 2 | no | yes | 0.915 | – | Atıf 1 (6502:m24:f1): belge 6502, 6502 \| madde: 24 \| fıkra: 1 değil.; Atıf 2 (6502:m24:f3): belge 6502, 6502 \| madde: 24 \| fıkra: 3 değil.; Atıf 3 (tuketici-kredisi-yon:m24:f4): belge tuketici-kredisi-yon, tuketici-kredisi-yon \| madde: 24 \| fıkra: 4 değil. |
| b1-048 | degisiklik | unverified | 2 | no | yes | 0.665 | – | Atıf 1 (6698:m6:f3): belge 6698, 6698 \| madde: 6 \| fıkra: 3 değil.; Atıf 2 (5411:m73:f3): belge 5411, 5411 \| madde: 73 \| fıkra: 3 değil.; Atıf 3 (6502:m29:f1): belge 6502, 6502 \| madde: 29 \| fıkra: 1 değil. |
| b1-049 | degisiklik | unverified | 2 | no | yes | 0.931 | – | Atıf 1 (6698:m3:f1): belge 6698, 6698 \| madde: 3 \| fıkra: 1 değil.; Atıf 2 (5411:m73:f3): belge 5411, 5411 \| madde: 73 \| fıkra: 3 değil.; Atıf 3 (5464:m23:f1): belge 5464, 5464 \| madde: 23 \| fıkra: 1 değil. |
| b1-050 | degisiklik | unverified | 2 | no | yes | 0.974 | – | Atıf 1 (mesafeli-finansal-yon:m13:f1): alıntı kaynak metinde birebir geçmiyor. Metinden kelimesi kelimesine kopyala.; Atıf 2 (6502:m47:f5): alıntı kaynak metinde birebir geçmiyor. Metinden kelimesi kelimesine kopyala. |
| b1-051 | kapsam_disi | out_of_scope | 1 | – | – | 0.037 | – | – |
| b1-052 | kapsam_disi | answered | 2 | – | – | 0.004 | 6493:m22:f3, 6493:m21:f11, odeme-hizmetleri-yon:m6:f2, odeme-hizmetleri-yon:m6:f1 | – |
| b1-053 | kapsam_disi | out_of_scope | 1 | – | – | 0.060 | – | – |
| b1-054 | kapsam_disi | out_of_scope | 1 | – | – | 0.004 | – | – |
| b1-055 | kapsam_disi | out_of_scope | 1 | – | – | 0.002 | – | – |
| b1-056 | kapsam_disi | out_of_scope | 1 | – | – | 0.038 | – | – |
| b1-057 | kapsam_disi | out_of_scope | 1 | – | – | 0.002 | – | – |
| b1-058 | kapsam_disi | answered | 1 | – | – | 0.022 | tcmb-ucret-talimat:s7:bi | – |
| b1-059 | yanlis_onerme | answered | 1 | yes | yes | 0.667 | 6502:m31:f3, tcmb-ucret-talimat:s8:bg, tcmb-ucret-talimat:s8:bd | – |
| b1-060 | yanlis_onerme | answered | 1 | yes | yes | 0.579 | 6502:m27:f1, 6502:m20:f1 | – |
| b1-061 | yanlis_onerme | answered | 1 | yes | yes | 0.587 | tuketici-kredisi-yon:m26:f4, tuketici-kredisi-yon:m26:f3, 6502:m29:f2 | – |
| b1-062 | yanlis_onerme | out_of_scope | 1 | no | no | 0.045 | – | – |
| b1-063 | yanlis_onerme | answered | 1 | yes | yes | 0.841 | 6493:m20:f5, odeme-hizmetleri-yon:m5:f4, 6493:m14:f3 | – |
| b1-064 | yanlis_onerme | answered | 1 | yes | yes | 0.990 | 5464:m24:f3, 5464:m26:f2, 5464:m26:f5 | – |
