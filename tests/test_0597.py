"""0.5.97: Osmanlıca rik'a hattı. Okuma ekranlarında (Stüdyo oku.html, Kütüphane raf.html) Nesih/Rik'a düğmesi;
Osmanlıca EPUB'ların ayrı rik'a sürümleri (Aref Ruqaa gömülü, ڭ yerine ك, başlıkta "(Rik'a)", ayrı kimlik ve klasör).
Çalıştırma (sunucuda, kod klasöründe):
  docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/app:/k berzahbey/dedplay-studyo:latest python tests/test_0597.py"""
import os, sys, tempfile, zipfile
KOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, KOK)
kok = tempfile.mkdtemp()
os.environ["DATA_DIR"] = os.path.join(kok, "kutuphane")
os.environ["CIKTI_DIR"] = os.path.join(kok, "dedplay", "EPUB")
from kutuphane import cikti, depo, epub
from kutuphane import kitap as K

BASARI = []


def ok(kosul, ad):
    BASARI.append(bool(kosul))
    print(("GECTI " if kosul else "KALDI ") + ad)


# 1) Okuma ekranları
for ad in ("oku.html", "raf.html"):
    s = open(os.path.join(KOK, "kutuphane", "static", ad), encoding="utf-8").read()
    ok("Aref+Ruqaa" in s and 'id="hatBtn"' in s and ":root.rika" in s and "osm-hat" in s, f"{ad}: Rik'a düğmesi, yazı tipi, ayar")
    ok("\\u06AD" in s or "\\u06ad" in s, f"{ad}: rik'a görünümünde sağır kef düz kefe çevrilir")

# 2) EPUB sürümleri
kit = K.yeni({"baslik": {"tr": "Deneme Kitabı"}, "yazar": {"tr": "Yazar"}, "asil_dil": "tr", "kaynak": {"kimlik": "deneme-0597"}})
K.blok_ekle(kit, "h", {"tr": "Birinci Bölüm", "osm": "برنجی بولوم"}, seviye=1)
for i in range(3):
    K.blok_ekle(kit, "p", {"tr": "Senin gönlün geniştir.", "osm": "سنڭ كوڭلڭ كنیشدر."})
S = depo.surumler(kit)
ok([s[0] for s in S] == ["turkce", "osmanlica", "turkce-osmanlica", "osmanlica-rika", "turkce-osmanlica-rika"], "Sürümler: nesih + ayrı rik'a")
ok(all(len(s) == 2 for s in S[:3]) and all(s[2] == "rika" for s in S[3:]), "Nesih sürümleri değişmedi, rik'a sürümleri işaretli")


def oku(z):
    return {n: z.read(n).decode("utf-8", "replace") for n in z.namelist() if n.endswith((".xhtml", ".opf", ".css"))}


ne = os.path.join(kok, "n.epub"); ri = os.path.join(kok, "r.epub")
epub.uret(kit, ["osm"], ne)
epub.uret(kit, ["osm"], ri, hat="rika")
zn, zr = zipfile.ZipFile(ne), zipfile.ZipFile(ri)
n, r = oku(zn), oku(zr)
metin_n = "".join(v for k, v in n.items() if k.endswith(".xhtml"))
metin_r = "".join(v for k, v in r.items() if k.endswith(".xhtml"))
opf_n = "".join(v for k, v in n.items() if k.endswith(".opf")); opf_r = "".join(v for k, v in r.items() if k.endswith(".opf"))
css_r = "".join(v for k, v in r.items() if k.endswith(".css"))
ok("\u06ad" in metin_n and "Aref Ruqaa" not in "".join(n.values()), "Nesih EPUB aynen: sağır kef var, rik'a yok")
ok("\u06ad" not in metin_r and "سنك كوكلك" in metin_r, "Rik'a EPUB: ڭ düz kef ك yazılır")
ok("Aref Ruqaa" in css_r and any(x.endswith("ArefRuqaa-Regular.ttf") for x in zr.namelist())
   and any(x.endswith("ArefRuqaa-Bold.ttf") for x in zr.namelist()), "Rik'a EPUB: Aref Ruqaa gömülü ve CSS'te")
ok("ArefRuqaa" in opf_r, "Rik'a EPUB: yazı tipi manifestte")
ok("(Rik'a)" in opf_r and "(Rik'a)" not in opf_n, "Başlıkta (Rik'a) yalnız rik'a sürümünde")
import re
uid = lambda o: re.search(r'<dc:identifier[^>]*>([^<]+)<', o).group(1)
ok(uid(opf_n) != uid(opf_r), "Rik'a EPUB'un kimliği nesihten ayrı (okuyucuda iki ayrı kitap)")

# 3) Çıktı klasörleri
os.makedirs(cikti.CIKTI, exist_ok=True)
d = os.path.join(kok, "e"); os.makedirs(d)
import shutil
shutil.copy(ne, os.path.join(d, "osmanlica.epub")); shutil.copy(ri, os.path.join(d, "osmanlica-rika.epub"))
yaz = cikti.ciktiya_yaz(kit, [{"dosya": "osmanlica.epub", "diller": ["osm"]},
                              {"dosya": "osmanlica-rika.epub", "diller": ["osm"], "hat": "rika"}], d)
ok(len(yaz) == 2 and len({os.path.dirname(y) for y in yaz}) == 2 and any(y.split("/")[0].endswith(" (Rik'a)") for y in yaz),
   f"Rik'a EPUB ayrı klasöre yazılır {yaz}")
sil = cikti.epublari_sil(kit, [])
ok(len(sil) == 2, "Kitap silinince rik'a EPUB'u da silinir")

print("SONUC:", "HEPSI GECTI" if all(BASARI) else f"{BASARI.count(False)} TEST KALDI")
sys.exit(0 if all(BASARI) else 1)
