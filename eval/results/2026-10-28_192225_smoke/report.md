# Smoke run (M4)

- Provider: `ollama`, model `qwen3:8b`; retrieval config `full`; thinking: False.
- Questions: 20; status: {'answered': 4, 'unverified': 2, 'error': 12, 'out_of_scope': 2}.
- Verified answers that cite an expected article: 3/17 (retrieval had it: 6/17).
- Answers verified on the first try: 4/4; false refusals of answerable questions: 0/17.
- Out-of-scope questions refused: 2/3.
- Tokens: {'input': 36021, 'output': 2534}; cost: 0.0 USD.
- Latency p50 0 ms, p95 488715 ms.

| Question | Category | Status | Attempts | Expected cited | Retrieved | Top score | Cited | Verification errors |
|---|---|---|---|---|---|---|---|---|
| b1-001 | dogrudan | answered | 1 | yes | yes | 0.956 | 6502:m22:f1, 6502:m22:f2, 6502:m22:f3 | – |
| b1-003 | dogrudan | unverified | 2 | no | yes | 0.862 | – | Atıf 1 (5464:m10:f1): fıkra 1, None değil. |
| b1-007 | dogrudan | error | 0 | no | – | – | – | LLMError: Ollama did not answer within 300 s |
| b1-011 | dogrudan | error | 0 | no | – | – | – | LLMError: Ollama did not answer within 300 s |
| b1-016 | dogrudan | error | 0 | no | – | – | – | LLMError: Ollama did not answer within 300 s |
| b1-021 | dogrudan | error | 0 | no | – | – | – | LLMError: Ollama did not answer within 300 s |
| b1-024 | cok_maddeli | error | 0 | no | – | – | – | LLMError: Ollama did not answer within 300 s |
| b1-025 | cok_maddeli | error | 0 | no | – | – | – | LLMError: Ollama did not answer within 300 s |
| b1-027 | cok_maddeli | error | 0 | no | – | – | – | LLMError: Ollama did not answer within 300 s |
| b1-033 | sayisal | error | 0 | no | – | – | – | LLMError: Ollama did not answer within 300 s |
| b1-036 | sayisal | answered | 1 | yes | yes | 0.959 | tcmb-ucret-talimat:s7:bf, tcmb-ucret-teblig:m10:f6 | – |
| b1-039 | sayisal | unverified | 2 | no | yes | 0.986 | – | Cevaptaki şu sayılar atıf yapılan kaynaklarda geçmiyor: 100. Yalnızca kaynakta yazan sayıları kullan; hesaplama yapma. |
| b1-045 | degisiklik | error | 0 | no | – | – | – | LLMError: Ollama did not answer within 300 s |
| b1-046 | degisiklik | answered | 1 | yes | yes | 0.999 | kart-yon:m18:f2 | – |
| b1-051 | kapsam_disi | error | 0 | – | – | – | – | LLMError: Ollama did not answer within 300 s |
| b1-053 | kapsam_disi | out_of_scope | 1 | – | – | 0.060 | – | – |
| b1-056 | kapsam_disi | out_of_scope | 1 | – | – | 0.038 | – | – |
| b1-059 | yanlis_onerme | error | 0 | no | – | – | – | LLMError: Ollama did not answer within 300 s |
| b1-060 | yanlis_onerme | error | 0 | no | – | – | – | LLMError: Ollama did not answer within 300 s |
| b1-064 | yanlis_onerme | answered | 1 | no | yes | 0.990 | 5464:m26:f2, 5464:m26:f5 | – |
