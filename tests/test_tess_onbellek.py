"""0.5.34: Tesseract önbelleği. Taklit Tesseract ile önbellek mantığı; gerçek Tesseract varsa (sunucu imajı) bir PDF
sayfasının ilk (Tesseract) ve ikinci (önbellek) okumasının birebir aynı olduğu sınanır."""
import os, sys, shutil, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
kok = tempfile.mkdtemp()
os.environ["OCR_ONBELLEK"] = os.path.join(kok, "onb")
os.environ.pop("TESS_ONBELLEK", None)
from kutuphane import kaynak as S
import pytesseract
import pytesseract.pytesseract as PT
from PIL import Image, ImageDraw

kalan = []


def dene(ad, kosul):
    print(("GECTI " if kosul else "KALDI ") + ad)
    if not kosul:
        kalan.append(ad)


asil_data, asil_str, asil_surum = PT.image_to_data, PT.image_to_string, pytesseract.get_tesseract_version
sayac = {"d": 0, "s": 0}


def sahte_data(img, lang=None, config="", output_type=None, **k):
    sayac["d"] += 1
    return {"text": [f"{lang}|{config}|{img.size}"], "conf": [90], "left": [0], "width": [1]}


def sahte_str(img, lang=None, config="", **k):
    sayac["s"] += 1
    return f"{lang}|{config}"


def kur(data=sahte_data, string=sahte_str):
    pytesseract.image_to_data = PT.image_to_data = data
    pytesseract.image_to_string = PT.image_to_string = string


def kaldir():
    pytesseract.image_to_data, PT.image_to_data = asil_data, asil_data
    pytesseract.image_to_string, PT.image_to_string = asil_str, asil_str
    pytesseract.get_tesseract_version = asil_surum


S._tess_surum = None
pytesseract.get_tesseract_version = lambda: "5.5.0-taklit"
kur()
a = Image.new("L", (100, 40), 255)
b = Image.new("L", (100, 40), 255); ImageDraw.Draw(b).point((5, 5), 0)

d1 = S._tess_data(a, lang="tur", config="--psm 7")
d2 = S._tess_data(a, lang="tur", config="--psm 7")
dene("Aynı görüntü ikinci kez Tesseract'a gitmez", sayac["d"] == 1 and d1 == d2)
d2["text"][0] = "değişti"
dene("Önbellekten dönen sözlük her seferinde yeni (yerinde değişiklik kayda sızmaz)",
     S._tess_data(a, lang="tur", config="--psm 7")["text"][0] != "değişti" and sayac["d"] == 1)
S._tess_data(b, lang="tur", config="--psm 7")
dene("Tek pikseli farklı görüntü yeniden okunur", sayac["d"] == 2)
S._tess_data(a, lang="ara", config="--psm 7")
S._tess_data(a, lang="tur", config="--psm 6")
S._tess_data(a, config="--psm 7")
dene("Dil, ayar ya da dilsiz çağrı farklı kayıt", sayac["d"] == 5)
S._tess_data(a.crop((0, 0, 50, 40)), lang="tur", config="--psm 7")
S._tess_data(a.crop((0, 0, 50, 40)), lang="tur", config="--psm 7")
dene("Kesit (crop) görüntü de önbellekte", sayac["d"] == 6)

s1, s2 = S._tess_string(a, lang="tur", config="--psm 8"), S._tess_string(a, lang="tur", config="--psm 8")
dene("image_to_string önbellekte", sayac["s"] == 1 and s1 == s2 == "tur|--psm 8")
S._tess_data(a, lang="tur", config="--psm 8")
dene("data ve string kayıtları karışmaz", sayac["d"] == 7)

S._tess_surum = None
pytesseract.get_tesseract_version = lambda: "5.6.0-taklit"
S._tess_data(a, lang="tur", config="--psm 7")
dene("Tesseract sürümü değişince yeniden okunur", sayac["d"] == 8)

yol = S._tess_onbellek_yolu("data", a, "tur", "--psm 7")
with open(yol, "w") as f:
    f.write("{bozuk")
S._tess_data(a, lang="tur", config="--psm 7")
S._tess_data(a, lang="tur", config="--psm 7")
dene("Bozuk kayıt yeniden okunur ve onarılır", sayac["d"] == 9)

