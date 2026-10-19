"""0.5.42 gerileme testi (19 Ekim): ana metin olmayan bölümler seslendirmeye gitmez.
Kaynakça, dizin, sözlük, kısaltmalar, kronoloji, sonnotlar (alt başlıklarıyla), yanlış-doğru cetveli, yayınevi künyesi Stüdyo parçasında
"Ek_" olur: EPUB ve PDF/DOCX/TXT/HTML'de kalır (bütün metin aynı), Kitap Okuma yalnız "Parca_" okur.
Gövdedeki numaralı paragraflar ("3. Hanbeli …"), "ANA KAYNAKLAR" gibi gövde bölümleri, yıllı tarih anlatısı seslendirmeye gider.
Ana metin dışı bölümü olmayan kitapta parçalar 0.5.41 ile birebir aynıdır.
Çalıştırma: docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/k:/app -e TR_KELIME=/app/app/data/tr_kelime.txt berzahbey/dedplay-studyo:latest python tests/test_0542.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kutuphane import kitap as K
from kutuphane import cikti as C

kalan = []


def dene(ad, kosul):
    print(("GECTI " if kosul else "KALDI ") + ad)
    if not kosul:
        kalan.append(ad)


def kitap(bolumler):
    """bolumler: [(başlık ya da None, seviye, [paragraflar])]"""
    kit = K.yeni({"baslik": {"tr": "Deneme Kitabı"}, "yazar": {"tr": "Yazar"}, "asil_dil": "tr", "kaynak": {"tur": "dosya"}})
    for bas, sv, ps in bolumler:
        if bas:
            K.blok_ekle(kit, "baslik", {"tr": bas}, seviye=sv)
        for p in ps:
            K.blok_ekle(kit, "p", {"tr": p})
    return kit


GOVDE = [f"Bu, kitabın {i}. paragrafıdır ve ana konuyu anlatır; dinleyici bunu dinlemelidir." for i in range(1, 8)]
KAYNAKCA = [f"Yazar {i}, Eser Adı {i}, Paris 19{50 + i}." for i in range(1, 12)]
DIZIN = [f"Kavram {i}: {i * 3}, {i * 7} vd., {i * 11}." for i in range(1, 12)]
NOTLAR = [f"{i} — Sübkî, Tabakât, IV, {100 + i}." for i in range(1, 9)]


def parcalar(kit):
    return C.studyo_parcalari(kit)


def ses(kit):
    return "\n".join(p["tr"] for p in parcalar(kit) if p["name"].startswith("Parca_"))


def tum(kit):
    return "\n".join(p["tr"] for p in parcalar(kit) if not p["name"].startswith("Dipnot_"))


# 1) Başlıkla tanınan bölümler
for bas in ("BİBLİYOGRAFYA", "KAYNAKÇA", "Kaynaklar", "GENEL DİZİNi", "TERIMLER INDEXI", "KISI. YER, VE ESER INDEXI",
            "FELSEFÎ TERİMLER SÖZLÜĞÜ", "KISALTMALAR", "KRONOLOJIK TABLO", "DIPNOTLAR", "MUKADDİMELERİN DİPNOTU",
            "YANLIŞ-DOĞRU CEDVELİ", "ÇAĞRI YAYINLARI"):
    kit = kitap([("GİRİŞ", 1, GOVDE), (bas, 2, ["Herhangi bir satır.", "Başka bir satır."])])
    s = ses(kit)
    dene(f"'{bas}' bölümü seslendirmeye gitmez", "Herhangi bir satır" not in s and "1. paragrafıdır" in s)
    dene(f"'{bas}' bölümü yazılı çıktılarda kalır", "Herhangi bir satır" in tum(kit))

# 2) Gövde bölümleri gider
for bas, ps in (("ANA KAYNAKLAR", ["Aşağıdaki bölümler, kelimenin dar anlamıyla İslam hukukunun kaynaklarını ele alır."] * 6),
                ("ŞÜPHENİN KAYNAKLARI", GOVDE), ("DÖRDÜNCÜ KAYNAK", GOVDE), ("ÖZLEŞMECİ TEPKİLER",
                 [f"{i}. Kuzey Nijerya'da {1890 + i} yılında bir idare kurulmuştu; o zaman uzun bir anlatı başladı ve sürdü, şöyle ki "
                  f"bu paragraf gövdenin numaralı bir paragrafıdır." for i in range(1, 7)]),
                ("SONUÇ", GOVDE)):
    kit = kitap([("GİRİŞ", 1, GOVDE), (bas, 2, ps)])
    dene(f"gövde bölümü '{bas}' seslendirmeye gider", ps[0] in ses(kit))

# 3) İçerikten tanınan bölümler (başlığı tanınmasa da)
kit = kitap([("GİRİŞ", 1, GOVDE), ("EK", 2, KAYNAKCA)])
dene("içerikten kaynakça (şehir + yıl) gitmez", "Paris 1951" not in ses(kit))
kit = kitap([("GİRİŞ", 1, GOVDE), ("EK", 2, DIZIN)])
dene("içerikten dizin ('Kavram: 3, 7 vd.') gitmez", "Kavram 1:" not in ses(kit))
kit = kitap([("GİRİŞ", 1, GOVDE), ("EK", 2, NOTLAR)])
dene("içerikten sonnot ('1 — Sübkî, Tabakât, IV, 101') gitmez", "Sübkî" not in ses(kit))
kit = kitap([("GİRİŞ", 1, [f"{i}- Bir zât, evinde yanan lambayı söndürüp karanlıkta oturdu ve şöyle dedi." for i in range(1, 8)])])
dene("gövdedeki numaralı liste ('1- Bir zât …') gider", "lambayı" in ses(kit))

# 4) Sonnotlar alt başlıklarla sürer: önceki başlığın tekrarı ya da not işaretli paragraflar; sonra gelen dizin listesi
kit = kitap([("BİRİNCİ MES'ELE", 2, GOVDE), ("İKİNCİ MES'ELE", 2, GOVDE), ("SONUÇ", 2, GOVDE),
             ("DIPNOTLAR", 2, ["Kontrol"]), ("BİRİNCİ MES'ELE", 2, ["(1) Ben derim ki bu söz doğru değildir.", "Uzun açıklama sürer."] * 4),
             ("İKİNCİ MES'ELE", 2, ["Ben derim ki, bu da böyledir ve uzun bir açıklamadır."] * 6),
             ("SONUÇ", 1, ["(1) Birinci Mes'eleye bakınız."]),
             ("BİBLİYOGRAFYA", 2, KAYNAKCA), ("XXIX", 1, ["Bağdat: xx, 218, 221", "Bursa: 12", "Asim Efendi: 252"] * 3)])
s = ses(kit)
dene("sonnot bölgesi: önceki başlığın tekrarı olan alt başlık gitmez", "bu da böyledir" not in s)
dene("sonnot bölgesi: 'SONUÇ' tekrarı gitmez", "Birinci Mes'eleye bakınız" not in s)
dene("dizinin devamı (liste biçimli alt başlık) gitmez", "Bağdat" not in s)
dene("ana metindeki bölümler gider", s.count("1. paragrafıdır") == 3)

# 5) Parça adları ve bütünlük
kit = kitap([("GİRİŞ", 1, GOVDE), ("BİBLİYOGRAFYA", 2, KAYNAKCA), ("EK BÖLÜM", 1, GOVDE)])
ad = [p["name"] for p in parcalar(kit)]
dene("parça adları sırayla: Parca_001, Ek_001, Parca_002", ad == ["Parca_001", "Ek_001", "Parca_002"])
dene("bütün metin (yazılı çıktılar) eksiksiz", all(k in tum(kit) for k in KAYNAKCA + GOVDE))

# 6) Ana metin dışı bölümü olmayan kitap: 0.5.41'deki gibi yalnız Parca_ (ve Dipnot_)
kit = kitap([("GİRİŞ", 1, GOVDE), ("BİRİNCİ BÖLÜM", 1, GOVDE * 3)])
dene("ana metin dışı bölümü olmayan kitapta Ek_ yok", not any(p["name"].startswith("Ek_") for p in parcalar(kit)))
dene("ses dışı blok yok", C.ses_disi_bloklar(K.gorunur(kit)) == {})

print("SONUC: HEPSI GECTI" if not kalan else f"SONUC: {len(kalan)} KALDI: " + "; ".join(kalan))
