# Sources

How the corpus is collected, what was verified, and what the official sites actually serve.
Snapshot: 2026-10-23. Machine-readable version: [`data/manifest.json`](../data/manifest.json)
(schema: [`data/manifest.schema.json`](../data/manifest.schema.json)).

## Collection rules

- At most **1 request per second per host** (`RateLimiter` refuses intervals below 1.0 s,
  NaN and infinity; default 1.1 s). Retries, redirects and robots.txt go through the same
  limiter. A robots.txt `Crawl-delay` can only make it slower.
- **robots.txt is honoured** for the product token `finhak`. mevzuat.gov.tr only has
  `Noindex` lines for Googlebot, no `Disallow`. A missing robots.txt (4xx) allows crawling;
  401/403 disallows everything; 5xx stops the host. Redirects of robots.txt are followed.
  Known limitation: the standard-library parser ignores `*`/`$` wildcards in rules.
- **Allowlist:** every hop, including redirects, must be `https://www.mevzuat.gov.tr` on
  port 443. The text iframe must point to `/anasayfa/MevzuatFihristDetayIframe` there, and
  files must be under `/MevzuatMetin/` with `.doc`, `.docx` or `.pdf` (one per extension).
- **Size and time caps:** bodies are streamed uncompressed (`Accept-Encoding: identity`),
  capped at 50 MB (robots.txt 512 KB) and 180 s per request.
- **Validated before caching:** the page must contain RG info and the text iframe, the text
  must have a title. A cached file is reused only if it came from the same URL and still has
  the logged SHA-256.
- Raw files are cached in `data/raw/{id}/` (not committed). Re-running the fetcher sends
  zero requests when everything is cached; `--refresh` re-downloads (keeping a good copy if
  the new download is bad).
- Legal basis for redistribution: laws, regulations and communiqués are outside copyright
  protection (FSEK art. 31).

## mevzuat.gov.tr URL patterns (verified)

| What | Pattern |
|---|---|
| Document page | `https://www.mevzuat.gov.tr/mevzuat?MevzuatNo={no}&MevzuatTur={tür}&MevzuatTertip=5` |
| Consolidated text (HTML, primary source) | `/anasayfa/MevzuatFihristDetayIframe?MevzuatTur={tür}&MevzuatNo={no}&MevzuatTertip=5` |
| Word / PDF of a law | `/MevzuatMetin/1.5.{no}.{doc,docx,pdf}` |
| Word / PDF of a regulation or communiqué | `/MevzuatMetin/yonetmelik/{tür}.5.{no}.{doc,pdf}` |
| Resmî Gazete daily index (for Phase 2) | `https://www.resmigazete.gov.tr/eskiler/YYYY/MM/YYYYMMDD.htm` |

`MevzuatTur`: 1 = Kanun, 7 = Kurum ve Kuruluş Yönetmeliği, 9 = Tebliğ.

The download links are **read from the page, never constructed**: the extension differs
per document (5464 has `.docx`; 11180, 19798 and 38873 have no PDF).

The document page has no title; the title is the first all-caps block of the text iframe.
The page carries `Resmî Gazete Tarihi: dd.mm.yyyy Resmî Gazete Sayısı: n`.

## Corpus (15 documents)

Every RG date/number below was read from the official mevzuat.gov.tr page and checked
against `data/sources.yaml`; 19798, 10735 and 38873 were also cross-checked against the
Resmî Gazete daily index. "Notes" = dated amendment notes found in the consolidated text.

