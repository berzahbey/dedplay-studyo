"""0.5.37: taranmış içindekiler sayfasında Tesseract okuması (numaralar) ile Surya okuması (yazı) birleşir.
Veri: tests/icindekiler_dinde_kirk.json (Dinde Kırk Prensip s.5-8, gerçek satırlar)."""
import json
import os
from types import SimpleNamespace as N

from kutuphane import kaynak as S

HATA = []


def kontrol(ad, kosul):
    print(("TAMAM  " if kosul else "HATA   ") + ad)
    if not kosul:
        HATA.append(ad)


veri = json.load(open(os.path.join(os.path.dirname(__file__), "icindekiler_dinde_kirk.json"), encoding="utf-8"))
olcek = 72 / S._SURYA_DPI
eski_sayfalar, yeni_sayfalar, tess_sayfalar = [], [], []
for no in sorted(veri["tesseract"], key=int):
    tess = [{"text": t, "x0": x0, "x1": (525 if "…" in t else x0 + 6 * len(t)), "top": top, "bot": top + 14, "h": 14,
             "n": len(t.split())} for t, x0, top in veri["tesseract"][no]]
    sur = S._surya_satirlari([N(text=t, bbox=b) for t, b in veri["surya"][no]], olcek, None)
    tess_sayfalar.append(tess)
    yeni_sayfalar.append(S._toc_okumalari_birlestir(tess, sur))

girdiler = S.icindekiler_girdileri(yeni_sayfalar)
basliklar = [g["baslik"] for g in girdiler]
no = {g["baslik"]: g.get("no") for g in girdiler}

# nokta dizisi çöpü gider
for b in basliklar:
    kontrol("çöpsüz: " + b, not any(x in b.split() for x in ("e", "w", "we", "a", "â", "4", "8", "TA", "A", "*", "ce")))
# Tesseract'ın kaybettiği son kelime Surya'dan
for b in ("Namazla Ilgilidir", "Oruçla İlgilidir", "Allah Teâlâ'yı Zikretmekle İlgilidir", "Sünnet'e Uymakla Ilgilidir"):
    kontrol("tamamlandı: " + b, b in basliklar)
# bütünüyle çöp satır Surya'nın yazısını alır, numara Tesseract'tan
kontrol("RİNE -> Şükretmektir (372)", "Şükretmektir" in basliklar and no.get("Şükretmektir") == "372" and "RİNE" not in basliklar)
kontrol("Kızmamaktır 202", no.get("Kızmamaktır") == "202")
kontrol("Kibirli Olmamaktır 250", no.get("Kibirli Olmamaktır") == "250")
kontrol("Tevbe Etmektir 323", no.get("Tevbe Etmektir") == "323")
kontrol("Nefisle Hasb-i Hal Etmek 483", no.get("Nefisle Hasb-i Hal Etmek") == "483")
# İLİM sayfa numarası (Roma rakamı) sayılmaz
kontrol("BİRİNCİ BÖLÜM: İLİM", "BİRİNCİ BÖLÜM: İLİM" in basliklar)
kontrol("kırıntı satırı (e w e) yok", "e w e" not in basliklar and not any(b.startswith("ÖNSÖZ ") for b in basliklar))
# sıradan sapan küçük numara (nokta dizisi rakam okunmuş)
kontrol("Beşinci Fazilet numarasız (… 5 değil)", no.get("Beşinci Fazilet") is None)
kontrol("Onuncu Prensip numarasız (… 4 değil)", all(g.get("no") != "4" for g in girdiler))
# her Fazilet ve Prensip yerinde (Surya çıktısı kadar)
for ad in ("Birinci", "İkinci", "Üçüncü", "Dördüncü", "Beşinci", "Altıncı", "Yedinci", "Sekizinci", "Dokuzuncu", "Onuncu"):
    kontrol(ad + " Fazilet", ad + " Fazilet" in basliklar)
kontrol("girdi sayısı %d (90 beklenir)" % len(girdiler), len(girdiler) == 90)

# eski okuma yoksa Tesseract satırları aynen
kontrol("eski okuma yok: değişmez", S._toc_okumalari_birlestir(tess_sayfalar[0], []) == tess_sayfalar[0])
# temiz Tesseract satırı aynen kalır (eski okuma aynı yazıyı veriyorsa)
temiz = [{"text": "Birinci Bölüm … 15", "x0": 60, "x1": 520, "top": 100, "bot": 114, "h": 14},
         {"text": "Mantık Nedir? … 17", "x0": 60, "x1": 520, "top": 120, "bot": 134, "h": 14},
         {"text": "Ek … 30", "x0": 60, "x1": 520, "top": 140, "bot": 154, "h": 14},
         {"text": "9", "x0": 300, "x1": 310, "top": 800, "bot": 812, "h": 12}]
eski = [{"text": "Birinci Bölüm ..........", "x0": 60, "x1": 520, "top": 99, "bot": 115, "h": 16},
        {"text": "Mantık Nedir? ..........17", "x0": 60, "x1": 520, "top": 119, "bot": 135, "h": 16},
        {"text": "Ek .........", "x0": 60, "x1": 520, "top": 139, "bot": 155, "h": 16}]