os.environ["TESS_ONBELLEK"] = "0"
S._tess_data(a, lang="tur", config="--psm 7")
dene("TESS_ONBELLEK=0 kapatır", sayac["d"] == 10)
os.environ.pop("TESS_ONBELLEK")
os.environ["OCR_ONBELLEK"] = "0"
S._tess_data(a, lang="tur", config="--psm 7")
dene("OCR_ONBELLEK=0 kapatır", sayac["d"] == 11)
os.environ["OCR_ONBELLEK"] = os.path.join(kok, "onb")


def hata(*x, **k):
    sayac["d"] += 1
    raise RuntimeError("tesseract yok")


kur(data=hata)
try:
    S._tess_data(b, lang="xyz", config="")
    hatali = False
except RuntimeError:
    hatali = True
kur()
S._tess_data(b, lang="xyz", config="")
dene("Hata önbelleğe girmez (yukarı atılır, sonra yeniden denenir)", hatali and sayac["d"] == 13)

# test taklidi (yalnız paket adı değiştirilmiş, tess55_taklit / test_surya3 gibi) önbelleği kullanmaz
kaldir()
S._tess_surum = None
pytesseract.get_tesseract_version = lambda: "5.6.0-taklit"
PT.image_to_data = sahte_data
taklit = {"n": 0}
pytesseract.image_to_data = lambda *x, **k: (taklit.__setitem__("n", taklit["n"] + 1), {"text": ["taklit"]})[1]
r1 = S._tess_data(a, lang="tur", config="--psm 7")
r2 = S._tess_data(a, lang="tur", config="--psm 7")
dene("Testlerin taklidi önbelleği okumaz ve yazmaz", r1 == r2 == {"text": ["taklit"]} and taklit["n"] == 2)
kaldir()

kod = open(S.__file__, encoding="utf-8").read()
import re
dogrudan = re.findall(r"pytesseract\.image_to_(?:data|string)\(", kod)
dene("kaynak.py'de önbelleksiz Tesseract çağrısı yok (yalnız _tess_data ve _tess_string içinde)", len(dogrudan) == 2)

# gerçek Tesseract (sunucu imajı): taranmış sayfa iki kez okunur, ikincisi önbellekten, sonuç birebir aynı
try:
    S._tess_surum = None
    gercek_var = bool(S._tess_surumu()) and "tur" in pytesseract.get_languages(config="")
except Exception:
    gercek_var = False
if gercek_var:
    import fitz
    from PIL import ImageFont
    font = None
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(f):
            font = ImageFont.truetype(f, 34)
            break
    resim = Image.new("L", (1240, 1754), 255)
    c = ImageDraw.Draw(resim)
    satirlar = ["BİRİNCİ BÖLÜM", "İnsanın şerefi ilim ve marifetledir.", "Allah Teâlâ kullarına rahmet eder;",
                "kalbin hastalıkları ise gıybet ve hasettir.", "", "17"]
    for k, t in enumerate(satirlar):
        c.text((150, 200 + k * 70) if t != "17" else (600, 1650), t, fill=0, font=font)
    pdf = os.path.join(kok, "sayfa.pdf")
    resim.save(pdf, "PDF", resolution=150)
    S._tess_surum = None
    os.environ["OCR_ONBELLEK"] = os.path.join(kok, "gercek")
    t0 = time.time(); i1 = S._ocr_sayfa((pdf, 0, "tur")); t1 = time.time() - t0
    kayit = sum(len(f) for _, _, f in os.walk(os.path.join(kok, "gercek")))
    t0 = time.time(); i2 = S._ocr_sayfa((pdf, 0, "tur")); t2 = time.time() - t0
    print(f"  ilk okuma {t1:.2f} sn, önbellekten {t2:.2f} sn, {kayit} kayıt; metin: {[r['text'] for r in i1[1]]}")
    dene("Gerçek Tesseract: önbellekten okunan sayfa birebir aynı", i1 == i2 and kayit >= 1)
    dene("Gerçek Tesseract: sayfa okundu (metin boş değil)", any("ilim" in r["text"] for r in i1[1]))
else:
    print("  (gerçek Tesseract yok: o bölüm atlandı)")

shutil.rmtree(kok, ignore_errors=True)
print("SONUC: " + ("HEPSI GECTI" if not kalan else "KALAN: " + ", ".join(kalan)))
