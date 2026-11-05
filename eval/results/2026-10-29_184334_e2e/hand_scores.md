# Elle puanlama: 2026-10-29_184334_e2e

Bu çalıştırmada kullanıcıya ulaşan cevaplardan 30 tanesi (kategoriye göre tabakalı örneklem, seed 42). Hakemlerin puanları bilerek gösterilmiyor.

Her cevabın altındaki "Puanın:" satırına `doğru`, `kısmen` veya `yanlış` yaz (kısaca d / k / y); istersen "Not:" satırına kısa bir gerekçe. Ölçüt hakeminkiyle aynı:

- **doğru:** beklenen cevabın ana sonucu ve önemli unsurları cevapta var; beklenenle çelişen ya da kaynağı olmayan bir iddia yok.
- **kısmen:** ana sonuç doğru, ama önemli bir unsur eksik, kaynağı olmayan bir iddia var ya da cevap kendi içinde çelişiyor.
- **yanlış:** ana sonuç beklenenle çelişiyor; bir tutar, oran veya süre yanlış; başka bir ürünün kuralı uygulanmış ya da sorudaki yanlış varsayım onaylanmış.

Beklenen cevabı ve alıntıları ölçü al: hakem de yalnızca bunları görüyor. Boş bıraktığın cevaplar sayılmaz.

Bitince: `python eval/hand_sheet.py score <bu klasör>`.

---

## b1-001 · doğrudan bilgi

**Soru:** 6502 sayılı Kanunun 22. maddesi neyi düzenliyor?

*Beklenen cevabı yazanın notu:* Madde atıflı soru; maddenin üç fıkrasının tamamı gerekir. f3'teki 'veya mesafeli' ibaresi 7529 sayılı Kanunla eklenmiş (chunk notu).

**Beklenen cevap:** Tüketici kredisi sözleşmesini tanımlar: kredi verenin tüketiciye faiz veya benzeri bir menfaat karşılığında ödemenin ertelenmesi, ödünç veya benzeri finansman yoluyla kredi verdiği ya da vermeyi taahhüt ettiği sözleşme. Kredi kartı sözleşmeleri, ödemenin üç aydan uzun ertelenmesi veya taksit imkânı sağlanması hâlinde tüketici kredisi sayılır; bu durumda faiz, kart sözleşmesindeki orandan fazla olamaz. Sözleşme yazılı veya mesafeli kurulmadıkça geçerli olmaz; geçersizlik tüketici aleyhine ileri sürülemez.

**Kaynak alıntıları:**
- `6502:m22:f1`: “kredi verenin tüketiciye faiz veya benzeri bir menfaat karşılığında ödemenin ertelenmesi, ödünç veya benzeri finansman şekilleri aracılığıyla kredi verdiği veya kredi vermeyi taahhüt ettiği sözleşmeyi ifade eder”
- `6502:m22:f2`: “ödemenin üç aydan daha uzun süre ertelenmesi veya benzer şekilde taksitle ödeme imkânı sağlanması hâlinde tüketici kredisi sözleşmesi olarak değerlendirilir”
- `6502:m22:f3`: “Tüketici kredisi sözleşmesi yazılı veya mesafeli olarak kurulmadıkça geçerli olmaz.”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> 6502 sayılı Kanunun 22. maddesi tüketici kredisi sözleşmelerini düzenler. Bu maddede, kredi verenin tüketiciye faiz karşılığında ödemenin ertelenmesi veya finansman şekilleriyle kredi verdiği sözleşmelerin tüketici kredisi sözleşmesi olarak değerlendirilmesi, kredi kartı sözleşmelerinin bu kapsamda yer alması ve sözleşmelerin yazılı veya mesafeli olarak kurulması gerekliliği belirtilmektedir.
>
> Kaynaklar:
> [1] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 22/1
>     “Tüketici kredisi sözleşmesi, kredi verenin tüketiciye faiz veya benzeri bir menfaat karşılığında ödemenin ertelenmesi, ödünç veya benzeri finansman şekilleri aracılığıyla kredi verdiği veya kredi vermeyi taahhüt ettiği sözleşmeyi ifade eder.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5
> [2] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 22/2
>     “Kredi kartı sözleşmeleri, faiz veya benzeri bir menfaat karşılığında, ödemenin üç aydan daha uzun süre ertelenmesi veya benzer şekilde taksitle ödeme imkânı sağlanması hâlinde tüketici kredisi sözleşmesi olarak değerlendirilir.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5
> [3] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 22/3
>     “Tüketici kredisi sözleşmesi yazılı veya mesafeli olarak kurulmadıkça geçerli olmaz.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-002 · doğrudan bilgi

**Soru:** Tüketici Kredisi Sözleşmeleri Yönetmeliği 9. madde ne diyor? Kredi başvurum reddedilirse banka bana haber vermek zorunda mı?

*Beklenen cevabı yazanın notu:* Madde atıflı soru; madde tek fıkradır. Ret gerekçesinin bildirilmesi konusunda metin bir şey söylemiyor.

**Beklenen cevap:** Evet. Kredi talebi reddedilirse kredi veren tüketiciyi yazılı olarak veya kalıcı veri saklayıcısı ile derhal ve ücretsiz bilgilendirmek zorundadır.

**Kaynak alıntıları:**
- `tuketici-kredisi-yon:m9:f1`: “kredi verenin yazılı olarak veya kalıcı veri saklayıcısı ile tüketiciyi derhal ve ücretsiz olarak bilgilendirmesi zorunludur”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Evet, Tüketici Kredisi Sözleşmeleri Yönetmeliği 9. maddesine göre kredi başvurunuz reddedilirse banka size yazılı olarak veya kalıcı veri saklayıcısıyla derhal ve ücretsiz olarak haber vermek zorundadır.
>
> Kaynaklar:
> [1] Tüketici Kredisi Sözleşmeleri Yönetmeliği md. 9/1
>     “Tüketicinin kredi talebinin reddedildiği durumlarda; kredi verenin yazılı olarak veya kalıcı veri saklayıcısı ile tüketiciyi derhal ve ücretsiz olarak bilgilendirmesi zorunludur.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20767&MevzuatTur=7&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-003 · doğrudan bilgi

**Soru:** 5464 m.10 ne diyor?

*Beklenen cevabı yazanın notu:* Kısa biçimli madde atfı (m.10). 5464 chunk'larında fıkra numarası çıkarımsal (fikra_inferred=true); m10 tek fıkra olduğundan sorun yok.

**Beklenen cevap:** Kredi kartı hesap özeti (ekstre) düzenlenmesi ve bunun yazılı olarak ya da kart hamilinin talebi üzerine elektronik ortam veya başka etkin yollarla bildirilmesi zorunludur; usul ve esasları Kurul belirler.

**Kaynak alıntıları:**
- `5464:m10:f1`: “kredi kartı hesap özeti düzenlenmesi, yazılı veya kart hamilinin talebi üzerine elektronik ortam veya başka etkin yollarla bildirilmesi zorunludur”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> 5464 sayılı Banka Kartları ve Kredi Kartları Kanunu'nun 10. maddesi, kredi kartı hesap özeti düzenlenmesini Kurulca belirlenecek usûl ve esaslar çerçevesinde, yazılı veya kart hamilinin talebi üzerine elektronik ortam veya başka etkin yollarla bildirilmesi zorunluluğunu öngörür.
>
> Kaynaklar:
> [1] 5464 sayılı Banka Kartları ve Kredi Kartları Kanunu md. 10/1
>     “Kurulca belirlenecek usûl ve esaslar çerçevesinde, kredi kartı hesap özeti düzenlenmesi, yazılı veya kart hamilinin talebi üzerine elektronik ortam veya başka etkin yollarla bildirilmesi zorunludur.”
>     Fıkra numarası kaynak metinde yazmıyor; maddenin paragrafları sayılarak bulundu.
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=5464&MevzuatTur=1&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-004 · doğrudan bilgi

**Soru:** KVKK'nın 11. maddesine göre bankaya başvurup kişisel verilerimle ilgili neler isteyebilirim?

*Beklenen cevabı yazanın notu:* Madde atıflı soru; tüm haklar tek fıkranın (a)-(ğ) bentlerinde.

**Beklenen cevap:** Veri sorumlusuna başvurarak: verinizin işlenip işlenmediğini öğrenme, işlenmişse bilgi isteme, işlenme amacını ve amaca uygun kullanılıp kullanılmadığını öğrenme, yurt içi/yurt dışında aktarıldığı üçüncü kişileri bilme, eksik veya yanlışsa düzeltilmesini isteme, 7. madde şartlarında silinmesini veya yok edilmesini isteme, bu düzeltme/silme işlemlerinin aktarılan üçüncü kişilere bildirilmesini isteme, münhasıran otomatik sistemlerle analiz sonucu aleyhinize çıkan sonuca itiraz etme ve kanuna aykırı işleme nedeniyle zarara uğradıysanız zararın giderilmesini talep etme haklarınız vardır.

