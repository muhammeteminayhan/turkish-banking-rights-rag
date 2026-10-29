# Judge report (M5)

- Run `2026-10-29_184334_e2e`; judge `gemini/gemini-3.1-flash-lite`, rubric 2f016276873b; 64 of 64 answers scored.
- Answerable questions: 56. Correct 20/56; correct or partly correct 37/56; wrong 8/56; withheld ("doğrulanamadı") 9/56; refused although answerable 2/56.
- Out-of-scope questions refused: 6/8. False premises corrected: 5/6.
- Refusals, withheld answers and errors are scored by rule. A judge that is also the answering model scores its own answers.

| Category | dogru | kismen | yanlis | dogru_red | yersiz_red | geri_tutuldu | hata |
|---|---|---|---|---|---|---|---|
| cok_maddeli | 1 | 4 | 4 | 0 | 0 | 1 | 0 |
| degisiklik | 2 | 1 | 0 | 0 | 0 | 5 | 0 |
| dogrudan | 11 | 8 | 2 | 0 | 1 | 0 | 0 |
| kapsam_disi | 0 | 0 | 2 | 6 | 0 | 0 | 0 |
| sayisal | 4 | 1 | 2 | 0 | 0 | 3 | 0 |
| yanlis_onerme | 2 | 3 | 0 | 0 | 1 | 0 | 0 |

