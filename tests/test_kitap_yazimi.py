"""0.5.32 gerileme testi: kitabın kendi yazımı esas (Abidler Yolu, Ahiret Âleminin Sırları, Ariflerin Yolu, El-Afâk,
Felsefenin Temel İlkeleri, Filozofların Tutarsızlığı kuru deneme raporundan, 10 Ekim).
1) Harf onarımı kitapta en az 2 kez aynı geçen yazımı kitapta hiç geçmeyen yazıma çevirmez (ucüp -> uçup, sedden -> şedden,
   kisimdir -> kişimdir yapılmaz); kitap o harfi baştan sona kaybetmişse koruma kalkar (Âlemlerin Sırrı: sey -> şey).
2) Büyük I ile başlayan kelime: "Iste" -> "İşte" (eskiden "Işte"); "Isa" -> "İsa" kitapta hiç "İsa" yokken de.
3) Büyük harfli kelime: kitabın gövdesinde en çok geçen yazım (CINDEN -> CİNDEN, eskiden ÇİNDEN; SURESININ -> SURESİNİN).
4) Kitap içi onarım: birden çok aday varsa kitapta açık ara en sık olan (hir -> bir); südur (sudur 9, südür 4) ve
   meâdin (meâdın 2) değişmez; baştaki t büyük İ olur (tkinci -> İkinci)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kutuphane import kaynak as S
from app import duzelt as DZ

kalan = []


def dene(ad, kosul, bilgi=""):
    print(("GECTI " if kosul else "KALDI ") + ad + ("" if kosul else "  -> " + str(bilgi)))
    if not kosul:
        kalan.append(ad)


def kitap(*parcalar):
    """('kelime', adet) çiftlerinden ve normal Türkçe dolgu metninden kitap bağlamı."""
    dolgu = ["Bu kitapta işte şöyle bir şey anlatılır, insanın hâli ve çok güzel düşünceler üzerine konuşulur."] * 40
    S._kitap_baglami_kur(dolgu + [" ".join([k] * n) for k, n in parcalar])


# 1) harf onarımı, kitap korumalı
kitap(("ucüb", 19), ("ucüp", 13), ("kisimdir", 2), ("sedden", 2), ("Iste", 4), ("Isa", 14), ("sey", 11))
for eski, yeni in [("Kibir, hırs ve ucüp.", "Kibir, hırs ve ucüp."), ("Ucüp ne demektir?", "Ucüp ne demektir?"),
                   ("ilimler üç kisimdir:", "ilimler üç kisimdir:"), ("eydîhim sedden ve", "eydîhim sedden ve"),
                   ("Iste saâdet yolcusu", "İşte saâdet yolcusu"), ("Hz. Isa da", "Hz. İsa da"),
                   ("hiç bir sey kalmaz", "hiç bir şey kalmaz"), ("Cenab-1 Hakk'a", "Cenab-ı Hakk'a"),
                   ("kiymetli uzvun", "kıymetli uzvun")]:
    s = S._harf_onar_korumali(eski)
    dene("harf onarımı: " + eski, s == yeni, s)

# Âlemlerin Sırrı gibi ş'siz kitap: sey -> şey (kitapta hiç şey yok)
S._kitap_baglami_kur(["Bu sey icin bos yere bas, simdi asil is bu kisinin isidir sunu soyle " * 30, "sey sey sey"])
s = S._harf_onar_korumali("hiç bir sey kalmaz")
dene("ş'siz kitapta sey -> şey", s == "hiç bir şey kalmaz", s)
S._kitap_baglami_sil()

# bağlam yokken eski davranış (DZ.harfleri_onar + _harf_kaybi_onar)
for t in ["Hz. Isa da hiç bir sey bilmez, Cenab-1 Hak", "Ucüp ne demektir, kiymetli"]:
    dene("bağlamsız eskisiyle aynı: " + t, S._harf_onar_korumali(t) == S._harf_kaybi_onar(DZ.harfleri_onar(t)))

# 3) büyük harfli kelime
kitap(("cin", 13), ("çin", 2), ("suresinin", 5), ("mescide", 3), ("beşinci", 4), ("cimada", 2))
for eski, yeni in [("CINDEN", "CİNDEN"), ("CINLERI", "CİNLERİ"), ("SURESININ", "SURESİNİN"), ("MESCIDE", "MESCİDE"),
                   ("BESINCI", "BEŞİNCİ"), ("IKINCI", "İKİNCİ"), ("GIRIS", "GİRİŞ")]:
    s = S._turkce_kelime_onar(eski)
    dene("büyük harf: " + eski, s == yeni, s)
S._kitap_baglami_sil()
dene("büyük harf bağlamsız eskisi gibi: BESINCI", S._turkce_kelime_onar("BESINCI") == "BEŞİNCİ")

# 4) kitap içi onarım
def ici(cumle, *ek):
    dolgu = ["bir şey bir insan bir varlık ve bilgi ve gibi"] * 50
    return S._kitap_ici_onar([cumle] + dolgu + [" ".join([k] * n) for k, n in ek])[0]

s = ici("ber şey hir nedenle", ("hir", 136), ("hır", 25), ("lir", 6))
dene("hir -> bir (hır, lir de aday)", s == "ber şey bir nedenle", s)
s = ici("kendinden südur edenleri", ("südur", 3), ("südür", 4), ("sudur", 9))
dene("südur değişmez (sudur ve südür ikisi aday)", s == "kendinden südur edenleri", s)
s = ici("cümle-i meâdin yediyüzdür", ("meâdin", 4), ("meâdın", 2))
dene("meâdin -> meâdın yapılmaz", s == "cümle-i meâdin yediyüzdür", s)
s = ici("dünyasını ve âhıretini", ("âhıretini", 3), ("âhiretini", 2), ("âhiret", 20))
dene("âhıretini -> âhiretini", s == "dünyasını ve âhiretini", s)
s = ici("gıybet eder, giybet", ("giybet", 14), ("gıybet", 3))
dene("giybet -> gıybet (şapkasız)", s == "gıybet eder, gıybet", s)
s = ici("tkinci Mod ve tbn Sina", ("ikinci", 3), ("ibn", 3))
dene("baştaki t büyük İ", s == "İkinci Mod ve İbn Sina", s)
s = ici("dünya vc âhiret varhk", ("varlık", 5))
dene("vc -> ve, varhk -> varlık (0.5.31)", s == "dünya ve âhiret varlık", s)

print("SONUC: " + ("HEPSI GECTI" if not kalan else "%d TEST KALDI" % len(kalan)))