**Kaynak alıntıları:**
- `6698:m11:f1`: “Kişisel veri işlenip işlenmediğini öğrenme”
- `6698:m11:f1`: “Kişisel verilerin eksik veya yanlış işlenmiş olması hâlinde bunların düzeltilmesini isteme”
- `6698:m11:f1`: “zarara uğraması hâlinde zararın giderilmesini talep etme”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> KVKK'nın 11. maddesi uyarınca bankaya başvurarak kişisel verilerinizle ilgili; veri işlenip işlenmediğini öğrenme, verilerin işlenme amacını ve kullanımını öğrenme, verilerin aktarıldığı üçüncü kişileri bilme, eksik/yanlış verilerin düzeltilmesini isteme, verilerin silinmesini veya yok edilmesini isteme, işlemlerin üçüncü kişilere bildirilmesini isteme, otomatik analizlerden kaynaklanan sonuçlara itiraz etme ve kanuna aykırı işlenmesi sebebiyle zarar giderilmesini talep etme haklarına sahipsiniz.
>
> Kaynaklar:
> [1] 6698 sayılı Kişisel Verilerin Korunması Kanunu md. 11/1
>     “Herkes, veri sorumlusuna başvurarak kendisiyle ilgili;
> a) Kişisel veri işlenip işlenmediğini öğrenme,
> b) Kişisel verileri işlenmişse buna ilişkin bilgi talep etme,
> c) Kişisel verilerin işlenme amacını ve bunların amacına uygun kullanılıp kullanılmadığını öğrenme,
> ç) Yurt içinde veya yurt dışında kişisel verilerin aktarıldığı üçüncü kişileri bilme,
> d) Kişisel verilerin eksik veya yanlış işlenmiş olması hâlinde bunların düzeltilmesini isteme,
> e) 7 nci maddede öngörülen şartlar çerçevesinde kişisel verilerin silinmesini veya yok edilmesini isteme,
> f) (d) ve (e) bentleri uyarınca yapılan işlemlerin, kişisel verilerin aktarıldığı üçüncü kişilere bildirilmesini isteme,
> g) İşlenen verilerin münhasıran otomatik sistemler vasıtasıyla analiz edilmesi suretiyle kişinin kendisi aleyhine bir sonucun ortaya çıkmasına itiraz etme,
> ğ) Kişisel verilerin kanuna aykırı olarak işlenmesi sebebiyle zarara uğraması hâlinde zararın giderilmesini talep etme,
> haklarına sahiptir.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6698&MevzuatTur=1&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-010 · doğrudan bilgi

**Soru:** Kredi başvurum reddedildi ama banka yine de dosya masrafı istiyor. Reddedilen kredi için ücret alınabilir mi?

*Beklenen cevabı yazanın notu:* tcmb-ucret-talimat:s7:bc aynı cümle.

**Beklenen cevap:** Hayır. Reddedilen kredi taleplerinden, bir kamu kurum ve kuruluşuna veya üçüncü kişilere ödenen ücretler hariç, herhangi bir ücret alınamaz.

**Kaynak alıntıları:**
- `tcmb-ucret-teblig:m10:f3`: “Reddedilen kredi taleplerinden bir kamu kurum ve kuruluşuna veya üçüncü kişilere ödenen ücretler hariç olmak üzere herhangi bir ücret alınamaz.”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Reddedilen kredi başvurusu için banka dosya masrafı gibi herhangi bir ücret alamaz. Kaynaklara göre reddedilen kredi taleplerinden ücret alınması yasaklanmıştır.
>
> Kaynaklar:
> [1] Ücret Tebliği Uygulama Talimatı (TCMB, 13.01.2026) md. 7 (c)
>     “Reddedilen kredi taleplerinden bir kamu kurum ve kuruluşuna veya üçüncü kişilere ödenen ücretler hariç olmak üzere herhangi bir ücret alınamaz.”
>     13.01.2026 tarihli sürüm, 23.10.2026 tarihinde alındı. https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Banka+Hakkinda/Mevzuat/Bankacilik/
> [2] Finansal Tüketicilerden Alınacak Ücretler Tebliği (2020/7) md. 10/3
>     “Reddedilen kredi taleplerinden bir kamu kurum ve kuruluşuna veya üçüncü kişilere ödenen ücretler hariç olmak üzere herhangi bir ücret alınamaz.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=34343&MevzuatTur=9&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-011 · doğrudan bilgi

**Soru:** Bankam ben istemeden kredi kartı limitimi yükseltti. Bunu yapmaya hakları var mı?

*Beklenen cevabı yazanın notu:* kart-yon:m22:f2, müşterinin genel nitelikli talimatı varsa 15 gün önceden bildirimle periyodik limit artırımına izin verir; müşteri böyle bir talimat verdiyse cevap değişebilir.

**Beklenen cevap:** Hayır. Kart çıkaran kuruluşlar, kart hamili talep etmedikçe kart limitini artıramaz.

**Kaynak alıntıları:**
- `5464:m9:f1`: “Kart çıkaran kuruluşlar, kart hamilleri talep etmedikçe kart limitlerini artıramazlar.”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Bankanın kredi kartı limitini istemeden artırmaya hakkı yoktur. Kaynaklara göre kart çıkaran kuruluşlar, kart hamileri talep etmedikçe kredi kartı limitlerini artıramazlar.
>
> Kaynaklar:
> [1] Banka Kartları ve Kredi Kartları Hakkında Yönetmelik md. 22/2
>     “Kart çıkaran kuruluşlar, kart hamilleri talep etmedikçe kredi kartı kart limitlerini artıramazlar.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=11180&MevzuatTur=7&MevzuatTertip=5
> [2] 5464 sayılı Banka Kartları ve Kredi Kartları Kanunu md. 9/1
>     “Kart çıkaran kuruluşlar, kart hamilleri talep etmedikçe kart limitlerini artıramazlar.”
>     Fıkra numarası kaynak metinde yazmıyor; maddenin paragrafları sayılarak bulundu.
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=5464&MevzuatTur=1&MevzuatTertip=5
> [3] Banka Kartları ve Kredi Kartları Hakkında Yönetmelik md. 17/5
>     “Kart hamilinden talep alınmadıkça kart limitlerinin artırılamayacağına”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=11180&MevzuatTur=7&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-013 · doğrudan bilgi

**Soru:** Engelli bir müşteriyim. Bankanın bana sunduğu kolaylaştırıcı hizmetler (ör. sesli yönlendirme, işaret dili desteği) için benden ekstra ücret istemesi doğru mu?

*Beklenen cevabı yazanın notu:* Örnek hizmetler (sesli menü m7, işaret dili desteği m8:f5) Yönetmelikte düzenlenmiş hizmetlerdir.

**Beklenen cevap:** Hayır. Banka, engelli müşterilerine Yönetmelik çerçevesinde sunduğu kullanımı kolaylaştırıcı veya bilgilendirici hizmetler için ek ücret talep edemez.

**Kaynak alıntıları:**
- `erisilebilirlik-yon:m4:f11`: “Banka, engelli müşterilerine bu Yönetmelik çerçevesinde sunduğu kullanımı kolaylaştırıcı veya bilgilendirici hizmetler dolayısıyla, müşterilerinden ek ücret talep edemez.”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Banka, engelli müşterilere sunduğu kolaylaştırıcı hizmetler (örneğin sesli yönlendirme, işaret dili desteği) için ek ücret isteyemez. Bu hizmetler, yasal zorunluluklar doğrultusunda ücretsiz sunulur.
>
> Kaynaklar:
> [1] Bankacılık Hizmetlerinin Erişilebilirliğine Dair Yönetmelik md. 4/11
>     “Banka, engelli müşterilerine bu Yönetmelik çerçevesinde sunduğu kullanımı kolaylaştırıcı veya bilgilendirici hizmetler dolayısıyla, müşterilerinden ek ücret talep edemez.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=38873&MevzuatTur=7&MevzuatTertip=5
> [2] Bankacılık Hizmetlerinin Erişilebilirliğine Dair Yönetmelik md. 4/4
>     “Banka, sunduğu bankacılık hizmetlerine yönelik erişim, kullanım ve güvenlik ile ilgili hususlarda engelli müşterilerini bilgilendirir.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=38873&MevzuatTur=7&MevzuatTertip=5
> [3] Bankacılık Hizmetlerinin Erişilebilirliğine Dair Yönetmelik md. 5/6
>     “Engelli müşteriler, engel durumuna ilişkin bilgi bankada mevcutsa, asgari olarak kendi hesaplarıyla ilgili bakiye sorgulamak, para çekmek, para yatırmak, kredi kartı borcu sorgulamak ve kredi kartı borcu ödemek için, yurt içinde kurulu tüm ATM’leri herhangi bir ek masraf ve ücrete tabi olmadan kullanırlar.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=38873&MevzuatTur=7&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-014 · doğrudan bilgi

**Soru:** Görme engelliyim. Kredi sözleşmemi ve hesap özetimi Braille alfabesiyle ya da sesli olarak isteyebilir miyim?

**Beklenen cevap:** Evet. Sözleşmeler, hesap özeti, PIN, parola gibi müşteriye iletilen bilgi ve dokümanlar, talep hâlinde ve gerekli güvenlik sağlanarak engelli müşterilere Braille alfabesi, sesli bilgilendirme, işaret dili çevirili video gibi farklı biçimlerde sunulur.

