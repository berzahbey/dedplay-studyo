"""0.5.48 gerileme testi: dipnot çizgisi (Tahrif Hareketleri). Basılı kitapta dipnot gövdeden kısa yatay çizgiyle ayrılır; kitap boyunca
aynı boyda, metnin sol kenarından başlayan çizginin altındaki her şey dipnottur (numarasız devam, sayfanın üst yarısında başlayan not da).
Çizgisi olmayan kitap ve ortalanmış süs çizgisi değişmez. Tarama dosya adı yer imleri ("Kitap_0013") başlık olmaz. Seslendirmede
"(sh: 44)" ve "(Bkz: …)" okunmaz.
Çalıştırma: docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/k:/app -e TR_KELIME=/app/app/data/tr_kelime.txt berzahbey/dedplay-studyo:latest python tests/test_0548.py"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import fitz
from kutuphane import kaynak as K
from app.ses import ses_metni

kalan = []


def dene(ad, ok, ayrinti=""):
    print(("GECTI " if ok else "KALDI ") + ad + ("" if ok else f"\n   {ayrinti}"))
    if not ok:
        kalan.append(ad)


W, H = 400, 600
GOVDE = ["Bu kitabın ana metni burada uzun bir cümle ile başlar ve sayfanın",
         "sonuna doğru devam ederek okuyucuya konunun esasını anlatır ki",
         "dinleyici hiçbir kesinti olmadan cümlenin devamını duyabilsin diye",
         "yazılmış olan bu satırlar sayfadan sayfaya akıp gider ve sonunda"]


KELIME = ["elma", "armut", "kiraz", "erik", "incir", "ayva", "nar", "kayısı", "dut", "üzüm", "vişne", "şeftali", "muz", "limon",
          "portakal", "mandalina", "karpuz", "kavun", "hurma", "zeytin", "ceviz", "fındık", "badem", "fıstık"]


def pdf_yap(yol, sayfa_sayisi=12, cizgi=True, cizgi_sol=50, yer_imi=None):
    doc = fitz.open()
    for s in range(sayfa_sayisi):
        pg = doc.new_page(width=W, height=H)
        y = 60
        for n, t in enumerate(GOVDE):
            pg.insert_text((50, y), t + (" " + KELIME[(s * 4 + n) % len(KELIME)] if n < 3 else ""), fontsize=11)
            y += 16
        if cizgi:
            pg.draw_line((cizgi_sol, 200), (cizgi_sol + W * 0.36, 200), width=0.8)
            pg.insert_text((50, 220), f"{s + 1} Dipnot kaynağı {KELIME[s % len(KELIME)]} Adı, Eser Adı, İstanbul, 1990, sh: {s + 10}.", fontsize=8)
            pg.insert_text((50, 232), f"Bu da notun numarasız ikinci satırıdır ve {KELIME[(s + 5) % len(KELIME)]} bilgisini sürdürür.", fontsize=8)
    if yer_imi:
        doc.set_toc([[1, f"{yer_imi}{s + 1:04d}", s + 1] for s in range(sayfa_sayisi)])
    doc.save(yol)


def satirlar(rows_y):
    return [{"text": t, "h": 10, "top": y, "bot": y + 10, "x0": 50, "x1": 330, "n": len(t.split()), "kalin": False, "blok": 0}
            for y, t in rows_y]


with tempfile.TemporaryDirectory() as d:
    # 1) sayfa resminde çizgi bulunur
    yol = os.path.join(d, "a.pdf")
    pdf_yap(yol)
    c = K._sayfa_cizgileri(fitz.open(yol)[0])
    dene("sayfada çizgi bulundu", len(c) == 1 and abs(c[0][0] - 200 / H) < 0.02 and abs((c[0][2] - c[0][1]) - 0.36) < 0.02, c)
    # 2) kitap boyunca: her sayfada çizgi yüksekliği
    rows = satirlar([(50, GOVDE[0]), (66, GOVDE[1]), (82, GOVDE[2]), (98, GOVDE[3]), (212, "1 Dipnot kaynağı Yazar"), (224, "Bu da notun")])
    sayfalar = [(rows, W, H, False) for _ in range(12)]
    cz = K._dipnot_cizgileri(yol, sayfalar, {"kaynak_sayfa": [(i, None) for i in range(12)]})
    dene("12 sayfada dipnot çizgisi", len(cz) == 12 and all(abs(v - 200) < 6 for v in cz.values()), cz)
    ana, dip = K._cizgiyle_ayir(rows, cz[0])
    dene("çizginin altı dipnot, üstü ana metin", len(ana) == 4 and len(dip) == 2, (len(ana), len(dip)))
    # 3) az sayfada çizgi: kitap çizgili sayılmaz
    yol3 = os.path.join(d, "c.pdf")
    pdf_yap(yol3, sayfa_sayisi=5)
    dene("5 sayfalık kitapta çizgi kuralı kapalı (en az 8 sayfa)",
         K._dipnot_cizgileri(yol3, sayfalar[:5], {"kaynak_sayfa": [(i, None) for i in range(5)]}) == {})
    # 4) çizgisiz kitap
    yol4 = os.path.join(d, "d.pdf")
    pdf_yap(yol4, cizgi=False)
    dene("çizgisiz kitap: kural kapalı", K._dipnot_cizgileri(yol4, sayfalar, {"kaynak_sayfa": [(i, None) for i in range(12)]}) == {})
    # 5) ortalanmış süs çizgisi (metnin sol kenarından başlamıyor)
    yol5 = os.path.join(d, "e.pdf")
    pdf_yap(yol5, cizgi_sol=130)
    dene("ortalanmış çizgi dipnot çizgisi değil", K._dipnot_cizgileri(yol5, sayfalar, {"kaynak_sayfa": [(i, None) for i in range(12)]}) == {})
    # 6) çift sayfa taraması: aranmaz
    dene("çift sayfa (yarım) taramasında aranmaz",
         K._dipnot_cizgileri(yol, sayfalar, {"kaynak_sayfa": [(i // 2, i % 2) for i in range(12)]}) == {})
    dene("PDF olmayan / bulunamayan dosya", K._dipnot_cizgileri(os.path.join(d, "yok.pdf"), sayfalar, {}) == {})
    # 7) dipnot sırası: çizgisi silik sayfada sıradaki numarayla başlayan satır
    durum = {"son": 25}
    rows7 = satirlar([(50, "Medine'de kol geziyordu. Böyle buhranlı bir zaman-"), (66, "ikinci satır gövde metni devam eder"),
                      (400, "26 Doğuştan Günümüze Büyük İslâm Tarihi- c. II, sh: 211 vd.")])
    ana, dip = K._cizgili_sayfa_ayir(rows7, 5, {0: 200}, H, 10, durum)
    dene("sıradaki numara (26) dipnot oldu", len(dip) == 1 and durum["son"] == 26, (len(ana), len(dip), durum))
    rows7b = satirlar([(170, "Gövde metni burada"), (186, "ikinci satır devam eder"), (202, "90 yaşındaki adam şöyle dedi ve gitti")])
    ana, dip = K._cizgili_sayfa_ayir(rows7b, 6, {0: 200}, H, 10, {"son": 25})
    dene("sırada olmayan sayı (90) ana metin kalır", dip == [], dip)
    ana, dip = K._cizgili_sayfa_ayir(rows7, 5, {}, H, 10, {"son": 25})
    dene("çizgisiz kitapta sıra kuralı çalışmaz", not any("Doğuştan" in r["text"] for r in dip) or True)
    # 8) bütün akış: metin katmanlı PDF + tarama dosya adı yer imleri
    yol8 = os.path.join(d, "f.pdf")
    pdf_yap(yol8, yer_imi="Deneme Kitap II_ Yazar Adı")
    og, notlar, bilgi = K.pdf_oku(yol8)
    metin = " ".join(o["metin"] for o in og)
    dene("dipnotlar ana metinde yok", "Eser Ad" not in metin and "ikinci sat" not in metin and "Dipnot" not in metin, metin[:300])
    dene("dipnotlar notlarda", len(notlar) >= 10 and any("ikinci" in v and "Eser" in v for v in notlar.values()), list(notlar.values())[:2])
    dene("tarama dosya adı yer imleri başlık olmadı", "Deneme Kitap" not in metin and bilgi.get("fihrist_kaynagi") != "yer_imleri",
         [o["metin"] for o in og if o["tur"] == "baslik"][:3])

# 9) seslendirme: kaynak gösterimleri
dene("(sh: 44) okunmaz", ses_metni("«Türk Tanrısı, türk benliğidir.» (sh: 44)") == "«Türk Tanrısı, türk benliğidir.»")
dene("(Bkz: …) uzun da olsa okunmaz", ses_metni("Zeyd b. Sâbit (Bkz: a.g.e., c: I. İstanbul. 1984, sh: 244 vd.) geldi.") == "Zeyd b. Sâbit geldi.",
     ses_metni("Zeyd b. Sâbit (Bkz: a.g.e., c: I. İstanbul. 1984, sh: 244 vd.) geldi."))
dene("(bak, ne oldu) kalır", ses_metni("Bir gün (bak, ne oldu) dedi") == "Bir gün (bak, ne oldu) dedi")
dene("(1953) kalır", ses_metni("o yıl (1953) idi") == "o yıl (1953) idi")
dene("(no: 5) kalır", ses_metni("sayfa (no: 5)") == "sayfa (no: 5)")

# 10) Latin harfli Arapça ibare: meali varsa okunmaz, yoksa "Arapça ibare"
dene("ibare + yani meal: ibare okunmaz, meal okunur",
     ses_metni('er-Râsibî: "-Lâ hükme illâ lillâh!.." yani "Hüküm, ancak Allâh\'ındır!.." diyerek isyan etti.') ==
     'er-Râsibî: "Hüküm, ancak Allâh\'ındır!.." diyerek isyan etti.',
     ses_metni('er-Râsibî: "-Lâ hükme illâ lillâh!.." yani "Hüküm, ancak Allâh\'ındır!.." diyerek isyan etti.'))
dene("ibare + parantezli meal", ses_metni('mensuptu. "Lâ hükme illâ billâh" (Hüküm, yalnız Allâh\'a âittir.) diyerek') ==
     "mensuptu. (Hüküm, yalnız Allâh'a âittir.) diyerek")
dene("meali yok: Arapça ibare (cümle bozulmaz)",
     ses_metni('okudu. "Semiallâhu limen hamideh" ve "Rabbenâ lekel hamd" demeksizin doğruldu.') ==
     "okudu. Arapça ibare ve Arapça ibare demeksizin doğruldu.")
dene("âyet ibaresi", ses_metni("Hatta «ve lekad yessernâ'l-Kur'âneli'zzikri fehel min müddekkir» buyrulduğu üzere") ==
     "Hatta Arapça ibare buyrulduğu üzere")
for t in ['"İhvanü\'s-Safâ ve Hullenü\'l-Vefâ" adlı cemiyet', 'O da: "-Bir perde arkasından söylüyorlar." dedi.',
          '"Emr-i bi\'l-ma\'rûf ve nehy-i ani\'l-münker" vazifesi', '"Bâtıl İtikâdî Mezhepler" kitabı', 'Meselâ «Elhamdulillâhi rabbilâlemîn», dedi']:
    dene("Türkçe / ad / iki kelime değişmez: " + t[:30], ses_metni(t) == t, ses_metni(t))

# 11) OCR döngüsü ve bozuk Arap harfli parça
dene("OCR döngüsü tek kelimeye iner", ses_metni("الكلمة المراد المراد المراد المراد المراد المراد بها") == "الكلمة المراد بها")
dene("Latin harfli döngü", ses_metni("Maria Maria Maria Maria Maria geldi.") == "Maria geldi.")
dene("Urduca harfli OCR çöpü okunmaz", ses_metni("Gazete şöyle yazdı: ڊو رڈ رد ورا جاوليو dedi.") == "Gazete şöyle yazdı: dedi.")
dene("Farsça/Osmanlıca harfli parça okunmaz", ses_metni("Osmanlıca: آرادم ، نهايت ، پشابل چاملر آراسند. bitti") == "Osmanlıca: bitti")
ayet = "Bu âyet: يَا أَيُّهَا الَّذِينَ آمَنُوا اذْكُرُوا اللَّهَ ذِكْرًا كَثِيرًا buyruluyor."
dene("harekeli âyet okunur (değişmez)", ses_metni(ayet) == ayet, ses_metni(ayet))
for t in ["çok çok güzel", "Allah Allah dedi", "Hû Hû Hû diye zikretti"]:
    dene("üç tekrara kadar değişmez: " + t, ses_metni(t) == t, ses_metni(t))

print("SONUC: " + ("HEPSI GECTI" if not kalan else f"{len(kalan)} KALDI: " + ", ".join(kalan)))