| id | Document | MevzuatNo/Tür | RG date / issue | Notes | Latest note |
|---|---|---|---|---|---|
| `6502` | Tüketicinin Korunması Hakkında Kanun | 6502/1 | 28.11.2013 / 28835 | 50 | 24.06.2026 (7587) |
| `5411` | Bankacılık Kanunu | 5411/1 | 01.11.2005 / 25983 | 97 | 27.12.2023 (7491) |
| `5464` | Banka Kartları ve Kredi Kartları Kanunu | 5464/1 | 01.03.2006 / 26095 | 7 | 18.06.2020 (7247) |
| `6493` | Ödeme ve Menkul Kıymet Mutabakat Sistemleri, Ödeme Hizmetleri ve Elektronik Para Kuruluşları Hakkında Kanun | 6493/1 | 27.06.2013 / 28690 | 31 | 18.06.2020 (7247) |
| `6698` | Kişisel Verilerin Korunması Kanunu | 6698/1 | 07.04.2016 / 29677 | 10 | 02.03.2024 (7499) |
| `tcmb-ucret-teblig` | Finansal Tüketicilerden Alınacak Ücretlere İlişkin Usûl ve Esaslar Hakkında Tebliğ (2020/7, TCMB) | 34343/9 | 07.03.2020 / 31061 | 11 | 22.12.2023 (RG 32407) |
| `tuketici-kredisi-yon` | Tüketici Kredisi Sözleşmeleri Yönetmeliği | 20767/7 | 22.05.2015 / 29363 | 20 | 31.12.2024 (RG 32769) |
| `kart-yon` | Banka Kartları ve Kredi Kartları Hakkında Yönetmelik (BDDK) | 11180/7 | 10.03.2007 / 26458 | 71 | 25.09.2020 (RG 31255) |
| `konut-finansmani-yon` | Konut Finansmanı Sözleşmeleri Yönetmeliği | 20793/7 | 28.05.2015 / 29369 | 17 | 31.12.2024 (RG 32769) |
| `odeme-hizmetleri-yon` | Ödeme Hizmetleri ve Elektronik Para İhracı ile Ödeme Hizmeti Sağlayıcıları Hakkında Yönetmelik (TCMB) | 39080/7 | 01.12.2021 / 31676 | 103 | 04.09.2026 (RG 33360) |
| `hakem-heyetleri-yon` | Tüketici Hakem Heyetleri Yönetmeliği | 39730/7 | 21.09.2022 / 31960 | 0 | – |
| `mesafeli-finansal-yon` | Finansal Hizmetlere İlişkin Mesafeli Sözleşmeler Yönetmeliği | 20495/7 | 31.01.2015 / 29253 | 7 | 31.12.2024 (RG 32769) |
| `haksiz-sartlar-yon` | Tüketici Sözleşmelerindeki Haksız Şartlar Hakkında Yönetmelik | 19798/7 | 17.06.2014 / 29033 | 0 | – |
| `mevduat-yon` | Mevduat ve Katılım Fonunun Kabulüne, Çekilmesine ve Zamanaşımına Uğrayan Mevduat, Katılım Fonu, Emanet ve Alacaklara İlişkin Usul ve Esaslar Hakkında Yönetmelik (BDDK) | 10735/7 | 01.11.2006 / 26333 | 23 | 23.01.2024 (RG 32438) |
| `erisilebilirlik-yon` | Bankacılık Hizmetlerinin Erişilebilirliğine Dair Yönetmelik (BDDK) | 38873/7 | 18.06.2016 / 29746 | 0 | – |

"Latest note" is the latest *dated amendment note in the consolidated text*, not a
statement that no later change exists. The consolidated texts are recent (6502 includes a
June 2026 amendment), but checking for newer changes is Phase 2 (Resmî Gazete tracking).

## Findings that change the brief

1. **The BDDK fee regulation is repealed.** "Finansal Tüketicilerden Alınacak Ücretlere
   İlişkin Usul ve Esaslar Hakkında Yönetmelik" (RG 03.10.2014/29138) was repealed in
   RG 07.03.2020/31061. The same issue published its replacement, TCMB Tebliğ 2020/7, which
   is in the corpus. The repealed text is not indexed; it is a good source for
   false-premise eval questions.
2. **Current fee amounts are not in the Tebliğ.** The Tebliğ's caps and monetary limits are
   increased every year by the TÜİK year-end CPI and notified to banks by TCMB (TCMB
   *Uygulama Talimatı*, section 4.a). The current values are in the TCMB "Finansal
   Tüketicilerden Alınacak Ücretlere İlişkin Usûl ve Esaslar Hakkında Tebliğe (Sayı: 2020/7)
   İlişkin Uygulama Talimatı" (tcmb.gov.tr PDF, version dated 13.01.2026), e.g. its EFT
   cap table "from 6/1/2026". That document is not on mevzuat.gov.tr and not published in
   the Resmî Gazete. Whether to add it is an open decision (see M1 report).
3. **Some `.doc` downloads are not Word binaries.** For 11180, 19798 and 38873 the `.doc`
   is a Word "web page" export: HTML in UTF-16LE with a BOM. These are kept and labelled
   `doc_html` in the manifest.
4. **One `.doc` is corrupt on the server.** For 39730 (Tüketici Hakem Heyetleri) the `.doc`
   is double-encoded: UTF-16LE text was decoded as Windows-1254 and re-encoded as UTF-16LE
   (bytes `FF FE FF 00 5F 01 3C 00 …` = "ÿş<…"). It is rejected and listed under
   `rejected_files`; the HTML text and the PDF of that regulation are fine.
5. **Amendment notes come in three spellings:** `(Değişik:RG-9/8/2021-31563)`,
   `( Değişik:RG -21/12/2008-27087)` and `(Ek:17/12/2010-27788)` in regulations;
   `(Değişik:24/3/2022-7392/2 md.)` and `…-KHK-703/97 md.` in laws. All are parsed.