**Kaynak alıntıları:**
- `erisilebilirlik-yon:m4:f7`: “talep halinde, gerekli güvenlik sağlanarak engelli müşterilere Braille alfabesi, sesli bilgilendirme, işaret dili çevirisi yapılmış video gibi farklı biçimlerde sunulur”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Evet, görme engelli müşterilere kredi sözleşmeleri ve hesap özetleri Braille alfabesiyle ya da sesli bilgilendirme biçimlerinde talep edilebilir.
>
> Kaynaklar:
> [1] Bankacılık Hizmetlerinin Erişilebilirliğine Dair Yönetmelik md. 4/7
>     “Bankacılık hizmetlerine ilişkin sözleşmeler, hesap özeti, PIN, parola gibi müşteriye iletilen bilgi ve dokümanlar, talep halinde, gerekli güvenlik sağlanarak engelli müşterilere Braille alfabesi, sesli bilgilendirme, işaret dili çevirisi yapılmış video gibi farklı biçimlerde sunulur.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=38873&MevzuatTur=7&MevzuatTertip=5
> [2] Bankacılık Hizmetlerinin Erişilebilirliğine Dair Yönetmelik md. 8/4
>     “Görme engelli müşteriler, bankacılık hizmetlerine ilişkin sözleşmelerle ilgili bilgi edinme ve inceleme haklarını kullanmaları akabinde sözleşmeye imza atabilirler. Bu kapsamda, kişinin talebi olmaksızın, engelli müşterilere yönelik farklı bir uygulamaya gidilmez.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=38873&MevzuatTur=7&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-015 · doğrudan bilgi

**Soru:** Vadesiz hesabımdan her ay 'hesap işletim ücreti' kesiliyor. Banka bu ücreti alabilir mi?

*Beklenen cevabı yazanın notu:* tcmb-ucret-talimat:s10:ba aynı metin. Kesilen ücretin gerçekte başka bir kalem (ör. paket ürün, s12:ba) olup olmadığı metinden anlaşılamaz; cevap yalnızca 'hesap işletimi' kalemi için.

**Beklenen cevap:** Tebliğe göre mevduat ve katılım fonu hesaplarının açılışındaki operasyonel süreçler ile hesapların işletimi, işletime hazır bulundurulması, saklama hizmeti ve bilgi işlem sistemi yatırımları kapsamında ücret alınamaz.

**Kaynak alıntıları:**
- `tcmb-ucret-teblig:m13:f1`: “hesapların işletimi, hesapların işletime hazır bulundurulması, saklama hizmeti verilmesi ve bilgi işlem sistemi yatırımları kapsamında ücret alınamaz”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Banka vadesiz hesap işletim ücretini kesmek mevzuat tarafından yasaklanmamıştır. Ancak bu ücretin hesap sahibine açıkça bildirilmesi ve anlaşmaya dahil edilmesi gerekmektedir.
>
> Kaynaklar:
> [1] Ödeme Hizmetleri ve Elektronik Para İhracı Yönetmeliği md. 50/4
>     “Ödeme hizmeti sağlayıcısı, çerçeve sözleşmedeki bildirim yükümlülüklerine ek olarak, müşteriye, ödeme hizmetinden faydalanması için sunduğu tüm hizmet kalemlerine ilişkin toplam maliyet ve kullanım miktarının görüleceği, tahakkuk ettirilen aylık ve yıllık ücretler, indirimler, kesintiler, işlem ücretleri, hesap işletim ücretleri, komisyonlar, sadakat puanları gibi kırılımları ayrı ayrı içeren bir ekstreyi, müşterinin tercihine göre basılı olarak veya kalıcı veri saklayıcısı ile ve her iki durumda da ücretsiz olarak sunmak zorundadır.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=39080&MevzuatTur=7&MevzuatTertip=5
> [2] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 4/3
>     “Tüketiciden; kendisine sunulan mal veya hizmet kapsamında haklı olarak yapılmasını beklediği ve sözleşmeyi düzenleyenin yasal yükümlülükleri arasında yer alan edimler ile sözleşmeyi düzenleyenin kendi menfaati doğrultusunda yapmış olduğu masraflar için ek bir bedel talep edilemez.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-017 · doğrudan bilgi

**Soru:** Kredi sözleşmemdeki bir madde muğlak, iki farklı anlama gelebiliyor. Bu durumda madde kimin lehine yorumlanır?

*Beklenen cevabı yazanın notu:* haksiz-sartlar-yon:m6:f3 aynı cümle.

**Beklenen cevap:** Açık ve anlaşılır olmayan veya birden çok anlama gelen hüküm tüketicinin lehine yorumlanır.

**Kaynak alıntıları:**
- `6502:m5:f4`: “Sözleşmede yer alan bir hükmün açık ve anlaşılır olmaması veya birden çok anlama gelmesi hâlinde; bu hüküm, tüketicinin lehine yorumlanır.”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Kredi sözleşmesinde muğlak veya iki anlama gelebilen bir madde, tüketicinin lehine yorumlanır.
>
> Kaynaklar:
> [1] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 5/4
>     “Sözleşme şartlarının yazılı olması hâlinde, tüketicinin anlayabileceği açık ve anlaşılır bir dilin kullanılmış olması gerekir. Sözleşmede yer alan bir hükmün açık ve anlaşılır olmaması veya birden çok anlama gelmesi hâlinde; bu hüküm, tüketicinin lehine yorumlanır.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5
> [2] Tüketici Sözleşmelerindeki Haksız Şartlar Hakkında Yönetmelik md. 6/3
>     “Sözleşme şartlarının yazılı olması halinde, tüketicinin anlayabileceği açık ve anlaşılır bir dilin kullanılmış olması gerekir. Sözleşmede yer alan bir hükmün açık ve anlaşılır olmaması veya birden çok anlama gelmesi hâlinde; bu hüküm, tüketicinin lehine yorumlanır.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=19798&MevzuatTur=7&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-018 · doğrudan bilgi

**Soru:** Kredimi kapattım ve bankadan 'borcum yoktur' yazısı istedim. Bunun için ücret ödemem gerekir mi?

*Beklenen cevabı yazanın notu:* tcmb-ucret-talimat:s7:be aynı. İkinci ve sonraki yazılar için metin ayrıca bir şey söylemiyor.

**Beklenen cevap:** Hayır, ilk talep için. Borcun bulunmadığına dair talep edilen bilgi yazıları için bir defaya mahsus olmak üzere ücret alınamaz.

**Kaynak alıntıları:**
- `tcmb-ucret-teblig:m10:f5`: “Finansal tüketicilerin ilgili kuruluşlardan borçlarının bulunmadığına dair talep ettikleri bilgi yazıları için bir defaya mahsus olmak üzere ücret alınamaz.”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Krediniz kapanmış ve bankadan 'borcum yoktur' yazısı istediniz. Bu durumda ücret ödemek zorunda kalmazsınız. Kaynaklara göre kredi ile ilgili işlemler için ücret alınmaz.
>
> Kaynaklar:
> [1] Ücret Tebliği Uygulama Talimatı (TCMB, 13.01.2026) md. 7 (e)
>     “Finansal tüketicilerin ilgili kuruluşlardan borçlarının bulunmadığına dair talep ettikleri bilgi yazıları için bir defaya mahsus olmak üzere ücret alınamaz.”
>     13.01.2026 tarihli sürüm, 23.10.2026 tarihinde alındı. https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Banka+Hakkinda/Mevzuat/Bankacilik/
> [2] Finansal Tüketicilerden Alınacak Ücretler Tebliği (2020/7) md. 10/5
>     “Finansal tüketicilerin ilgili kuruluşlardan borçlarının bulunmadığına dair talep ettikleri bilgi yazıları için bir defaya mahsus olmak üzere ücret alınamaz.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=34343&MevzuatTur=9&MevzuatTertip=5
> [3] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 31/1
>     “Belirli süreli kredi sözleşmesine ilişkin bir hesap açılması ve bu hesaptan sadece kredi ile ilgili işlemler yapılması durumunda, tüketiciden bu hesaba ilişkin herhangi bir isim altında ücret veya masraf talep edilemez.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-019 · doğrudan bilgi

**Soru:** Hesabımdan onaylamadığım bir ödeme çekildi. Bunun yetkisiz olduğu ispatlanırsa banka parayı ne zaman iade etmeli?

*Beklenen cevabı yazanın notu:* 'Beşinci fıkrada yer alan hususlar' = hileli kullanım veya kasten/ağır ihmalle yükümlülük ihlali (m54:f5). İspat yükü sağlayıcıda (m54:f2).

**Beklenen cevap:** İşlemin yetkilendirilmeden veya hatalı gerçekleştiği ispatlanırsa gönderenin ödeme hizmeti sağlayıcısı tutarı derhal iade etmek veya borçlandırılan hesabı eski durumuna getirmekle yükümlüdür. Düzeltme talebi mümkün olan en kısa sürede yerine getirilir; yönetmeliğin 54/5'te saydığı hâllere dair kuvvetli şüphe varsa sağlayıcı düzeltmeden önce makul bir süreyle sınırlı araştırma yapabilir.

**Kaynak alıntıları:**
- `odeme-hizmetleri-yon:m54:f3`: “gönderenin ödeme hizmeti sağlayıcısı bu ödeme işlemine ilişkin tutarı derhal gönderene iade etmek veya borçlandırılan ödeme hesabını eski durumuna getirmekle yükümlüdür”
- `odeme-hizmetleri-yon:m54:f3`: “makul bir süreyle sınırlı olmak üzere, araştırma yapma hakkına sahiptir”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Banka, yetkilendirilmemiş ödeme işlemi ispatlandıktan sonra tutarı derhal iade etmekle yükümlüdür. Düzeltme talebi 13 ay içinde yapılabilir.
>
> Kaynaklar:
> [1] Ödeme Hizmetleri ve Elektronik Para İhracı Yönetmeliği md. 54/3
>     “gönderenin ödeme hizmeti sağlayıcısı bu ödeme işlemine ilişkin tutarı derhal gönderene iade etmek veya borçlandırılan ödeme hesabını eski durumuna getirmekle yükümlüdür.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=39080&MevzuatTur=7&MevzuatTertip=5
> [2] Ödeme Hizmetleri ve Elektronik Para İhracı Yönetmeliği md. 54/1
>     “Düzeltme talebi, her halükarda ödeme işleminin gerçekleştirilmesinden itibaren on üç ay içinde yapılır.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=39080&MevzuatTur=7&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-020 · doğrudan bilgi