kontrol("temiz okuma değişmez", S._toc_okumalari_birlestir(temiz, eski) == temiz)
# Roma rakamı
for t, b in (("xii", True), ("XIV", True), ("iv", True), ("12", True), ("- 7 -", True),
             ("İLİM", False), ("ILIM", False), ("MİM", False), ("CİLD", False), ("IIII", False)):
    kontrol("sayfa numarası mı: %s -> %s" % (t, b), S._toc_no_mu(t) == b)

# 0.5.37b: atılan numara sonraki doğru numarayı attırmaz (deneme PDF'i: 5, 26, 7, 47, 8)
satir = [{"text": t, "x0": 60, "x1": 520, "top": 100 + 20 * i, "bot": 114 + 20 * i, "h": 14, "n": 2}
         for i, t in enumerate(["ÖNSÖZ … 5", "BİRİNCİ BÖLÜM … 26", "İKİNCİ BÖLÜM … 7", "Kelâmın Önemi … 47", "SONUÇ … 8"])]
kontrol("sıra: 5 26 7 47 8 -> 5 - 7 - 8", [g.get("no") for g in S.icindekiler_girdileri([satir])] == ["5", None, "7", None, "8"])

# 0.5.37c: gövde cümlesi içindekiler başlığı sayılmaz; büyük harfli başlık satırı ve başlıkla başlayan satır sayılır
kontrol("cümle: Bu prensip namazla ilgilidir.", S._toc_puan("Bu prensip namazla ilgilidir.", "Namazla İlgilidir") == 0)
kontrol("cümle: iradesiyle", S._toc_puan("Bu prensip Allah teâlâ'nın iradesiyle ilgilidir.", "Allah Teâlâ'nın İradesiyle İlgilidir") == 0)
kontrol("başlık satırı: ALTINCI FAZİLET: İHLÂS VE SIDK'TIR", S._toc_puan("ALTINCI FAZİLET: İHLÂS VE SIDK'TIR", "İhlâs ve Sıdk'tır") == 2)
kontrol("başlık satırı: ALTINCI FAZİLET (önek)", S._toc_puan("ALTINCI FAZİLET: İHLÂS VE SIDK'TIR", "Altıncı Fazilet") == 2)
kontrol("başlık satırı: C BEŞİNCİ FAZİLET: ŞÜKRETMEKTİR.", S._toc_puan("C BEŞİNCİ FAZİLET: ŞÜKRETMEKTİR.", "Şükretmektir") > 0)
kontrol("aynı: Kızmamaktır.", S._toc_puan("Kızmamaktır.", "Kızmamaktır") == 3)
kontrol("OCR hatalı başlık: Kizmamaktir.", S._toc_puan("Kizmamaktir.", "Kızmamaktır") > 0)
kontrol("noktasız başlık: Mantık nedir", S._toc_puan("Mantık nedir", "Mantık Nedir?") > 0)

# 0.5.37d: tek harfli kırıntı satırı atılır, 'we' Surya'daki 've' sayılmaz, satır içinde biten cümle başlık değil
r = lambda t, top, x0=60: {"text": t, "x0": x0, "x1": 520, "top": top, "bot": top + 14, "h": 14}
tess = [r("Yataktan Kalkmak e 4 e 6 m … 66", 100), r("a", 112, 250), r("Libas Giymek /Giyinmek 4 8 8 a a … 67", 122),
        r("Ruküa gitmek ve Secde Etmek e e we … 81", 144), r("BİRİNCİ BÖLÜM", 166), r("İLİM e ce 4 .. * NN", 188), r("w", 200, 300),
        r("FASIL-I1 … 129", 222)]
sur = [r("Yataktan Kalkmak ....................", 99), r("Libas Giymek/Giyinmek ...............", 121),
       r("Rukûa gitmek ve Secde Etmek . . . . . . . .", 143), r("BİRİNCİ BÖLÜM", 165), r("ilim ..........", 187),
       r("FASIL-11 ..........", 221)]
yazi = [x["text"] for x in S._toc_okumalari_birlestir(tess, sur)]
kontrol("kırıntı 'a' ve 'w' atılır", "a" not in yazi and "w" not in yazi)
kontrol("Yataktan Kalkmak ayrı kalır", "Yataktan Kalkmak … 66" in yazi and "Libas Giymek … 67" in yazi)
kontrol("we != ve: Ruküa gitmek ve Secde Etmek … 81", "Ruküa gitmek ve Secde Etmek … 81" in yazi)
kontrol("FASIL-I1 kalır", any(x.startswith("FASIL-I1") for x in yazi))
kontrol("cümle satır içinde bitiyor", S._toc_puan("Bu prensip sünnet'e uymakla ilgilidir. Sünnetten", "Sünnet'e Uymakla İlgilidir") == 0)
kontrol("başlık: Birinci Bölüm: Kavram ve Terim", S._toc_puan("Birinci Bölüm: Kavram ve Terim", "Kavram ve Terim") > 0)

print("SONUC: HEPSI GECTI" if not HATA else "SONUC: %d HATA" % len(HATA))
