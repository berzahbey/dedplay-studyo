"""0.5.33 gerileme testi: Arapça yazının (ve vefk tablolarının) Türkçe OCR'ından kalan Latin harfli çöp
(Ey Oğul, Esmaul hüsna, El-Afâk, Felsefenin Temel İlkeleri, Filozofların Tutarsızlığı kuru deneme raporlarından)
paragraf, başlık ve dipnotta silinir; transkripsiyon (Esmâ listeleri, dualar), âyet künyesi, kaynakça, Roma rakamlı
başlık, tarih ve gerçek Türkçe kalır.
11 Ekim taraması (bütün kitaplar, 68 bulgu): harekeli âyet, büyük harfli başlıkta OCR ı/l'si (KıYASLAR, elVAHHÂB),
OCR hatalı cümle, kaynakça, dizin, dipnot numaralı başlık (ETMEKTİR1), çöple birlikte âyet atfı korunur; Arap harfli satıra dokunulmaz. Metin kaynağında (EPUB/DOCX/TXT) ve Türkçe olmayan kitapta hiçbir şey silinmez."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kutuphane import kaynak as S

kalan = []


def dene(ad, kosul):
    print(("GECTI " if kosul else "KALDI ") + ad)
    if not kosul:
        kalan.append(ad)


COP = ["V ili iîûjlii ollîl Jliî l-Sıl", ", ^ ^ tr ^ C/f <..Jp", "•,û) jı;^5>>", "İL__ü'jG’J. ‘^ \\ t\"' ^", "iT^lı \\'j:",
       "on;- ^ ^ 'Olİ", "jj Ji. ^'}i\\ ^ 'j, lij", "Jij ^\"^'j ı^'^\" vL^", "Ji. LİL4 üic^ij \\Jîry i4ij o-f '4^'*.^. uij",
       ".0^*11,l£Xİ\\.^<^>«11", ". ^ ^ o jÇ il'", "İ£Xİ\\ \\A\\", "\" Ö \\ ç o } D. O u Z C f o f t / » —* / —» ı ı. ^ H",
       "AA911111119111AA91A11A1111AoA 11911 1719", "YE1 10Y 10E1Y 10 E YY 1 E 9 Y", "VYOYYI qVAYYYOI + IIEIYIV",
       "222 ccc 222-111222 cccc dd bb", "EE YOTT ZZZ YAIAJJIAJ 022", "î 11 1 ı S u 1 13 16 i", "•iii,^-,„"]
KAL = ["Allâhümme kün lená velâ tekün", "Isra sOresi/79", "Tevbe sûresi/95 Kchfsûresi/107-108 \" m.",
       "\"Vahidun, habisûr, latîfun. ehadün, Basîrun, Bâriun, Kebîrun, Kuddusûn, Hayyün\" En iyisini Allah bilir.",
       "ESMAİ A'ZAMIN ÖZELLİKLERİ", "107. FASIL", "\"Bismillahi'rrahmâni'rrahîm.", "KALBTE MUHUBBET",
       "\"Şaheti'l-vücuhu ve ümiyeti'l-ebsaru.\"", "\"Efehasibtüm ennema haleknaküm abesen....\"", "Elkuddüsü Elmüheyminü Elazizü",
       "Elkabizü Errâfiü", "Elvali Elbatînü", "Ennûrü Ennâfiü", "Elmuizzü Elbasirü", "el'KAVIY el'METIN i o elVELÎY", "III: ŞEKlL",
       "111. Şekil 11. Şekil", "(Şekil: 1)", "INSANI NEFS", "4. Vehmiyat 5 Musellemât", "25 Zilkade 1379/ 1960", "20 Ağustos 1968",
       "1 — Ni'met.", "Fadîl İbni İyâz:", "(1) Kasas Súresi, âyet: 83", "En'âm, 76", "Şebe', 24", "Kâria, 6-11", "Mü'min 40/16)",
       "Hanbel 3/17)", "ISBN 975-290-630-3", "Tel: 28-08-03", "TEHÂFÜT EL-FELÂSİFE", "c — Tehâfüt ei-Felâsife:",
       "Lelong, m. Actualité de Ghazzâli IBLA 21 (1958), pp. 195-212.", "(Maurice Bouyges, Essai, p. 65)",
       "Rahman, S.M. Al-Ghazâlî. IC 1 (1927), pp. 406-411).", "IMAM-Igazali", "Allah (C.C.):", "ei'KUDDÜS*",
       "\"In yeşe' yüskini'r-rîhu fey yazlalne revâkide ala zahrihi\"", "1 - Dehriyyun (Materyelistl er)",
       "Elmüntekimü Ettevâbü Malikülmülki zülcelali velikram Elganiyyü Elmugni", "Muzaf isimlerdende;", "Hz. Ali (r.a.):",
       "— Evet, dedi.", "A — ZAMAN", "B — İRTİKÂ (Yücelme) TABİRİ", "II. BÖLÜM", "XIII. Fasıl", "Hicrî 1111 senesinde vefat etti.",
       "3üncü mertebe", "( وإن الى ربك المنتهى ) «Muhakkak ki", "Watt, W.M.A. forgery in al Ghazâlî's Mishkât? JRAS, 1949, pp. 5-22.",
       "Cabanelas, d. Un capitulo inedito de Algazel sobre la «razon».", "A = B ise B = A olur.", "Şiîler ve Sünnîler"]
KAL.append("۲ م ۲ MYJ9 ETAV ( ۳ )")  # Arap harfi içeren satıra dokunulmaz (vefk tablosu parçası)
exec(open(os.path.join(os.path.dirname(__file__), "ocr_copu_tarama.txt"), encoding="utf-8").read())  # K2, C2: 11 Ekim taraması
KAL += K2
COP += [t for t in C2 if t != "J/-İ »ü"]  # kısa başlık artığı kalır (bilinen)
for t in COP:
    dene("çöp: " + t[:40], S._ocr_copu(t))
for t in KAL:
    dene("kalır: " + t[:40], not S._ocr_copu(t))

# kitaba_cevir: başlık, paragraf ve dipnot
KUNYE = {"baslik": {"tr": "D"}, "yazar": {"tr": ""}, "asil_dil": "tr"}


def kitap(metin_kaynagi=False, dil="tr"):
    og = [{"tur": "baslik", "metin": "BİRİNCİ BÖLÜM", "seviye": 1, "boy": 14},
          {"tur": "p", "boy": 10, "metin": "Allah'a hamd olsun ki bizi doğru yola iletti{{n0001}} ve bize bu kitabı okumayı nasip etti."},
          {"tur": "baslik", "metin": "jj Ji. ^'}i\\ ^ 'j, lij", "seviye": 2, "boy": 12},
          {"tur": "p", "boy": 10, "metin": "YE1 10Y 10E1Y 10 E YY 1 E 9 Y"},
          {"tur": "p", "boy": 10, "metin": "Âlim olan kimse ilmiyle amel eder{{n0002}} ve insanlara faydalı olur."},
          {"tur": "baslik", "metin": "İKİNCİ BÖLÜM", "seviye": 1, "boy": 14},
          {"tur": "p", "boy": 10, "metin": "Elkuddüsü Elmüheyminü Elazizü"}]
    notlar = {"n0001": "Fâtiha sûresi/6", "n0002": "\" Ö \\ ç o } D. O u Z C f o f t / » —* / —» ı ı. ^ H"}
    return S.kitaba_cevir(og, notlar, dict(KUNYE), metin_kaynagi=metin_kaynagi, dil=dil)


kit = kitap()
bas = [b["metin"]["tr"] for b in kit["bloklar"] if b["tur"] == "baslik"]
par = [b["metin"]["tr"] for b in kit["bloklar"] if b["tur"] == "p"]
hepsi = " ".join(bas + par)
dene("çöp başlık silinir", not any("lij" in b for b in bas) and len(bas) == 2)
dene("çöp paragraf silinir", "10E1Y" not in hepsi)
dene("gerçek başlıklar kalır", "BİRİNCİ BÖLÜM" in bas[0] and "İKİNCİ BÖLÜM" in bas[1])
dene("Esmâ satırı kalır", any("Elmüheyminü" in p for p in par))
dene("çöp dipnot silinir", "n0002" not in kit["dipnotlar"])
dene("çöp dipnotun atfı metinden kalkar", not any("{{n0002}}" in p for p in par) and any("amel eder ve insanlara" in p for p in par))
dene("gerçek dipnot ve atfı kalır", "n0001" in kit["dipnotlar"] and any("iletti{{n0001}}" in p for p in par))

# metin kaynağında (EPUB/DOCX/TXT) 0.5.33 kuralı çalışmaz: kural açıkken ve kapalıyken kitap birebir aynı
asil = S._ocr_copu
acik = kitap(metin_kaynagi=True)
S._ocr_copu = lambda p: False
kapali = kitap(metin_kaynagi=True)
S._ocr_copu = asil
dene("metin kaynağında 0.5.33 hiçbir şeyi değiştirmez", acik["bloklar"] == kapali["bloklar"] and acik["dipnotlar"] == kapali["dipnotlar"])

print("SONUC: HEPSI GECTI" if not kalan else "SONUC: KALAN %d: %s" % (len(kalan), "; ".join(kalan)))