| Question | Category | Status | Outcome | Judged by | Missing | Unsupported |
|---|---|---|---|---|---|---|
| b1-001 | dogrudan | answered | kismen | gemini/gemini-3.1-flash-lite | Geçersizliğin tüketici aleyhine ileri sürülemeyeceği hususu belirtilmemiştir. | – |
| b1-002 | dogrudan | answered | dogru | gemini/gemini-3.1-flash-lite | – | – |
| b1-003 | dogrudan | answered | dogru | gemini/gemini-3.1-flash-lite | – | – |
| b1-004 | dogrudan | answered | dogru | gemini/gemini-3.1-flash-lite | – | – |
| b1-005 | dogrudan | answered | dogru | gemini/gemini-3.1-flash-lite | Sözleşmeyi düzenleyenin, bu şartlar olmasaydı sözleşmeyi yapmayacağını ileri süremeyeceği bilgisi. | – |
| b1-006 | dogrudan | answered | kismen | gemini/gemini-3.1-flash-lite | Müşteri talep ederse yapılan diğer işlemlere ilişkin her türlü belgenin bir örneğinin verilmesi zorunluluğu.; Bankaların müşterilerin sorularını cevaplayacak bir sistem kurma yükümlülüğü. | – |
| b1-007 | dogrudan | answered | kismen | gemini/gemini-3.1-flash-lite | İptal edilen kartın borç geri ödeme döneminde yıllık üyelik ücreti alınamayacağı bilgisi. | – |
| b1-008 | dogrudan | answered | dogru | gemini/gemini-3.1-flash-lite | – | – |
| b1-009 | dogrudan | out_of_scope | yersiz_red | rule | – | – |
| b1-010 | dogrudan | answered | kismen | gemini/gemini-3.1-flash-lite | bir kamu kurum ve kuruluşuna veya üçüncü kişilere ödenen ücretler hariç tutulmalıdır. | – |
| b1-011 | dogrudan | answered | dogru | gemini/gemini-3.1-flash-lite | – | – |
| b1-012 | dogrudan | answered | dogru | gemini/gemini-3.1-flash-lite | Başvurunun elden veya posta yoluyla da yapılabileceği bilgisi eksik. | – |
| b1-013 | dogrudan | answered | dogru | gemini/gemini-3.1-flash-lite | – | – |
| b1-014 | dogrudan | answered | dogru | gemini/gemini-3.1-flash-lite | Gerekli güvenlik önlemlerinin sağlanacağı detayı. | – |
| b1-015 | dogrudan | answered | yanlis | gemini/gemini-3.1-flash-lite | Tebliğe göre mevduat ve katılım fonu hesaplarının işletimi kapsamında ücret alınamayacağı bilgisi. | Banka vadesiz hesap işletim ücretini kesmek mevzuat tarafından yasaklanmamıştır. |
| b1-016 | dogrudan | answered | kismen | gemini/gemini-3.1-flash-lite | Sigorta ve bireysel emeklilik sözleşmelerinde cayma süresi için diğer mevzuattaki tüketici lehine hükümlerin uygulanacağına dair bilgi. | Bu hakkınızı kullanmak için sağlayıcının bilgilendirmesini doğrulayıp |
| b1-017 | dogrudan | answered | dogru | gemini/gemini-3.1-flash-lite | – | – |
| b1-018 | dogrudan | answered | kismen | gemini/gemini-3.1-flash-lite | Ücret alınmama kuralının 'bir defaya mahsus' olduğu belirtilmelidir. | Kredi ile ilgili işlemler için ücret alınmaz. |
| b1-019 | dogrudan | answered | kismen | gemini/gemini-3.1-flash-lite | 54/5 maddesinde sayılan hileli kullanım veya kasten/ağır ihmal durumlarında bankanın makul bir süre araştırma yapma hakkı olduğu bilgisi. | – |
| b1-020 | dogrudan | answered | yanlis | gemini/gemini-3.1-flash-lite | Sözleşmede haklı bir sebep belirtilmediği durumun vurgulanması | kredi kartı sözleşmesinde 'banka sözleşme şartlarını dilediği zaman tek taraflı değiştirebilir' ifadesi haksız şart sayılır. |
| b1-021 | dogrudan | answered | kismen | gemini/gemini-3.1-flash-lite | Diğer kanunlardaki saklama hükümlerinin saklı olduğu bilgisi | – |
| b1-022 | dogrudan | answered | dogru | gemini/gemini-3.1-flash-lite | – | – |
| b1-023 | cok_maddeli | answered | kismen | gemini/gemini-3.1-flash-lite | Ödeme Hizmetleri Yönetmeliği m.54/4'teki 250 TL'lik sınır ve bildirim sonrası sorumluluğun kalkması kuralı; Hamilin ağır ihmali veya kastı durumunun sorumluluğa etkisi | bildirim yapılmazsa, hukuka aykırı kullanımdan doğan zararlar tamamen size aittir |
| b1-024 | cok_maddeli | answered | yanlis | gemini/gemini-3.1-flash-lite | İade yükümlülüğünün bankaya ait olduğu açıkça belirtilmeli, tüketicinin bankaya bir şey iade etmeyeceği netleştirilmeliydi. | Diğer ücretler 7 gün içinde bankaya iade etmelisin. |
| b1-025 | cok_maddeli | answered | dogru | gemini/gemini-3.1-flash-lite | – | – |
| b1-026 | cok_maddeli | answered | yanlis | gemini/gemini-3.1-flash-lite | Artışın TÜFE oranının üzerinde olması durumunda tüketiciden ayrıca onay alınması gerektiği bilgisi.; Bildirimden itibaren 15 gün içinde vazgeçme hakkı olduğu bilgisi.; Hizmeti kullanmaya devam etmenin değişikliği kabul etmiş sayılacağı bilgisi.; Kuruluşun hizmeti durdurabileceği bilgisi. | Kabul etmezseniz, bildirim tarihinden itibaren en geç 60 gün içinde tüm borcunu ödediyseniz ve kredi kartını kullanmayı bırakırsanız, faiz artışından etkilenmez.; yeni faiz oranı geriye dönük olarak uygulanamaz |
| b1-027 | cok_maddeli | answered | kismen | gemini/gemini-3.1-flash-lite | Dönem borcunun tamamı ödenene kadar limit artırılmayacağı bilgisi eksiktir.; Yeni kart düzenlenememesi yaptırımının ilgili kuruluş ile sınırlı olduğu vurgusu eksiktir. | – |
| b1-028 | cok_maddeli | answered | yanlis | gemini/gemini-3.1-flash-lite | Kararın İcra ve İflas Kanununun ilamların yerine getirilmesine ilişkin hükümlerine göre yerine getirileceği bilgisi eksik. | Bankaya ödenmesini talep edebilirsiniz.; Banka ödemeyi sürdürüyorsa, kararın tebliğ tarihinden itibaren iki hafta içinde tüketici mahkemesine itiraz edebilirsiniz.; Kararın icrası için tüketici mahkemesine başvurarak uygulama sürecini başlatmanız gerekir. |
| b1-029 | cok_maddeli | answered | kismen | gemini/gemini-3.1-flash-lite | %40 ve üzeri engelli olduğuna dair belge ibrazı şartı; Belgenin aslının veya onaylı suretinin sunulması gerektiği; 70 yaş ve üzeri kişilerin bildirim yapmadan bu haktan yararlanabileceği bilgisi | – |
| b1-030 | cok_maddeli | unverified | geri_tutuldu | rule | – | – |
| b1-031 | cok_maddeli | answered | kismen | gemini/gemini-3.1-flash-lite | Banka hakkı sözleşmede saklı tutmuşsa kullanabilir; Banka tüm edimlerini ifa etmiş olmalıdır; Tüketici kredisinde muaccel kılınan taksit hesaplamasında faiz ve ücretlerin dikkate alınmaması | 6502 sayılı Kanun md. 19/1'in tüketici kredileri için geçerli olduğu (bu madde taksitli satış sözleşmeleri ile ilgilidir) |
| b1-032 | cok_maddeli | answered | yanlis | gemini/gemini-3.1-flash-lite | Ergin olmayanlar adına açtırılan hesaplarda zamanaşımının kişinin ergin olduğu tarihte işlemeye başlayacağı bilgisi. | Çocuğunuzun 10 yaşında açılan hesapta zamanaşımı süresi hesap açıldığı tarihten başlar.; Bloke hesaplarda zamanaşımı, blok kaldırıldığında devam eder.; Sorudaki varsayım kaynaklarla çelişiyor. |
| b1-033 | sayisal | answered | yanlis | gemini/gemini-3.1-flash-lite | Doğru ücret tutarı olan 7,97 TL bilgisi eksiktir. | 5.000 TL EFT gönderimi için 2026'da banka en fazla 15,96 TL ücret alabilir. |
| b1-034 | sayisal | unverified | geri_tutuldu | rule | – | – |
| b1-035 | sayisal | unverified | geri_tutuldu | rule | – | – |
| b1-036 | sayisal | answered | kismen | gemini/gemini-3.1-flash-lite | Taksitli nakit avans işlemleri için ücret tahsil edilemeyeceği net bir şekilde belirtilmemiştir. | Taksitli nakit avans kullanıldığında, bu taksitlerle ilgili hizmetlerden (örn. ödeme tarihlerinin uzatılması) ücret alınmaz. |
| b1-037 | sayisal | unverified | geri_tutuldu | rule | – | – |
| b1-038 | sayisal | answered | dogru | gemini/gemini-3.1-flash-lite | – | – |
| b1-039 | sayisal | answered | dogru | gemini/gemini-3.1-flash-lite | – | – |
| b1-040 | sayisal | answered | dogru | gemini/gemini-3.1-flash-lite | Fazla tahsilat durumunda kredi verenin iade yükümlülüğü ve bu tutarın hesaplanma yöntemi. | – |
| b1-041 | sayisal | answered | yanlis | gemini/gemini-3.1-flash-lite | Parasal sınırın her yıl yeniden değerleme oranında arttırıldığı bilgisi eksik.; 2026 yılı için geçerli tutarın güncel Tebliğ'den kontrol edilmesi gerektiği uyarısı eksik. | 2026 yılında tüketici hakem heyetine 30.000 TL'ye kadar olan uyuşmazlıklar için başvuru yapılabilir. |
| b1-042 | sayisal | answered | dogru | gemini/gemini-3.1-flash-lite | Talebin niteliğine göre sonuçlandırılacağı ifadesi. | – |
| b1-043 | degisiklik | unverified | geri_tutuldu | rule | – | – |
| b1-044 | degisiklik | answered | kismen | gemini/gemini-3.1-flash-lite | Geçerli sözleşme yapmamış kredi verenin, geçersizliği tüketici aleyhine ileri süremeyeceği bilgisi. | ancak mesafeli sözleşme formatı mevzuatın kabul ettiği şekilde (örneğin dijital imza, saklanabilir veri) olmalıdır |
| b1-045 | degisiklik | answered | dogru | gemini/gemini-3.1-flash-lite | Bakanlığın görüşü alınarak belirlendiği bilgisi. | – |
| b1-046 | degisiklik | answered | dogru | gemini/gemini-3.1-flash-lite | Şubeden yapılan limit azaltma veya iptal taleplerinde, talebin alındığı tarihi gösteren imzalı bir belge veya doldurulan formun bir örneğinin kart hamiline verilmesi gerektiği bilgisi. | – |
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
| b1-059 | yanlis_onerme | answered | kismen | gemini/gemini-3.1-flash-lite | Aidatlı kartın, limit aynı kalmak kaydıyla aidatsız kartla değiştirilmesi talebinin yerine getirilmek zorunda olduğu bilgisi. | – |
| b1-060 | yanlis_onerme | answered | kismen | gemini/gemini-3.1-flash-lite | – | Bu kural, konut finansmanı kredileri hariç genel tüketici kredileri için geçerlidir. |
| b1-061 | yanlis_onerme | answered | kismen | gemini/gemini-3.1-flash-lite | Tüketicinin yazılı veya kalıcı veri saklayıcısı ile açık talebi olmadan kredi bağlantılı sigorta yaptırılamayacağı bilgisi.; Banka sigortalı kredi sunuyorsa, sigortasız kredi de teklif etmek zorunda olduğu bilgisi. | – |
| b1-062 | yanlis_onerme | out_of_scope | yersiz_red | rule | – | – |
| b1-063 | yanlis_onerme | answered | dogru | gemini/gemini-3.1-flash-lite | – | – |
| b1-064 | yanlis_onerme | answered | dogru | gemini/gemini-3.1-flash-lite | – | – |
