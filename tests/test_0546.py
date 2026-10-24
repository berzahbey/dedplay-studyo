"""0.5.46 gerileme testi: bağlantısız düz dipnotlar (kaynak._duz_notlari_bagla). EPUB'da metinde düz "[18]" işareti, notlar bölüm sonunda
"[18] …" paragrafı (El-Muvâfakât, Füsus'un Sırları): dipnot olur, seslendirilmez. Ana metin paragrafları ("[80]âyetindeki …") ve
işaretsiz numaralı listeler değişmez.
Çalıştırma: docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/k:/app -e TR_KELIME=/app/app/data/tr_kelime.txt berzahbey/dedplay-studyo:latest python tests/test_0546.py"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kutuphane import kaynak as K

kalan = []


def dene(ad, ok, ayrinti=""):
    print(("GECTI " if ok else "KALDI ") + ad + ("" if ok else f"\n   {ayrinti}"))
    if not ok:
        kalan.append(ad)


p = lambda t: {"tur": "p", "metin": t}
h = lambda t: {"tur": "baslik", "metin": t, "seviye": 1}


def bolum(bas, no, ad):
    ogeler = [h(ad)]
    for k in range(no):
        ogeler.append(p(f"Bu bölümün {k + 1}. paragrafı uzunca bir cümleyle devam eder ve sonunda bir atıf vardır.[{bas + k}] Sonra devam eder."))
    ogeler.append(p("Bölümün son paragrafı burada biter."))
    for k in range(no):
        ogeler.append(p(f"[{bas + k}] Sâtibi, el-Muvâfakât, İz Yayıncılık: 3/{100 + k}"))
    return ogeler


# 1) iki bölüm, numaralar ikinci bölümde baştan başlıyor
og = bolum(1, 8, "BİRİNCİ BÖLÜM") + bolum(1, 6, "İKİNCİ BÖLÜM")
notlar = {}
n = K._duz_notlari_bagla(og, notlar)
metin = " ".join(o["metin"] for o in og)
dene("14 düz not bağlandı", n == 14 and len(notlar) == 14, f"{n} {len(notlar)}")
dene("not paragrafları metinden çıktı", "İz Yayıncılık" not in metin, metin[:300])
dene("işaretler {{nXXXX}} oldu, düz [n] kalmadı", "[1]" not in metin and metin.count("{{n") == 14, metin[:300])
ikinci = next(o["metin"] for o in og if o["metin"].startswith("Bu bölümün 1.") and "{{n0009}}" in o["metin"])
dene("ikinci bölümün [1]'i kendi notuna bağlı (n0009 → 3/100)", notlar["n0009"] == "Sâtibi, el-Muvâfakât, İz Yayıncılık: 3/100", notlar.get("n0009"))
dene("not sırası metindeki sıra", list(notlar) == ["n%04d" % i for i in range(1, 15)])

# 2) "[80]âyetindeki" (boşluksuz) ana metin kalır; işareti olmayan dizi başı notu öncesine bağlanır
og = bolum(1, 12, "BÖLÜM") + [p("[80]âyetindeki kelimesini hazır olanlara sordu.")]
og.insert(14, p("[99] Yayıncının notu: bu metin ilk ciltte."))   # dizinin başında, işareti yok
notlar = {}
n = K._duz_notlari_bagla(og, notlar)
metin = [o["metin"] for o in og]
dene("boşluksuz '[80]âyetindeki' ana metin kalır", metin[-1].startswith("[80]âyetindeki"), metin[-1])
dene("işaretsiz dizi notu da not oldu (öncesindeki paragrafa bağlı)", n == 13 and "Yayıncının notu: bu metin ilk ciltte." in notlar.values()
     and any(m.startswith("Bölümün son paragrafı") and "{{n" in m for m in metin), f"{n} {metin[12:15]}")

# 3) 10'dan az aday: dokunulmaz
og = bolum(1, 5, "BÖLÜM")
eski = [dict(o) for o in og]
dene("az aday (5) dokunulmaz", K._duz_notlari_bagla(og, {}) == 0 and og == eski)

# 4) işaretsiz numaralı liste ("[1] Birinci madde") dokunulmaz
og = [h("LİSTE"), p("Şu maddeler vardır:")] + [p(f"[{k}] Madde {k}: açıklama burada.") for k in range(1, 15)]
eski = [dict(o) for o in og]
dene("işaretsiz numaralı liste dokunulmaz", K._duz_notlari_bagla(og, {}) == 0 and og == eski)

# 5) uçtan uca: EPUB → kitap.json (dipnotlar), seslendirme parçalarında not yok
from ebooklib import epub
from kutuphane import cikti as C
kitap = epub.EpubBook(); kitap.set_identifier("t"); kitap.set_title("Deneme"); kitap.set_language("tr")
govde = "".join(f"<p>Bu cümle bir kaynağa dayanır ve uzunca devam eder.[{k}]</p>" for k in range(1, 13))
notp = "".join(f"<p> [{k}] Sâtibi, el-Muvâfakât, İz Yayıncılık: 1/{k}</p>" for k in range(1, 13))
c = epub.EpubHtml(title="B", file_name="b.xhtml", lang="tr"); c.content = f"<html><body><h1>BÖLÜM</h1>{govde}<p>Son.</p>{notp}</body></html>"
kitap.add_item(c); kitap.toc = [c]; kitap.spine = [c]; kitap.add_item(epub.EpubNcx()); kitap.add_item(epub.EpubNav())
yol = os.path.join(tempfile.mkdtemp(), "Yazar - Deneme.epub"); epub.write_epub(yol, kitap)
kit = K.cevir(yol)
dene("EPUB: 12 dipnot", len(kit.get("dipnotlar") or {}) == 12, len(kit.get("dipnotlar") or {}))
ses = " ".join(x["tr"] for x in C.studyo_parcalari(kit) if x["name"].startswith("Parca_"))
dene("EPUB: seslendirme parçalarında not metni yok", "İz Yayıncılık" not in ses and "Bu cümle bir kaynağa" in ses, ses[:200])

# 6) 0.5.44 yan etkisi: satır sonundaki "(bak., s. 123" sayısı kenar numarası sayılmaz; gerçek kenar numaraları yine çıkar
def satir(t, top, x0=66.0, x1=390.0):
    return {"text": t, "h": 11, "top": top, "bot": top + 11, "x0": x0, "x1": x1, "n": len(t.split()), "kalin": False, "blok": 0, "ocr": False}
sl = []
for k in range(10):
    rows = [satir("ortaya çıkmaya başlamıştır ki bu çağda İslam medeniyetinin kapısı", 100 + 13 * j) for j in range(6)]
    rows.append(satir("hukuki kavram ve kaidelerin kudretli nâkilleri %d" % (20 + 2 * k), 180.0, x1=410.0))
    rows.append(satir("akitle de karşılaştırılabilir (bak., s. %d" % (150 + k), 193.0, x1=410.0))
    sl.append(rows)
K._kenar_numaralari_konumla(sl)
dene("'(bak., s. 152' sayısı kalır, kenar numarası çıkar", sl[0][-1]["text"].endswith("s. 150") and sl[0][-2]["text"].endswith("nâkilleri"),
     f"{sl[0][-2]['text']} | {sl[0][-1]['text']}")

# 7) notun içindeki "[n]" (notta başka nota atıf) işaret sayılmaz; hiçbir not metni kaybolmaz (El-Muvâfakât'ta 5 not kayboluyordu)
from ebooklib import epub as _e
kitap = _e.EpubBook(); kitap.set_identifier("t2"); kitap.set_title("Deneme2"); kitap.set_language("tr")
govde = "".join(f"<p>Bu cümle bir kaynağa dayanır ve uzunca devam eder.[{k}]</p>" for k in range(1, 13) if k != 5)
notp = "".join(f"<p> [{k}] Not {k}: Sâtibi, el-Muvâfakât, İz Yayıncılık: 1/{k}{' (bkz. [5])' if k == 4 else ''}</p>" for k in range(1, 13))
c = _e.EpubHtml(title="B", file_name="b.xhtml", lang="tr"); c.content = f"<html><body><h1>BÖLÜM</h1>{govde}<p>Son.</p><p> [47] . Hûd, 11/7.</p>{notp}</body></html>"
kitap.add_item(c); kitap.toc = [c]; kitap.spine = [c]; kitap.add_item(_e.EpubNcx()); kitap.add_item(_e.EpubNav())
yol2 = os.path.join(tempfile.mkdtemp(), "Yazar - Deneme2.epub"); _e.write_epub(yol2, kitap)
kit2 = K.cevir(yol2)
hepsi = " ".join(b["metin"]["tr"] for b in kit2["bloklar"]) + " " + " ".join(v["metin"]["tr"] for v in kit2["dipnotlar"].values())
kayip = [k for k in range(1, 13) if f"Not {k}:" not in hepsi]
dene("notun içindeki [5] işaret sayılmaz, hiçbir not kaybolmaz", not kayip, f"kaybolan: {kayip}")
dene("not başındaki nokta atılır ('. Hûd' -> 'Hûd')", any(v["metin"]["tr"].startswith("Hûd, 11/7") for v in kit2["dipnotlar"].values()),
     [v["metin"]["tr"][:20] for v in kit2["dipnotlar"].values()][:14])

print("SONUC: HEPSI GECTI" if not kalan else f"SONUC: {len(kalan)} KALDI: " + "; ".join(kalan))