**Soru:** Kredi kartı sözleşmemde 'banka sözleşme şartlarını dilediği zaman tek taraflı değiştirebilir' yazıyor. Bu haksız şart sayılır mı?

*Beklenen cevabı yazanın notu:* Somut maddenin haksız olup olmadığı yorum gerektirir: sözleşmede haklı sebep belirtilip belirtilmediğine bağlı; ek1:p3 (2)(c) bazı finansal işlemleri (h) bendinin dışında tutar; kart sözleşmesi değişiklikleri ayrıca 5464 m25 / kart-yon m18 ile bildirim usulüne bağlanmıştır. Cevap yalnızca listedeki kuralı aktarmalı.

**Beklenen cevap:** Yönetmelik ekindeki listeye göre, sözleşmeyi düzenleyenin sözleşme şartlarını sözleşmede belirtilen haklı bir sebep olmaksızın tek taraflı değiştirmesine imkân veren şartlar haksız şarttır.

**Kaynak alıntıları:**
- `haksiz-sartlar-yon:ek1:p2`: “Sözleşmeyi düzenleyenin sözleşme şartlarını, sözleşmede belirtilen haklı bir sebep olmaksızın tek taraflı olarak değiştirmesine imkan veren şartlar”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Evet, kredi kartı sözleşmesinde 'banka sözleşme şartlarını dilediği zaman tek taraflı değiştirebilir' ifadesi haksız şart sayılır. Bu tür tek taraflı değişiklikler tüketici aleyhine dengesizlik yaratır ve tüketici korunması kanununa göre hükümsüzdür.
>
> Kaynaklar:
> [1] 5464 sayılı Banka Kartları ve Kredi Kartları Kanunu md. 24/4
>     “Sözleşmede kart hamilinin haklarını zedeleyici ve kart çıkaran kuruluş lehine tek taraflı haksız şartlar sağlayan hükümlere yer verilemez.”
>     Fıkra numarası kaynak metinde yazmıyor; maddenin paragrafları sayılarak bulundu.
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=5464&MevzuatTur=1&MevzuatTertip=5
> [2] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 5/2
>     “Tüketiciyle akdedilen sözleşmelerde yer alan haksız şartlar kesin olarak hükümsüzdür.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5
> [3] Tüketici Sözleşmelerindeki Haksız Şartlar Hakkında Yönetmelik md. 5/4
>     “Bu Yönetmeliğin ekinde yer alan listede sayılan şartlar haksız şart olarak kabul edilir.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=19798&MevzuatTur=7&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-022 · doğrudan bilgi

**Soru:** İhtiyaç kredisi çekerken banka bana sormadan krediye bağlı bir kredili mevduat hesabı (KMH) açabilir mi?

*Beklenen cevabı yazanın notu:* tuketici-kredisi-yon:m29:f2 ve tcmb-ucret-teblig:m10:f8 benzer kural.

**Beklenen cevap:** Hayır. Tüketicinin açık talimatı olmadan, belirli süreli kredi sözleşmesiyle ilişkili bir kredili mevduat sözleşmesi yapılamaz.

**Kaynak alıntıları:**
- `6502:m31:f2`: “Tüketicinin açık talimatı olmaksızın, belirli süreli kredi sözleşmesi ile ilişkili bir kredili mevduat sözleşmesi yapılamaz.”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Banka, tüketicinin açık talimatı olmaksızın krediye bağlı kredili mevduat hesabı açamaz.
>
> Kaynaklar:
> [1] Tüketici Kredisi Sözleşmeleri Yönetmeliği md. 29/2
>     “Tüketicinin açık talimatı olmaksızın belirli süreli kredi sözleşmesi ile ilişkili bir kredili mevduat hesabı sözleşmesi yapılamaz.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20767&MevzuatTur=7&MevzuatTertip=5
> [2] Konut Finansmanı Sözleşmeleri Yönetmeliği md. 18/2
>     “Tüketicinin açık talimatı olmaksızın konut finansmanı sözleşmesi ile ilişkili bir kredili mevduat hesabı sözleşmesi yapılamaz.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20793&MevzuatTur=7&MevzuatTertip=5
> [3] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 31/2
>     “Tüketicinin açık talimatı olmaksızın, belirli süreli kredi sözleşmesi ile ilişkili bir kredili mevduat sözleşmesi yapılamaz.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5
> [4] Mevduat ve Katılım Fonunun Kabulü, Çekilmesi ve Zamanaşımı Yönetmeliği md. 4/3
>     “Kanıtlanabilir onay veya talep olmaksızın kişiler adına kredili hesap dahil herhangi bir hesap açılamaz, kredili hesabın limiti artırılamaz ve kredili hesaptan herhangi bir tahsilat yapılamaz.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=10735&MevzuatTur=7&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-023 · birden fazla madde

**Soru:** Kredi kartım çalındı ve ben bankaya haber vermeden önce kartla harcama yapılmış. Bu harcamaların ne kadarından sorumluyum?

*Beklenen cevabı yazanın notu:* İki kaynak farklı sınır veriyor (5464/Kart Yön.: 150 YTL; Ödeme Hizmetleri Yön.: 250 TL). Kredi kartına hangisinin uygulanacağı ve 5464 m47 uyarınca tutarın güncellenip güncellenmediği korpustan çözülemez; sahibin karar vermesi gerekir. Cevap iki hükmü de aktarmalı, birini seçmemeli.

**Beklenen cevap:** 5464 m.12 ve Kart Yönetmeliği m.23'e göre kart hamili, bildirimden önceki 24 saat içindeki hukuka aykırı kullanımdan doğan zararlardan 150 Yeni Türk Lirası ile sınırlı sorumludur; kullanım hamilin ağır ihmali veya kastına dayanıyorsa ya da bildirim yapılmamışsa bu sınır uygulanmaz. Ödeme Hizmetleri Yönetmeliği m.54/4 ise kayıp/çalıntı ödeme aracında bildirimden önceki 24 saatteki yetkilendirilmemiş işlemlerden doğan zararın 250 TL'ye kadar olan kısmından sorumluluk öngörür ve bildirimden sonraki işlemlerden sorumluluğu kaldırır.

**Kaynak alıntıları:**
- `5464:m12:f1`: “yapacağı bildirimden önceki yirmidört saat içinde gerçekleşen hukuka aykırı kullanımdan doğan zararlardan yüzelli Yeni Türk Lirası ile sınırlı olmak üzere sorumludur”
- `kart-yon:m23:f1`: “Hukuka aykırı kullanımın, hamilin ağır ihmaline veya kastına dayanması veya bildirimin yapılmaması hallerinde bu sınır uygulanmaz.”
- `odeme-hizmetleri-yon:m54:f4`: “zararın ikiyüzelli Türk Lirasına kadar olan bölümünden sorumludur”
- `odeme-hizmetleri-yon:m54:f4`: “Gönderen, 53 üncü maddenin dördüncü fıkrası uyarınca yaptığı bildirimden sonra gerçekleşen yetkilendirmediği ödeme işlemlerinden sorumlu tutulamaz.”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Kart çalındığında 24 saat içinde bildirim yapılmazsa, hukuka aykırı kullanımdan doğan zararlar tamamen size aittir. Yüzelli Yeni Türk Lirası'na kadar sorumluluğunuz vardır, ancak bildirim yapılmazsa bu sınır geçerli değildir.
>
> Kaynaklar:
> [1] Banka Kartları ve Kredi Kartları Hakkında Yönetmelik md. 23/1
>     “Banka kartı veya kredi kartının ya da Kanunun 16 ncı maddesinde belirtilen bilgilerin kaybolması veya çalınması halinde kart hamili, kart çıkaran kuruluşa yapacağı bildirimden önceki yirmidört saat içinde gerçekleşen hukuka aykırı kullanımdan doğan zararlardan yüzelli Yeni Türk Lirası ile sınırlı olmak üzere sorumludur.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=11180&MevzuatTur=7&MevzuatTertip=5
> [2] 5464 sayılı Banka Kartları ve Kredi Kartları Kanunu md. 12/1
>     “Kartın ya da 16 ncı maddede belirtilen bilgilerin kaybolması veya çalınması halinde kart hamili, yapacağı bildirimden önceki yirmidört saat içinde gerçekleşen hukuka aykırı kullanımdan doğan zararlardan yüzelli Yeni Türk Lirası ile sınırlı olmak üzere sorumludur.”
>     Fıkra numarası kaynak metinde yazmıyor; maddenin paragrafları sayılarak bulundu.
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=5464&MevzuatTur=1&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-024 · birden fazla madde

**Soru:** İhtiyaç kredisinden 14 gün içinde caydım. Bankaya neyi, ne kadar sürede ödemem gerekiyor? Benden aldıkları masrafları geri alabilir miyim?

*Beklenen cevabı yazanın notu:* Kanun (30 gün, istenebilecek bedeller) + Yönetmelik (7 günde iade) birlikte gerekir. 'Masraf' gündelik ifadesi metindeki 'her türlü ücret' ile eşlendi.

**Beklenen cevap:** Krediyi kullandıysanız anaparayı ve kullanım tarihinden geri ödeme tarihine kadar akdi faizle hesaplanan faizi, cayma bildiriminden sonra en geç otuz gün içinde ödersiniz; bu sürede ödemezseniz caymamış sayılırsınız. Sizden akdi faiz ile kamu kurumlarına veya üçüncü kişilere ödenmiş masraflar dışında bedel istenemez; bunlar dışında tahsil edilen her türlü ücret, anapara ve faizi geri ödediğiniz tarihten itibaren yedi gün içinde iade edilir.

