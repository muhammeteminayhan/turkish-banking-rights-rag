# Judge report (M5)

- Run `2026-10-29_184334_e2e`; judge `ollama/qwen3:8b`, rubric 2026-10-29.1; 64 of 64 answers scored.
- Answerable questions: 56. Correct 26/56; correct or partly correct 41/56; wrong 4/56; withheld ("doğrulanamadı") 9/56; refused although answerable 2/56.
- Out-of-scope questions refused: 6/8. False premises corrected: 3/5.
- Refusals, withheld answers and errors are scored by rule. A judge that is also the answering model scores its own answers.

| Category | dogru | kismen | yanlis | dogru_red | yersiz_red | geri_tutuldu | hata |
|---|---|---|---|---|---|---|---|
| cok_maddeli | 2 | 5 | 2 | 0 | 0 | 1 | 0 |
| degisiklik | 0 | 3 | 0 | 0 | 0 | 5 | 0 |
| dogrudan | 17 | 3 | 1 | 0 | 1 | 0 | 0 |
| kapsam_disi | 0 | 0 | 2 | 6 | 0 | 0 | 0 |
| sayisal | 4 | 2 | 1 | 0 | 0 | 3 | 0 |
| yanlis_onerme | 3 | 2 | 0 | 0 | 1 | 0 | 0 |

