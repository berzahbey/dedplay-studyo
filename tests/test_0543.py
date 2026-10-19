"""0.5.43 gerileme testi (19 Ekim): seslendirmeye giden metinden yazarın kaynak gösterimleri çıkar (app/ses.py, worker.parts_to_epub).
Yazılı çıktılara dokunulmaz. Kaynak gösterimi olmayan satır birebir aynı kalır (sesi yeniden üretilmez).
Çalıştırma: docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/k:/app -e TR_KELIME=/app/app/data/tr_kelime.txt berzahbey/dedplay-studyo:latest python tests/test_0543.py"""
import os, sys, tempfile, zipfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.ses import ses_metni as S

kalan = []


def dene(ad, girdi, beklenen):
    c = S(girdi)
    ok = c == beklenen
    print(("GECTI " if ok else "KALDI ") + ad + ("" if ok else f"\n   cikan:    {c!r}\n   beklenen: {beklenen!r}"))
    if not ok:
        kalan.append(ad)


# çıkanlar
dene("âyet atfı (Kehf, 110; Fussilet, 6)", 'insanım" (Kehf, 110; Fussilet, 6) demesini', 'insanım" demesini')
dene("köşeli âyet atfı [Enâm, 149].", "delil vardır” [Enâm, 149]. Hâkim", "delil vardır”. Hâkim")
dene("Sûresi'li atıf", "erenlerdir.» (Haşr sûresi, 9) buyuruyor", "erenlerdir.» buyuruyor")
dene("numara/sûre (20/Taha: 50)", "yöneltendir (20/Taha: 50) dedi", "yöneltendir dedi")
dene("bozuk parantez [Bakara, 179)", "hayat vardır” [Bakara, 179) mealindeki", "hayat vardır” mealindeki")
dene("satır başı -Kehf, 54", "kâfirdir. -Kehf, 54", "kâfirdir.")
dene("Bakara 2/40.", "korkun. Bakara 2/40. Yola", "korkun. Yola")
dene("hadis kaynağı (Müslim)", 'sığının." (Müslim) "Kabir', 'sığının." "Kabir')
dene("hadis kaynağı (Buharî, Müslim)", "Hz. Âişe (Buharî, Müslim) dedi", "Hz. Âişe dedi")
dene("hadis kaynağı dizisi", "korkun. 43 Buhârî, Tevhîd, 35, Bed'ü'l-Halk, 8; Müslim, İmân, 312; Tirmizî, Cennet, 15; Ahmed b. Hanbel, Müsned, 2/313, 438. Yola",
     "korkun. Yola")
dene("Bk. ile hadis dizisi", 'değerlendirir)." Bk. Müslim, Birr; 33, ibn Mâce, Zühd, 9.', 'değerlendirir)."')
dene("sayfa atfı (M. 54)", "biraz (M.6) palazlaştı ve (M. 93) dedi.", "biraz palazlaştı ve dedi.")
dene("(bak., s. 204)", "devam etmiştir (bak., s. 204). Bu", "devam etmiştir. Bu")
dene("eser + sayfa (Ta'rîfât, 130)", "kastediyorum (Ta'rîfât, 130) ve (Mevzûât el-Ulûm, I, 358).", "kastediyorum ve.")
dene("not işaretleri (3) [1] (٢) (Haşiye-1) (*)", "dedi (3) ve [1] ile (٢) sonra (Haşiye-1) bitti (*).", "dedi ve ile sonra bitti.")
dene("yapışık not numarası", "ifade edilmiştir:124 Lâ ilâhe", "ifade edilmiştir: Lâ ilâhe")
dene("açıklama + atıf: yalnız atıf çıkar", "esirliğin (İslamın kabul ettiği esirlik anlamı içerisinde; bak., s. 127) evlilik",
     "esirliğin (İslamın kabul ettiği esirlik anlamı içerisinde) evlilik")
# kalanlar (kaynak gösterimi değil)
for ad, t in (("yıl (1953)", "O (1953) yılında"), ("tarih", "(19 Kasım 1908) günü"), ("ölüm tarihi", "Taberî (ölm. 310/923) ve (Öl. 950)"),
              ("hicrî/milâdî yıl", "(H. 505) ve (M. 1058) yılında"), ("açıklama", "(yani bir yıl) sonra"), ("sayı değeri", "(400.000) kişi"),
              ("uzun açıklama", "kimsedir (yukarıda s. 182'de sözü edilen durum bunun dışında kalır). Nefis"),
              ("anlatıda ad + yıl", "Ahmed, 1950 yılında İstanbul'a gitti."), ("anlatıda sûre adına benzeyen kelime", "Rum, 1453 yılında fethedildi."),
              ("dergi numarası", "Volkan No:107 Sayı: 111"), ("Arapça ünlem", "انْتَثَرَتْ ! وَاِذَا"), ("noktalama boşluğu", "Nasıl ? diye sordu ,,")):
    dene("kalır: " + ad, t, t)
# seslendirme EPUB'u kaynak gösterimsiz, ayet numarası yine okunmaz
from app.worker import parts_to_epub
yol = os.path.join(tempfile.mkdtemp(), "k.epub")
parts_to_epub([{"tr": 'GİRİŞ\n1. Elif-Lâm-Mîm.\n"Ben de sizin gibi bir insanım" (Kehf, 110) dedi. (M. 54)'}], "Kitap", yol)
x = "".join(zipfile.ZipFile(yol).read(n).decode("utf-8") for n in zipfile.ZipFile(yol).namelist() if n.endswith("b0001.xhtml"))
ok = "Kehf" not in x and "M. 54" not in x and "insanım" in x and "Elif-Lâm-Mîm." in x and ">1." not in x
print(("GECTI " if ok else "KALDI ") + "seslendirme EPUB'unda kaynak gösterimi yok")
if not ok:
    kalan.append("epub")
print("SONUC: HEPSI GECTI" if not kalan else f"SONUC: {len(kalan)} KALDI: " + "; ".join(kalan))
