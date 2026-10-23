# Test fixtures

`mevzuat/` holds real pages from mevzuat.gov.tr, downloaded on 2026-10-23 at no more than
one request per second. Legislation texts are outside copyright protection (FSEK art. 31).

| File | Source URL |
|---|---|
| `page_kanun_6502.html` | `https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5` |
| `page_yonetmelik_11180.html` | `https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=11180&MevzuatTur=7&MevzuatTertip=5` |
| `page_teblig_34343.html` | `https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=34343&MevzuatTur=9&MevzuatTertip=5` |
| `text_kanun_6502.html` | `https://www.mevzuat.gov.tr/anasayfa/MevzuatFihristDetayIframe?MevzuatTur=1&MevzuatNo=6502&MevzuatTertip=5` |
| `text_yonetmelik_11180.html` | `https://www.mevzuat.gov.tr/anasayfa/MevzuatFihristDetayIframe?MevzuatTur=7&MevzuatNo=11180&MevzuatTertip=5` |
| `text_teblig_34343.html` | `https://www.mevzuat.gov.tr/anasayfa/MevzuatFihristDetayIframe?MevzuatTur=9&MevzuatNo=34343&MevzuatTertip=5` |

`text_kanun_6502.html` and `text_yonetmelik_11180.html` are **truncated** at a paragraph
boundary (about 64 KB and 40 KB) to keep the repository small. A closing comment marks the cut.
Do not use them to count articles. The full texts live in `data/raw/` (not committed).

`tcmb/listing_bankacilik.html` is the TCMB "Bankacılık ile İlgili Mevzuat" listing page
(`https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Banka+Hakkinda/Mevzuat/Bankacilik/`),
downloaded on 2026-10-23; it links the 13.01.2026 version of the fee Tebliğ's Uygulama Talimatı.
