"""0.5.44 gerileme testi (19 Ekim): sayfa katmanı (ana metin planı adım 4). Konumla bulunan sayfa üst bilgisi
(kaynak._sayfa_ust_bilgileri) ve metin sütununun dışına taşan çıplak kenar numarası (kaynak._kenar_numaralari_konumla).
Çalıştırma: docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/k:/app -e TR_KELIME=/app/app/data/tr_kelime.txt berzahbey/dedplay-studyo:latest python tests/test_0544.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kutuphane import kaynak as K

kalan = []
H, W = 842.0, 595.0


def dene(ad, ok, ayrinti=""):
    print(("GECTI " if ok else "KALDI ") + ad + ("" if ok else f"\n   {ayrinti}"))
    if not ok:
        kalan.append(ad)


def satir(t, top, x0=60.0, x1=530.0, boy=20.0):
    return {"text": t, "h": boy, "top": top, "bot": top + boy, "x0": x0, "x1": x1, "n": len(t.split()), "kalin": False,
            "blok": 0, "ocr": True, "surya": True}


GOVDE = ["Bu sebeple Allah teâlâ'yı seven bir kimse onun sevdiği", "kulları da sever ve bu sevginin alameti şudur ki",
         "kendisini ondan uzaklaştıran her şeyi terk eder", "ve gideceği yolu gündüzü ve gecesiyle aydınlık bilir",
         "bundan sonra bu yoldan ancak azabı hakedenler sapar", "çünkü bilmek ile amel etmek birbirinden ayrı değildir"]


def sayfa(ust, govde_bas=80.0, govde=GOVDE, ust_boy=20.0):
    rows = [satir(t, 30.0, boy=ust_boy) for t in ([ust] if ust else [])]
    rows += [satir(t, govde_bas + 26 * k) for k, t in enumerate(govde)]
    return rows


def calistir(ustler, nolar=None, **kw):
    satirlar = [sayfa(u, **kw) for u in ustler]
    sayfalar = [(list(r), W, H, True) for r in satirlar]
    n = K._sayfa_ust_bilgileri(satirlar, sayfalar, nolar or [None] * len(ustler))
    return n, satirlar


def ilkler(satirlar):
    return [min(r, key=lambda x: x["top"])["text"] for r in satirlar]


# 1) Dinde Kırk: kitap adı + bölüm adı + sayfa numarası tek satır, OCR her sayfada başka okuyor
ustler = ["Dinde Kirk Prensip Peygambere iman etmek %d" % (41 + 2 * k) if k % 3 else "Dunle Kirk Prensip Mal sevgisi %d" % (41 + 2 * k)
          for k in range(12)]
n, s = calistir(ustler, nolar=[str(41 + 2 * k) for k in range(12)])
dene("numaralı üst bilgi (kitap adı + bölüm + numara) çıkar", n == 12 and all(i.startswith("Bu sebeple") for i in ilkler(s)), f"{n} {ilkler(s)[:2]}")

# 2) numarası okunamamış ama her sayfada benzer üst bilgi (OCR farkları, baştaki artık)
ust = ["Kitabu'I-Burhan", "K i tibu ' I -Burh a n", "Kitab u 'I-Burhin", "_AZ Ki li b u 'I-Burhi n", "Ki tabu'I -Bu rhin",
       "Kitabu' I-Burhin", "Kiti bu'I -Burhan", "Kitabu'I -Burhan"]
n, s = calistir(ust)
dene("numarasız benzer üst bilgi (OCR farkları) çıkar", n == 8 and all(i.startswith("Bu sebeple") for i in ilkler(s)), f"{n} {ilkler(s)}")

# 3) Kudsî Hadisler: her sayfa aynı yerde bölüm başlığıyla başlıyor, önceki sayfa cümle sonuyla bitiyor -> başlık kalır
govde_biten = GOVDE[:-1] + ["çünkü bilmek ile amel etmek birbirinden ayrı değildir."]
satirlar = [sayfa("%d. KUDSİ HADİS" % (k + 1), govde=govde_biten) for k in range(10)]
sayfalar = [(list(r), W, H, True) for r in satirlar]
n = K._sayfa_ust_bilgileri(satirlar, sayfalar, [str(k + 3) for k in range(10)])
dene("her sayfadaki bölüm başlığı (önceki sayfa cümle sonu) kalır", n == 0 and ilkler(satirlar)[0] == "1. KUDSİ HADİS", f"{n} {ilkler(satirlar)[:2]}")

# 4) üst bilgisi olmayan kitap: sayfanın ilk satırı gövde (boşluk yok) -> dokunulmaz
n, s = calistir([None] * 10, nolar=[str(k) for k in range(10)])
dene("üst bilgisi olmayan kitap aynı", n == 0 and all(len(r) == len(GOVDE) for r in s), str(n))

# 5) üstte boşlukla ayrılmış ama ne numaralı ne tekrar eden satır (bölüm başlığı) kalır
n, s = calistir(["BİRİNCİ BÖLÜM", "İKİNCİ MES'ELE", "GİRİŞ", "SONUÇ", "ÜÇÜNCÜ FASIL", "NOTLAR HAKKINDA", "MUKADDİME"])
dene("tekrar etmeyen başlıklar kalır", n == 0, str(n))

# 6) numara satır başında madde numarası gibi ("3. KUDSİ") ise numaralı üst bilgi sayılmaz
adlar = ["Nefsin Terbiyesi", "Kalbin Halleri", "Sabır ve Şükür", "Tevekkülün Mânâsı", "Rıza Makamı", "Zühd Hakkında",
         "Takvanın Alâmetleri", "Haramdan Sakınmak"]
n, s = calistir(["%d. %s" % (5 + k, adlar[k]) for k in range(8)], nolar=[str(5 + k) for k in range(8)])
dene("'5. Bölüm' madde numarası üst bilgi sayılmaz", n == 0, str(n))

# 7) üst bilgi kutusu büyük okunmuş (boşluk az görünüyor) ama numaralı -> yine çıkar
n, s = calistir(["Dinde Kirk Prensip Mal sevgisi %d" % (200 + k) for k in range(8)], nolar=[str(200 + k) for k in range(8)],
                ust_boy=42.0, govde_bas=79.0)
dene("büyük kutulu numaralı üst bilgi çıkar", n == 8, str(n))


# kenar numaraları
def kenar_sayfa(no, x_no=44.0, ek=" olmayan unsurlardı ve bu nâkiller İslamiyeti"):
    rows = [satir("ortaya çıkmaya başlamıştır ki bu çağda İslam medeniyetinin kapısı", 100 + 13 * k, x0=66.0, x1=390.0, boy=11)
            for k in range(6)]
    rows.append(satir(str(no) + ek, 180.0, x0=x_no, x1=390.0, boy=11))
    return rows


sl = [kenar_sayfa(7 + 2 * k) for k in range(10)]
n = K._kenar_numaralari_konumla(sl)
dene("sütun dışına taşan kenar numarası çıkar", n == 10 and sl[0][-1]["text"] == "olmayan unsurlardı ve bu nâkiller İslamiyeti",
     f"{n} {sl[0][-1]['text']}")

sl = [kenar_sayfa(7 + 2 * k, x_no=66.0) for k in range(10)]
dene("sütun içindeki satır başı sayısı kalır", K._kenar_numaralari_konumla(sl) == 0 and sl[0][-1]["text"].startswith("7 "))

sl = [kenar_sayfa(k + 1, ek=".Onlara gökten rızık indirdik ve dedik ki") for k in range(12)]
dene("Bakara düzeni '13.Onlara' (numara + nokta) kalır", K._kenar_numaralari_konumla(sl) == 0 and sl[0][-1]["text"].startswith("1.Onlara"))

sl = [kenar_sayfa(n) for n in (40, 7, 300, 12, 88, 3, 150, 9, 61, 2)]
dene("düzenli artmayan sayılar kalır", K._kenar_numaralari_konumla(sl) == 0)

print("SONUC: HEPSI GECTI" if not kalan else f"SONUC: {len(kalan)} KALDI: " + "; ".join(kalan))