| Question | Category | Status | Outcome | Judged by | Missing | Unsupported |
|---|---|---|---|---|---|---|
| b1-001 | dogrudan | answered | dogru | ollama/qwen3:8b | f3'teki 'veya mesafeli' ibaresi 7529 sayılı Kanunla eklenmiş | – |
| b1-002 | dogrudan | answered | dogru | ollama/qwen3:8b | – | – |
| b1-003 | dogrudan | answered | dogru | ollama/qwen3:8b | – | – |
| b1-004 | dogrudan | answered | dogru | ollama/qwen3:8b | – | – |
| b1-005 | dogrudan | answered | dogru | ollama/qwen3:8b | sözleşmeyi düzenleyen, bu şartlar olmasaydı sözleşmeyi yapmayacağını ileri süremez | – |
| b1-006 | dogrudan | answered | kismen | ollama/qwen3:8b | Müşteri talep ettiğinde diğer işlemlerle ilgili belgelerin örneğini verme yükümlülüğü | – |
| b1-007 | dogrudan | answered | dogru | ollama/qwen3:8b | borç geri ödeme döneminde yıllık üyelik ücreti alınamaz | – |
| b1-008 | dogrudan | answered | dogru | ollama/qwen3:8b | – | – |
| b1-009 | dogrudan | out_of_scope | yersiz_red | rule | – | – |
| b1-010 | dogrudan | answered | dogru | ollama/qwen3:8b | – | – |
| b1-011 | dogrudan | answered | dogru | ollama/qwen3:8b | – | – |
| b1-012 | dogrudan | answered | dogru | ollama/qwen3:8b | elden, posta yoluyla | – |
| b1-013 | dogrudan | answered | dogru | ollama/qwen3:8b | Örnek hizmetler (sesli menü m7, işaret dili desteği m8:f5) | – |
| b1-014 | dogrudan | answered | dogru | ollama/qwen3:8b | işaret dili çevirisi yapılmış video | – |
| b1-015 | dogrudan | answered | yanlis | ollama/qwen3:8b | TCMB düzenlemesinin (s10:ba) 'hesap işletimi' kaleminin ücret alınamayacağını doğrudan belirtmemesi; Beklenen cevapta yer alan 'hesap işletimi' kaleminin ücret alınamayacağını ifade eden doğrudan yasaklamayı modelin cevabı içermemesi | Modelin cevabı, 'hesap işletim ücretinin mevzuat tarafından yasaklanmamış olup, ancak açıkça bildirilmesi gerekmektedir' ifadesiyle, TCMB düzenlemesinin (s10:ba) kapsamına giren 'hesap işletimi' kalemini doğrudan yasaklamadığını belirtiyor. Ancak bu ifade, beklenen cevapta yer alan 'hesap işletimi' kaleminin ücret alınamayacağını ifade eden doğrudan yasaklamayı ihmal ediyor. |
| b1-016 | dogrudan | answered | dogru | ollama/qwen3:8b | sigorta ve bireysel emeklilik sözleşmelerinde cayma süresi için diğer mevzuattaki tüketici lehine hükümler uygulanır | – |
| b1-017 | dogrudan | answered | dogru | ollama/qwen3:8b | – | – |
| b1-018 | dogrudan | answered | dogru | ollama/qwen3:8b | ilk talep için | – |
| b1-019 | dogrudan | answered | kismen | ollama/qwen3:8b | kuvvetli şüphe varsa sınırlı araştırma yapma; 13 ay içinde düzeltme talebi | – |
| b1-020 | dogrudan | answered | dogru | ollama/qwen3:8b | Beklenen cevapta yer alan 'haklı sebep olmaksızın' ifadesinin doğrudan kullanılması eksik. | – |
| b1-021 | dogrudan | answered | kismen | ollama/qwen3:8b | diğer kanunlardaki saklama hükümleri saklıdır; sebepler ortadan kalkınca şartını vurgulamalı | – |
| b1-022 | dogrudan | answered | dogru | ollama/qwen3:8b | – | – |
| b1-023 | cok_maddeli | answered | yanlis | ollama/qwen3:8b | Ödeme Hizmetleri Yönetmeliği m.54/4'ün 250 TL tutarını da ele alma; 150 TL sınırının geçerli olup olmaması korpustan çözülemez ve sahibin karar vermesi gerektiği ifadesi | Bildirim yapılmamışsa 150 TL sınırı geçerli olmaz ifadesi eksik ve yanlış uygulanmış |
| b1-024 | cok_maddeli | answered | dogru | ollama/qwen3:8b | – | – |
| b1-025 | cok_maddeli | answered | dogru | ollama/qwen3:8b | faiz değişkense tazminat istenemez | – |
| b1-026 | cok_maddeli | answered | kismen | ollama/qwen3:8b | TÜFE artış oranı üzerindeki artışta onay gerektiren durum; 15 gün süreli vazgeçme hakkı | 60 gün süreli vazgeçme hakkı (beklenen cevapta ve kaynak alıntısında bu süre yer almadığı için) |
| b1-027 | cok_maddeli | answered | kismen | ollama/qwen3:8b | Asgari ödeme eksikliği sonucu kredi kartının nakit kullanımına kapatılması ve mal/hizmet alımına kapatılması gibi iki farklı mevzuat maddesinin ayrı ayrı uygulandığı durumun belirtilmemesi; Bir yıl içinde toplam üç kez ödeme eksikliği (yönetmelik) ve üst üste üç kez ödeme eksikliği (kanun) gibi farklı süre ve koşulların belirtilmemesi | – |
| b1-028 | cok_maddeli | answered | kismen | ollama/qwen3:8b | itiraz süresi; uygulama süreci; itirazın icrası durdurmadığı | itiraz kararın icrasını durdurmaz |
| b1-029 | cok_maddeli | answered | kismen | ollama/qwen3:8b | %40 ve üzeri engelli olma belgesinin sunulması şartı | – |
| b1-030 | cok_maddeli | unverified | geri_tutuldu | rule | – | – |
| b1-031 | cok_maddeli | answered | kismen | ollama/qwen3:8b | Tüketici kredisinde faiz/ücret hariç tutma kuralı eksik | – |
| b1-032 | cok_maddeli | answered | yanlis | ollama/qwen3:8b | 10 yıl kuralının en son işlem tarihinden başlayarak hesapta işlem yapılmadığında zamanaşımına uğradığı; ergin olmayanlar adına açılan hesapların zamanaşımı süresinin erginlik tarihine göre başladığı | Çocuğunuzun 10 yaşında açılan hesapta zamanaşımı süresi hesap açıldığı tarihten başlar |
| b1-033 | sayisal | answered | yanlis | ollama/qwen3:8b | 5.000 TL tutarının 8.300 TL ve altı kategorisinde olduğu ve bu kategori için 7,97 TL ücretin geçerli olduğu bilgisi eksik.; 6/1/2026 tarihinden itibaren uygulanan tabloyu doğru şekilde yansıtmadığı için 15,96 TL ücreti yanlış belirtmiş. | 15,96 TL ücreti 5.000 TL tutarına uygulanabilir. Bu ücret 8.300,01-399.000 TL aralığına ait olup 5.000 TL tutarına uygulanamaz. |
| b1-034 | sayisal | unverified | geri_tutuldu | rule | – | – |
| b1-035 | sayisal | unverified | geri_tutuldu | rule | – | – |
| b1-036 | sayisal | answered | dogru | ollama/qwen3:8b | – | – |
| b1-037 | sayisal | unverified | geri_tutuldu | rule | – | – |
| b1-038 | sayisal | answered | dogru | ollama/qwen3:8b | – | – |
| b1-039 | sayisal | answered | dogru | ollama/qwen3:8b | kuruluş, önceden bilgi vererek bu kartları kapatabilir | – |
| b1-040 | sayisal | answered | kismen | ollama/qwen3:8b | fazla tahsil edilirse kredi veren, fazla tutarı tahsil tarihinden iade tarihine kadar akdi faizin yüzde otuz fazlası üzerinden hesaplanan faiziyle birlikte ödemekle yükümlüdür | – |
| b1-041 | sayisal | answered | kismen | ollama/qwen3:8b | Her takvim yılı başında yeniden değerleme oranında artırılan kuralın belirtilmemesi; 2026 yılı tutarının Tebliğ'den kontrol edilmesi önerisinin eksikliği | – |
| b1-042 | sayisal | answered | dogru | ollama/qwen3:8b | – | – |
| b1-043 | degisiklik | unverified | geri_tutuldu | rule | – | – |
| b1-044 | degisiklik | answered | kismen | ollama/qwen3:8b | RG-31/12/2024 ile değiştirilmiştir | – |
| b1-045 | degisiklik | answered | kismen | ollama/qwen3:8b | 7222 sayılı Kanunla BDDK'dan TCMB'ye geçiş | – |
| b1-046 | degisiklik | answered | kismen | ollama/qwen3:8b | talebin alındığı tarihi gösteren imzalı belge veya formun verilmesi; RG-6/7/2018-30470 değişiklik tarihi; 5464:m25:f2 iptal/fesih hakkını süre belirtmeden tanır ifadesi | – |
| b1-047 | degisiklik | unverified | geri_tutuldu | rule | – | – |
| b1-048 | degisiklik | unverified | geri_tutuldu | rule | – | – |
| b1-049 | degisiklik | unverified | geri_tutuldu | rule | – | – |
| b1-050 | degisiklik | unverified | geri_tutuldu | rule | – | – |
| b1-051 | kapsam_disi | out_of_scope | dogru_red | rule | – | – |
| b1-052 | kapsam_disi | answered | yanlis | rule | – | – |
| b1-053 | kapsam_disi | out_of_scope | dogru_red | rule | – | – |
| b1-054 | kapsam_disi | out_of_scope | dogru_red | rule | – | – |
| b1-055 | kapsam_disi | out_of_scope | dogru_red | rule | – | – |
| b1-056 | kapsam_disi | out_of_scope | dogru_red | rule | – | – |
| b1-057 | kapsam_disi | out_of_scope | dogru_red | rule | – | – |
| b1-058 | kapsam_disi | answered | yanlis | rule | – | – |
| b1-059 | yanlis_onerme | answered | kismen | ollama/qwen3:8b | aidatsız kartla değiştirilmesi talebi de yerine getirilmek zorundadır | – |
| b1-060 | yanlis_onerme | answered | dogru | ollama/qwen3:8b | – | konut finansmanı kredileri hariç |
| b1-061 | yanlis_onerme | answered | kismen | ollama/qwen3:8b | Tüketicinin yazılı/kalıcı veri saklayıcısıyla açık talebinin bulunması şartı | – |
| b1-062 | yanlis_onerme | out_of_scope | yersiz_red | rule | – | – |
| b1-063 | yanlis_onerme | answered | dogru | ollama/qwen3:8b | – | – |
| b1-064 | yanlis_onerme | answered | dogru | ollama/qwen3:8b | – | – |