**Kaynak alıntıları:**
- `6502:m24:f3`: “anaparayı ve kredinin kullanıldığı tarihten anaparanın geri ödendiği tarihe kadar olan sürede tahakkuk eden faizi en geç cayma bildirimini kredi verene göndermesinden sonra otuz gün içinde geri öder”
- `6502:m24:f3`: “Bu süre içinde ödeme yapılmaması hâlinde tüketici kredisinden cayılmamış sayılır.”
- `tuketici-kredisi-yon:m24:f5`: “tüketicinin anapara ile tahakkuk eden faizi kredi verene geri ödediği tarihten itibaren yedi gün içinde tüketiciye iade edilir”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Krediden cayma hakkını kullanarak 14 gün içinde caydıktan sonra, anaparayı ve kredinin kullanıldığı tarihten anaparanın geri ödendiği tarihe kadar olan sürede tahakkuk eden faizi 30 gün içinde bankaya ödemelisin. Aldığın masrafları, kamu kurum veya kuruluşuna ödediğin ücretler hariç, geri alabilirsin. Diğer ücretler 7 gün içinde bankaya iade etmelisin.
>
> Kaynaklar:
> [1] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 24/3
>     “Cayma hakkını kullanan tüketicinin krediden faydalandığı hâllerde, tüketici, anaparayı ve kredinin kullanıldığı tarihten anaparanın geri ödendiği tarihe kadar olan sürede tahakkuk eden faizi en geç cayma bildirimini kredi verene göndermesinden sonra otuz gün içinde geri öder.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5
> [2] Tüketici Kredisi Sözleşmeleri Yönetmeliği md. 24/5
>     “Tüketiciden, hesaplanan akdi faiz ve bir kamu kurum veya kuruluşuna veya üçüncü kişilere ödenmiş olan ücretler dışında herhangi bir bedel talep edilemez. Bu bedeller dışında kalan ve tüketiciden tahsil edilen her türlü ücret, tüketicinin anapara ile tahakkuk eden faizi kredi verene geri ödediği tarihten itibaren yedi gün içinde tüketiciye iade edilir.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20767&MevzuatTur=7&MevzuatTertip=5
> [3] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 24/1
>     “Tüketici, on dört gün içinde herhangi bir gerekçe göstermeksizin ve cezai şart ödemeksizin tüketici kredisi sözleşmesinden cayma hakkına sahiptir.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-025 · birden fazla madde

**Soru:** Sabit faizli konut kredimi erken kapatmak istiyorum. Banka erken ödeme tazminatı alabilir mi, en fazla ne kadar? Bunun dışında başka bir ücret isteyebilir mi?

*Beklenen cevabı yazanın notu:* konut-finansmani-yon:m11:f4 aynı oranları tekrarlar; tcmb-ucret-talimat:s7:bd Tebliğ m10/4 ile aynı.

**Beklenen cevap:** Faiz sabitse ve sözleşmede yer verilmişse erken ödeme tazminatı istenebilir: erken ödenen tutarın kalan vadesi 36 ayı aşmayan kredilerde %1'ini, 36 ayı aşan kredilerde %2'sini geçemez; faiz değişkense tazminat istenemez. Tebliğe göre bu durumda erken ödeme tazminatı dışında hiçbir ücret alınamaz ve tazminat yapılacak faiz indirimi tutarını aşamaz.

**Kaynak alıntıları:**
- `6502:m37:f2`: “kalan vadesi otuz altı ayı aşmayan kredilerde yüzde birini, kalan vadesi otuz altı ayı aşan kredilerde ise yüzde ikisini geçemez”
- `6502:m37:f2`: “Oranların değişken olarak belirlenmesi hâlinde tüketiciden erken ödeme tazminatı talep edilemez.”
- `tcmb-ucret-teblig:m10:f4`: “Kanunun 37 nci maddesinde yer alan erken ödeme tazminatı haricinde hiçbir ücret alınamaz”
- `tcmb-ucret-teblig:m10:f4`: “Tahsil edilebilecek erken ödeme tazminatı ise yapılacak faiz veya kâr payı indirimi tutarını aşamaz.”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Banka sabit faizli kredinizde erken ödeme tazminatı alabilir. Kalan vadesi 36 ayı aşmayan kredilerde tazminat, ödenen tutarın %1'ini; aşan kredilerde %2'yi geçemez. Diğer ücretler alamaz. Tazminat, faiz indirimi tutarını aşamaz.
>
> Kaynaklar:
> [1] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 37/2
>     “Erken ödeme tazminatı gerekli faiz indirimi yapılarak hesaplanan ve tüketici tarafından konut finansmanı kuruluşuna erken ödenen tutarın kalan vadesi otuz altı ayı aşmayan kredilerde yüzde birini, kalan vadesi otuz altı ayı aşan kredilerde ise yüzde ikisini geçemez.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5
> [2] Ücret Tebliği Uygulama Talimatı (TCMB, 13.01.2026) md. 7 (d)
>     “Tahsil edilebilecek erken ödeme tazminatı ise yapılacak faiz veya kâr payı indirimi tutarını aşamaz.”
>     13.01.2026 tarihli sürüm, 23.10.2026 tarihinde alındı. https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Banka+Hakkinda/Mevzuat/Bankacilik/
> [3] Finansal Tüketicilerden Alınacak Ücretler Tebliği (2020/7) md. 10/1
>     “Kredi tahsis ücreti, kullandırılan kredi anaparasının binde beşini geçemez.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=34343&MevzuatTur=9&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-027 · birden fazla madde

**Soru:** Kredi kartımın asgari ödemesini birkaç ay üst üste ödeyemedim. Kartıma ne olur, yeni kart alabilir miyim?

*Beklenen cevabı yazanın notu:* Yeni kart yasağının yalnızca ilgili kuruluş için mi yoksa tüm kuruluşlar için mi geçerli olduğu metinden net değil; cevap bunu genellememeli. kart-yon m22:f6 birden çok kez değişmiş (2010 ek, 2013 değişik).

**Beklenen cevap:** Yönetmeliğe göre bir takvim yılında asgari tutarı toplam üç kez ödenmeyen kartlar nakit kullanımına, üst üste üç kez ödenmeyen kartlar nakit kullanımı ile mal ve hizmet alımına kapatılır; dönem borcunun tamamı ödenene kadar limit artırılmaz. Kanuna göre asgari tutar son ödeme tarihini izleyen üç ay içinde ödenmez ve kuruluşun bildiriminden itibaren bir ay içinde de ödenmezse kart hamilinin kredi kartları iptal edilir ve borcun tamamı ödenene kadar yeni kredi kartı düzenlenemez.

**Kaynak alıntıları:**
- `kart-yon:m22:f6`: “toplam üç kez ödenmeyen kredi kartları nakit kullanımına, üst üste üç kez ödenmeyen kredi kartları nakit kullanımı ile mal ve hizmet alımına kapatılır”
- `5464:m8:f2`: “Asgarî tutarın son ödeme tarihini takip eden üç ay içinde ödenmemesi durumunda”
- `5464:m8:f2`: “ilgili kart çıkaran kuruluşça kart hamiline verilen kredi kartları iptal edilir ve borcun tamamı ödeninceye kadar yeni kredi kartı düzenlenemez”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Kredi kartınızın asgari ödemesini üst üste üç ay ödemeyerek nakit kullanımına ve mal/hizmet alımına kapalı hale gelir. Borcun tamamı ödenene kadar yeni kredi kartı düzenlenemez.
>
> Kaynaklar:
> [1] 5464 sayılı Banka Kartları ve Kredi Kartları Kanunu md. 8/2
>     “Asgarî tutarın son ödeme tarihini takip eden üç ay içinde ödenmemesi durumunda kart çıkaran kuruluşça kart hamiline yapılacak bildirimden itibaren bir aylık süre içerisinde bu tutarın ödenmemesi ya da banka kartı ile kredi kartı kullanımından dolayı adli cezaların uygulanması halinde, ilgili kart çıkaran kuruluşça kart hamiline verilen kredi kartları iptal edilir ve borcun tamamı ödeninceye kadar yeni kredi kartı düzenlenemez.”
>     Fıkra numarası kaynak metinde yazmıyor; maddenin paragrafları sayılarak bulundu.
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=5464&MevzuatTur=1&MevzuatTertip=5
> [2] Banka Kartları ve Kredi Kartları Hakkında Yönetmelik md. 22/6
>     “Bir takvim yılı içinde asgari ödeme tutarı; toplam üç kez ödenmeyen kredi kartları nakit kullanımına, üst üste üç kez ödenmeyen kredi kartları nakit kullanımı ile mal ve hizmet alımına kapatılır.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=11180&MevzuatTur=7&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-028 · birden fazla madde

**Soru:** Tüketici hakem heyeti lehime karar verdi ama banka parayı ödemiyor. Karar bankayı bağlar mı, nasıl uygulatabilirim?

*Beklenen cevabı yazanın notu:* 6502:m70:f1 ve m70:f2 aynı kuralları içerir. İcra takibinin adımları korpusta yok; cevap ayrıntı uydurmamalı.

**Beklenen cevap:** Evet, tüketici hakem heyeti kararı tarafları bağlar. Karar, İcra ve İflas Kanununun ilamların yerine getirilmesine ilişkin hükümlerine göre yerine getirilir.

**Kaynak alıntıları:**
- `hakem-heyetleri-yon:m20:f4`: “Tüketici hakem heyeti kararı tarafları bağlar.”
- `hakem-heyetleri-yon:m24:f1`: “Tüketici hakem heyeti kararları, İcra ve İflas Kanununun ilamların yerine getirilmesi hakkındaki hükümlerine göre yerine getirilir.”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Tüketici hakem heyeti kararları tarafları bağlar. Karar bankayı bağlar. Kararı uygulamak için bankaya ödenmesini talep edebilirsiniz. Banka ödemeyi sürdürüyorsa, kararın tebliğ tarihinden itibaren iki hafta içinde tüketici mahkemesine itiraz edebilirsiniz. Ancak itiraz kararın icrasını durdurmaz. Kararın icrası için tüketici mahkemesine başvurarak uygulama sürecini başlatmanız gerekir.
>
> Kaynaklar:
> [1] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 70/1
>     “Tüketici hakem heyeti kararları tarafları bağlar.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5
> [2] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 70/3
>     “Taraflar, tüketici hakem heyetinin kararlarına karşı tebliğ tarihinden itibaren iki hafta içinde tüketici hakem heyetinin veya tüketicinin yerleşim yerinin bulunduğu yerdeki tüketici mahkemesine itiraz edebilir.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5
> [3] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 70/7
>     “Uyuşmazlıkla ilgili olarak tüketici hakem heyeti tarafından tüketici aleyhine verilen kararlarda tebligat ve bilirkişi ücretleri Bakanlıkça karşılanır.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-032 · birden fazla madde

**Soru:** Bankada unuttuğum bir hesabım var. Ne kadar süre işlem yapmazsam zamanaşımına uğrar? Çocuğum 10 yaşındayken onun adına açtığım hesapta süre ne zaman başlar?

*Beklenen cevabı yazanın notu:* mevduat-yon m9 başlığı 'ergin olmayanlar adına ve yalnızca bunlara ödeme yapılmak kaydıyla açtırılan hesaplar' diyor; fıkra metni bu kaydı tekrarlamıyor. Her çocuk hesabının kapsamda olup olmadığı yorum gerektirir. 10 yıl kuralı mevduat-yon:m8:f1'de de var.

**Beklenen cevap:** Bankadaki mevduat, katılım fonu, emanet ve alacaklardan hak sahibinin en son talebi, işlemi veya yazılı talimatı tarihinden itibaren on yıl içinde aranmayanlar zamanaşımına tabidir. Ergin olmayanlar adına açtırılan hesaplarda zamanaşımı süresi kişinin ergin olduğu tarihte işlemeye başlar.

**Kaynak alıntıları:**
- `5411:m62:f1`: “hak sahibinin en son talebi, işlemi, herhangi bir yazılı talimatı tarihinden başlayarak on yıl içinde aranmayanlar zamanaşımına tâbidir”
- `mevduat-yon:m9:f2`: “Ergin olmayanlar adına açtırılan hesaplarda, zamanaşımı süresi kişinin ergin olduğu tarihte işlemeye başlar.”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Bankada unuttuğunuz hesapta en son işlem tarihinden itibaren 10 yıl geçmeden işlem yapılmazsa zamanaşımına uğrar. Çocuğunuzun 10 yaşında açılan hesapta zamanaşımı süresi hesap açıldığı tarihten başlar. Bloke hesaplarda zamanaşımı, blok kaldırıldığında devam eder.
> Not: Sorudaki varsayım kaynaklarla çelişiyor.
>
> Kaynaklar:
> [1] 5411 sayılı Bankacılık Kanunu md. 62/1
>     “Bankalar nezdlerindeki mevduat, katılım fonu, emanet ve alacaklardan hak sahibinin en son talebi, işlemi, herhangi bir yazılı talimatı tarihinden başlayarak on yıl içinde aranmayanlar zamanaşımına tâbidir.”
>     Fıkra numarası kaynak metinde yazmıyor; maddenin paragrafları sayılarak bulundu.
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=5411&MevzuatTur=1&MevzuatTertip=5
> [2] Mevduat ve Katılım Fonunun Kabulü, Çekilmesi ve Zamanaşımı Yönetmeliği md. 9/1
>     “Kiralık kasalardaki kıymetler için zamanaşımı, kasa kira bedelinin en son tahsil edildiği ya da kasanın en son açıldığı tarihten itibaren başlar.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=10735&MevzuatTur=7&MevzuatTertip=5
> [3] Mevduat ve Katılım Fonunun Kabulü, Çekilmesi ve Zamanaşımı Yönetmeliği md. 9/3
>     “Yetkili merciler tarafından üzerine bloke konulan hesaplarda zamanaşımı süresi blokenin konduğu tarihte durur. Zamanaşımı süresi, hesaptaki blokenin kaldırıldığı tarihten itibaren işlemeye devam eder.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=10735&MevzuatTur=7&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-033 · sayısal (tutar, oran, süre)

**Soru:** Mobil bankacılıktan 5.000 TL EFT göndereceğim. 2026'da banka bu işlem için en fazla ne kadar ücret alabilir?

*Beklenen cevabı yazanın notu:* Güncel tutar Talimat dipnotunda (6/1/2026'dan itibaren). Gövde metnindeki 1.000 TL / 1 TL dilimleri eski taban tutarlar; cevap bunları güncel diye vermemeli. Sınırlanan ücretlere BSMV dahil değil (s3:be).

**Beklenen cevap:** 6/1/2026'dan itibaren uygulanan tabloya göre 8.300 TL ve altındaki EFT'lerde mobil/internet/düzenli ödeme kanalı için azami ücret 7,97 TL'dir.

**Kaynak alıntıları:**
- `tcmb-ucret-talimat:s9:bc`: “6/1/2026 tarihinden itibaren; EFT işlemlerinden alınabilecek azami ücret, aşağıdaki tabloda belirtilen şekliyle uygulanır”
- `tcmb-ucret-talimat:s9:bc`: “EFT | 8.300 TL ve Altı | 8.300,01-399.000 TL | 399.000 TL Üzeri”
- `tcmb-ucret-talimat:s9:bc`: “Mobil/İnternet/Düzenli Ödeme | 7,97 | 15,96 | 199,41”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Mobil bankacılıktan 5.000 TL EFT gönderimi için 2026'da banka en fazla 15,96 TL ücret alabilir.
>
> Kaynaklar:
> [1] Ücret Tebliği Uygulama Talimatı (TCMB, 13.01.2026) md. 9 (c)
>     “İşlem tutarının 1.000 TL ile 50.000 TL arasında olması hâlinde bu sınırlar sırasıyla 2 TL, 8 TL ve 10 TL olarak, işlem tutarının 50.000 TL üzerinde olması durumunda ise 25 TL, 50 TL ve 100 TL olarak uygulanır.”
>     13.01.2026 tarihli sürüm, 23.10.2026 tarihinde alındı. https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Banka+Hakkinda/Mevzuat/Bankacilik/
> [2] Ücret Tebliği Uygulama Talimatı (TCMB, 13.01.2026) md. 9 (c)
>     “[Dipnot 1] Tebliğin 7 nci maddesinin birinci fıkrası uyarınca 6/1/2026 tarihinden itibaren; EFT işlemlerinden alınabilecek azami ücret, aşağıdaki tabloda belirtilen şekliyle uygulanır.”
>     13.01.2026 tarihli sürüm, 23.10.2026 tarihinde alındı. https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Banka+Hakkinda/Mevzuat/Bankacilik/
> [3] Ücret Tebliği Uygulama Talimatı (TCMB, 13.01.2026) md. 9 (c)
>     “EFT | 8.300 TL ve Altı | 8.300,01-399.000 TL | 399.000 TL Üzeri”
>     13.01.2026 tarihli sürüm, 23.10.2026 tarihinde alındı. https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Banka+Hakkinda/Mevzuat/Bankacilik/

**Puanın:** 
**Not:** 

---

## b1-039 · sayısal (tutar, oran, süre)

**Soru:** Kredi kartımı uzun süredir hiç kullanmıyorum. Kaç gün hareket görmezse 'hareketsiz kart' sayılır ve aidat alınmaz?

*Beklenen cevabı yazanın notu:* s8:bi: tahsil edilemeyen ücretler en fazla son 12 aylık dönem için bekletilebilir, sonra iptal edilir; takip sorusu olarak ayrıca kullanılabilir.

**Beklenen cevap:** Kesintisiz en az yüz seksen gün hareket görmeyen kredi kartları hareketsiz kabul edilir ve hareketsiz kaldıkları sürece yıllık üyelik ücreti yansıtılamaz. Kuruluş, önceden bilgi vererek bu kartları kapatabilir.

**Kaynak alıntıları:**
- `tcmb-ucret-talimat:s8:bh`: “Kesintisiz olarak, en az yüzseksen gün süreyle hareket görmeyen kredi kartları hareketsiz kart kabul edilir ve bu kartlara hareketsiz kaldığı müddetçe yıllık üyelik ücreti yansıtılamaz.”
- `tcmb-ucret-talimat:s8:bh`: “bu nitelikteki kredi kartlarını kapatma hakkına sahiptir”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Kredi kartı 180 gün hareket görmezse 'hareketsiz kart' sayılır ve bu süre boyunca yıllık üyelik ücreti alınmaz.
>
> Kaynaklar:
> [1] Ücret Tebliği Uygulama Talimatı (TCMB, 13.01.2026) md. 8 (h)
>     “Kesintisiz olarak, en az yüzseksen gün süreyle hareket görmeyen kredi kartları hareketsiz kart kabul edilir ve bu kartlara hareketsiz kaldığı müddetçe yıllık üyelik ücreti yansıtılamaz.”
>     13.01.2026 tarihli sürüm, 23.10.2026 tarihinde alındı. https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Banka+Hakkinda/Mevzuat/Bankacilik/
> [2] Finansal Tüketicilerden Alınacak Ücretler Tebliği (2020/7) md. 11/6
>     “Kesintisiz olarak, en az yüzseksen gün süreyle hareket görmeyen kredi kartları hareketsiz kart kabul edilir ve bu kartlara hareketsiz kaldığı müddetçe yıllık üyelik ücreti yansıtılamaz.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=34343&MevzuatTur=9&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-040 · sayısal (tutar, oran, süre)

**Soru:** İhtiyaç kredimin taksidini geç ödedim. Banka en fazla ne kadar gecikme faizi uygulayabilir?

*Beklenen cevabı yazanın notu:* Konut kredisi için aynı %30 kuralı konut-finansmani-yon:m13:f3'te.

**Beklenen cevap:** Temerrüt veya geç ödemede, sözleşmedeki akdi faiz oranının yüzde otuz fazlasından daha yüksek oranda gecikme faizi alınamaz. Fazla tahsil edilirse kredi veren, fazla tutarı tahsil tarihinden iade tarihine kadar akdi faizin yüzde otuz fazlası üzerinden hesaplanan faiziyle birlikte ödemekle yükümlüdür.

**Kaynak alıntıları:**
- `tuketici-kredisi-yon:m18:f2`: “Temerrüt veya geç ödeme durumunda tüketiciden sözleşmede yer alan akdi faiz oranının yüzde otuz fazlasından daha yüksek bir oranda gecikme faizi tahsil edilemez.”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Banka, taksidin geç ödenmesi durumunda sözleşmede belirtilen akdi faiz oranının yüzde otuz fazlasından daha yüksek bir gecikme faizi uygulayamaz.
>
> Kaynaklar:
> [1] Tüketici Kredisi Sözleşmeleri Yönetmeliği md. 18/2
>     “Temerrüt veya geç ödeme durumunda tüketiciden sözleşmede yer alan akdi faiz oranının yüzde otuz fazlasından daha yüksek bir oranda gecikme faizi tahsil edilemez.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20767&MevzuatTur=7&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-041 · sayısal (tutar, oran, süre)

**Soru:** 2026 yılında tüketici hakem heyetine kaç liraya kadar olan uyuşmazlıklar için başvurabilirim?

*Beklenen cevabı yazanın notu:* 2026 için geçerli TL tutarı korpusta yok (yalnızca Tebliğ'e atıf var). Beklenen davranış: taban tutarı ve artış kuralını söyleyip güncel tutarın Tebliğ'den kontrol edilmesini önermek; rakam uydurmamak.

**Beklenen cevap:** Metindeki taban sınır otuz bin TL'dir: bu değerin altındaki uyuşmazlıklarda hakem heyetine başvuru zorunludur, bu değer ve üzerindekiler için başvurulamaz. Sınır her takvim yılı başında yeniden değerleme oranında artırılır. 1/1/2026'dan itibaren uygulanacak tutar için 23/12/2025 tarihli ve 33116 sayılı Resmî Gazete'deki Ticaret Bakanlığı Tebliği'ne atıf yapılmaktadır; bu güncel tutar korpusta yer almıyor.

**Kaynak alıntıları:**
- `hakem-heyetleri-yon:m6:f2`: “değeri otuz bin Türk Lirasının altında bulunan uyuşmazlıklarda tüketici hakem heyetlerine başvuru zorunludur”
- `hakem-heyetleri-yon:m6:f5`: “yeniden değerleme oranında arttırılarak uygulanır”
- `6502:m68:f1`: “Bu maddede yer alan parasal sınırların 1/1/2026 tarihinden itibaren uygulanması ile ilgili olarak 23/12/2025 tarihli ve 33116 sayılı Resmî Gazete’ de yayımlanan”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> 2026 yılında tüketici hakem heyetine 30.000 TL'ye kadar olan uyuşmazlıklar için başvuru yapılabilir.
>
> Kaynaklar:
> [1] Tüketici Hakem Heyetleri Yönetmeliği md. 6/2
>     “değeri otuz bin Türk Lirasının altında bulunan uyuşmazlıklarda tüketici hakem heyetlerine başvuru zorunludur.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=39730&MevzuatTur=7&MevzuatTertip=5
> [2] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 68/1
>     “değeri otuz bin Türk Lirasının altında bulunan uyuşmazlıklarda tüketici hakem heyetlerine başvuru zorunludur.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-042 · sayısal (tutar, oran, süre)

**Soru:** Bankaya KVKK kapsamında verilerimle ilgili başvuru yaptım. Banka kaç gün içinde cevap vermek zorunda, bunun için ücret alabilir mi?

*Beklenen cevabı yazanın notu:* Tarifedeki ücret tutarı korpusta yok.

**Beklenen cevap:** Veri sorumlusu talebi niteliğine göre en kısa sürede ve en geç otuz gün içinde ücretsiz olarak sonuçlandırır. İşlem ayrıca bir maliyet gerektirirse Kurulca belirlenen tarifedeki ücret alınabilir.

**Kaynak alıntıları:**
- `6698:m13:f2`: “en kısa sürede ve en geç otuz gün içinde ücretsiz olarak sonuçlandırır”
- `6698:m13:f2`: “Kurulca belirlenen tarifedeki ücret alınabilir”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Banka, veri sorumlusuna yapılan başvuruya en geç otuz gün içinde ücretsiz cevap vermek zorundadır. Ancak işlemin maliyeti varsa, Kurulca belirlenen ücret alınabilir.
>
> Kaynaklar:
> [1] 6698 sayılı Kişisel Verilerin Korunması Kanunu md. 13/2
>     “Veri sorumlusu başvuruda yer alan talepleri, talebin niteliğine göre en kısa sürede ve en geç otuz gün içinde ücretsiz olarak sonuçlandırır. Ancak, işlemin ayrıca bir maliyeti gerektirmesi hâlinde, Kurulca belirlenen tarifedeki ücret alınabilir.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6698&MevzuatTur=1&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-044 · değişiklik görmüş hüküm

**Soru:** İhtiyaç kredisi sözleşmesini şubeye gitmeden, tamamen internetten ya da mobilden yapabilir miyim? Kâğıt üzerinde yazılı sözleşme şart mı?

*Beklenen cevabı yazanın notu:* Kanun düzeyinde aynı değişiklik: 6502:m22:f3 notu (7529 ile 'veya mesafeli' eklendi). Mesafeli sözleşmenin teknik şartları bu chunk'ta yok.

**Beklenen cevap:** Güncel metne göre tüketici kredisi sözleşmesi yazılı veya mesafeli olarak kurulmadıkça geçerli olmaz; yani mesafeli (uzaktan) kurulan sözleşme de geçerlidir. Geçerli sözleşme yapmamış kredi veren, geçersizliği tüketici aleyhine ileri süremez. Bu birinci cümle RG-31/12/2024 ile değiştirilmiştir.

**Kaynak alıntıları:**
- `tuketici-kredisi-yon:m10:f1`: “Tüketici kredisi sözleşmesi yazılı veya mesafeli olarak kurulmadıkça geçerli olmaz.”
- `tuketici-kredisi-yon:m10:f1`: “(Değişik birinci cümle:RG-31/12/2024-32769)”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> İhtiyaç kredisi sözleşmesi internet veya mobil cihaz üzerinden mesafeli olarak kurulabilir. Kâğıt üzerinde yazılı sözleşme şartı aranmaz, ancak mesafeli sözleşme formatı mevzuatın kabul ettiği şekilde (örneğin dijital imza, saklanabilir veri) olmalıdır.
>
> Kaynaklar:
> [1] Tüketici Kredisi Sözleşmeleri Yönetmeliği md. 10/1
>     “Tüketici kredisi sözleşmesi yazılı veya mesafeli olarak kurulmadıkça geçerli olmaz.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20767&MevzuatTur=7&MevzuatTertip=5
> [2] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 22/3
>     “Tüketici kredisi sözleşmesi yazılı veya mesafeli olarak kurulmadıkça geçerli olmaz.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-046 · değişiklik görmüş hüküm

**Soru:** Kredi kartımın limitini düşürmek ya da kartı tamamen iptal ettirmek istiyorum. Banka talebimi kaç gün içinde yerine getirmek zorunda?

*Beklenen cevabı yazanın notu:* Fıkra RG-6/7/2018 ile değiştirilmiş; güncel kural 7 gün. 5464:m25:f2 iptal/fesih hakkını süre belirtmeden tanır.

**Beklenen cevap:** Kart limitinin veya toplam kart limitinin azaltılması, kartın iptali ve sözleşmenin feshi talepleri en geç yedi gün içinde yerine getirilmelidir. Şubeden yapılan limit azaltma veya iptal taleplerinde, talebin alındığı tarihi gösteren imzalı bir belge veya doldurulan formun bir örneği kart hamiline verilmelidir.

**Kaynak alıntıları:**
- `kart-yon:m18:f2`: “talebin en geç yedi gün içinde kart çıkaran kuruluşça yerine getirilmesi zorunludur”
- `kart-yon:m18:f2`: “(Değişik:RG-6/7/2018-30470)”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Banka, kredi kartı limitini düşürme veya kart iptali talebinizi en geç 7 gün içinde yerine getirmek zorundadır.
>
> Kaynaklar:
> [1] Banka Kartları ve Kredi Kartları Hakkında Yönetmelik md. 18/2
>     “Kart limitinin veya toplam kart limitinin azaltılmasına, kartın iptal edilmesine ve sözleşmenin feshine ilişkin kart hamilince yapılan talebin en geç yedi gün içinde kart çıkaran kuruluşça yerine getirilmesi zorunludur.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=11180&MevzuatTur=7&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-059 · yanlış önermeli

**Soru:** Kredi kartlarında yıllık aidat zorunlu bir şey; aidatsız kredi kartı diye bir seçenek yok, değil mi?

*Sorunun varsayımı yanlış; iyi bir cevap onu kaynağa dayanarak düzeltir.*

*Beklenen cevabı yazanın notu:* Önerme hem Kanun hem Tebliğ tarafından açıkça çürütülüyor. tcmb-ucret-talimat:s8:ba aynı.

**Beklenen cevap:** Hayır, bu doğru değil. Kart çıkaran kuruluşlar yıllık üyelik aidatı veya benzeri ücret almadıkları bir kredi kartı türü sunmak zorundadır. Aidatlı kartın, limit aynı kalmak kaydıyla aidatsız kartla değiştirilmesi talebi de yerine getirilmek zorundadır.

**Kaynak alıntıları:**
- `6502:m31:f3`: “Kart çıkaran kuruluşlar, tüketicilere yıllık üyelik aidatı ve benzeri isim altında ücret tahsil etmedikleri bir kredi kartı türü sunmak zorundadır.”
- `tcmb-ucret-teblig:m11:f1`: “yıllık üyelik ücreti bulunan kredi kartını limiti aynı kalmak kaydıyla yıllık üyelik ücreti bulunmayan kredi kartı ile değiştirme talepleri, kart çıkaran kuruluşlar tarafından yerine getirilmek zorundadır”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Yıllık aidat zorunlu değil. 6502 sayılı Kanun ve TCMB talimatları, kart çıkaran kuruluşlara yıllık üyelik ücreti almayan kredi kartı türü sunma zorunluluğu getiriyor.
>
> Kaynaklar:
> [1] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 31/3
>     “Kart çıkaran kuruluşlar, tüketicilere yıllık üyelik aidatı ve benzeri isim altında ücret tahsil etmedikleri bir kredi kartı türü sunmak zorundadır.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5
> [2] Ücret Tebliği Uygulama Talimatı (TCMB, 13.01.2026) md. 8 (g)
>     “Kredi kartı yıllık üyelik ücreti, ancak finansal tüketiciyi borçlandırıcı nitelikteki ilk kullanımı müteakip ve yıllık olarak tahakkuk ettirilebilir.”
>     13.01.2026 tarihli sürüm, 23.10.2026 tarihinde alındı. https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Banka+Hakkinda/Mevzuat/Bankacilik/
> [3] Ücret Tebliği Uygulama Talimatı (TCMB, 13.01.2026) md. 8 (d)
>     “Banka kartları ile sanal kredi kartlarından yıllık üyelik ücreti alınamaz.”
>     13.01.2026 tarihli sürüm, 23.10.2026 tarihinde alındı. https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Banka+Hakkinda/Mevzuat/Bankacilik/

**Puanın:** 
**Not:** 

---

## b1-061 · yanlış önermeli

**Soru:** Banka ihtiyaç kredisi verirken hayat sigortası yaptırmamı zorunlu tutabilir ve yalnızca kendi anlaştığı sigorta şirketini kabul eder; başka şirketten sigorta getiremem, değil mi?

*Sorunun varsayımı yanlış; iyi bir cevap onu kaynağa dayanarak düzeltir.*

*Beklenen cevabı yazanın notu:* Madde 7392 sayılı Kanunla başlığıyla birlikte değişmiş (2022). tuketici-kredisi-yon:m26:f1 ve m26:f3 aynı kuralları (dain-i mürtehin ve kredi tutarı/süresiyle uyum şartıyla) tekrarlar.

**Beklenen cevap:** Hayır. Tüketicinin yazılı veya kalıcı veri saklayıcısıyla açık talebi olmadan kredi bağlantılı sigorta yaptırılamaz; kredi veren sigortalı bir kredi sunacaksa sigortasız bir sözleşmeyi de teklif etmek zorundadır. Tüketicinin istediği sigorta şirketinden sağladığı teminat kredi veren tarafından kabul edilmek zorundadır.

**Kaynak alıntıları:**
- `6502:m29:f1`: “Tüketicinin yazılı veya kalıcı veri saklayıcısı aracılığıyla açık talebi olmaksızın kredi bağlantılı sigorta yaptırılamaz.”
- `6502:m29:f1`: “kredi bağlantılı sigorta içermeyen bir sözleşmeyi de tüketiciye teklif etmek koşuluyla”
- `6502:m29:f2`: “Tüketicinin istediği sigorta şirketinden sağladığı teminat, kredi veren tarafından kabul edilmek zorundadır.”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Banka, tüketicinin seçtiği sigorta şirketinden teminat sağlanması zorunludur. Kredi tutarını aşan sigorta yaptırılamaz ve kredi konusu ile uyumlu olmalıdır. Banka, tüketicinin seçtiği sigorta şirketini kabul etmek zorundadır.
>
> Kaynaklar:
> [1] Tüketici Kredisi Sözleşmeleri Yönetmeliği md. 26/4
>     “Kredi bağlantılı sigortanın kredi konusu ile uyumlu olması zorunludur. Krediye ilişkin aynı teminatı içeren birden fazla sigorta yaptırılamaz. Kredi tutarını aşan sigorta yapılması yasaktır.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20767&MevzuatTur=7&MevzuatTertip=5
> [2] Tüketici Kredisi Sözleşmeleri Yönetmeliği md. 26/3
>     “Tüketicinin istediği sigorta şirketinden sağladığı, kredi tutarı ve süresi ile uyumlu, dain-i mürtehini kredi veren olan sigorta poliçesi, tüketiciye önerilen kredinin koşullarında değişikliğe sebep olmaksızın kredi veren tarafından kabul edilmek zorundadır.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20767&MevzuatTur=7&MevzuatTertip=5
> [3] 6502 sayılı Tüketicinin Korunması Hakkında Kanun md. 29/2
>     “Tüketicinin istediği sigorta şirketinden sağladığı teminat, kredi veren tarafından kabul edilmek zorundadır.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5

**Puanın:** 
**Not:** 

---

## b1-063 · yanlış önermeli

**Soru:** Bir elektronik para kuruluşunun uygulamasına yüklediğim e-para bakiyesi de vadesiz mevduat gibi sayılır ve bekledikçe faiz getirir, değil mi?

*Sorunun varsayımı yanlış; iyi bir cevap onu kaynağa dayanarak düzeltir.*

*Beklenen cevabı yazanın notu:* Soru bilerek 'dijital cüzdan' yerine 'e-para bakiyesi' diye kuruldu; dijital cüzdan odeme-hizmetleri-yon m4/A'da ayrı bir hizmet ve bakiyenin e-para olup olmadığı ürüne bağlı.

**Beklenen cevap:** Hayır. Elektronik para ihraç eden kuruluş, elektronik parayı elde bulundurma süresine bağlı olarak hamiline faiz veremez ve herhangi bir menfaat sağlayamaz. Elektronik para karşılığında alınan fonlar Bankacılık Kanunu m.60'a göre mevduat veya katılım fonu kabul edilmez.

**Kaynak alıntıları:**
- `6493:m20:f5`: “elektronik para hamiline faiz veremez ve herhangi bir menfaat sağlayamaz”
- `6493:m20:f7`: “5411 sayılı Kanunun 60 ıncı maddesine göre mevduat veya katılım fonu olarak kabul edilmez”

**Modelin cevabı** (kullanıcının gördüğü hâliyle):

> Elektronik para bakiyesi vadesiz mevduat olarak sayılmaz ve faiz getirmez. Kanunlar elektronik para ihraç eden kuruluşların faiz veya menfaat sağlayamayacağını belirtir.
>
> Kaynaklar:
> [1] 6493 sayılı Ödeme Hizmetleri ve Elektronik Para Kuruluşları Kanunu md. 20/5
>     “Elektronik para ihraç eden kuruluş, elektronik parayı elinde bulundurma süresine bağlı olarak elektronik para hamiline faiz veremez ve herhangi bir menfaat sağlayamaz.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6493&MevzuatTur=1&MevzuatTertip=5
> [2] Ödeme Hizmetleri ve Elektronik Para İhracı Yönetmeliği md. 5/4
>     “Elektronik para karşılığında alınan fon için faiz işletilemez ve müşteriye elektronik paranın tutulduğu süreye ve tutara bağlı herhangi bir menfaat sağlanamaz.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=39080&MevzuatTur=7&MevzuatTertip=5
> [3] 6493 sayılı Ödeme Hizmetleri ve Elektronik Para Kuruluşları Kanunu md. 14/3
>     “Ödeme ve elektronik para kuruluşlarının ödeme hizmeti ile ilgili olarak aldığı fonlar, 5411 sayılı Kanunun 60 ıncı maddesine göre mevduat veya katılım fonu veya bu Kanun kapsamında elektronik para olarak değerlendirilmez.”
>     mevzuat.gov.tr'deki metin, 23.10.2026 tarihinde alındı. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6493&MevzuatTur=1&MevzuatTertip=5

**Puanın:** 
**Not:** 
