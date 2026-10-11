"""0.5.36: zeyrek'in sıra hataları (kutuphane/zeyrek_onarim.py). Aynı kelime Python'un her açılışında (PYTHONHASHSEED)
aynı sonucu vermeli: önceden "zıddı", "zıddının", "öd" bazı açılışlarda geçersiz sayılıyordu (altın çıktı, 11 Ekim)."""
import os, subprocess, sys

kalan = []


def dene(ad, kosul):
    print(("  TAMAM  " if kosul else "  KALDI  ") + ad)
    if not kosul:
        kalan.append(ad)


KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KELIMELER = ["zıddı", "zıddının", "zıddını", "zıt", "öd", "ödü", "ödler", "ödemek", "ödedi", "ödüyor", "hakkı",
             "hakkında", "sırrı", "haddi", "reddi", "kitap", "kitabı", "gitti", "gidiyor", "olanlar"]
COCUK = (
    "import sys, logging\n"
    "sys.path[:0] = [%r]\n"
    "import kutuphane.zeyrek_onarim\n"
    "from app import duzelt as DZ\n"
    "logging.disable(logging.CRITICAL)\n"
    "if DZ._an() is None: print('ZEYREK_YOK'); sys.exit()\n"
    "print('SONUC ' + ' '.join('%%s=%%d' %% (w, DZ.gecerli_mi(w)) for w in %r))\n" % (KOK, KELIMELER))

sonuclar = {}
for tohum in ("0", "1", "2"):
    ortam = dict(os.environ, PYTHONHASHSEED=tohum)
    cikti = subprocess.run([sys.executable, "-c", COCUK], env=ortam, capture_output=True, text=True).stdout
    if "ZEYREK_YOK" in cikti:
        print("  (zeyrek yok: test atlandı)")
        print("SONUC: HEPSI GECTI")
        sys.exit()
    satir = [s for s in cikti.splitlines() if s.startswith("SONUC ")]
    sonuclar[tohum] = dict(x.split("=") for x in satir[0][6:].split()) if satir else {}
    print(f"  tohum {tohum}: geçersiz = {[w for w, v in sonuclar[tohum].items() if v != '1']}")

dene("üç tohumda da sonuç alındı", all(len(v) == len(KELIMELER) for v in sonuclar.values()))
dene("üç tohumun sonucu birebir aynı", sonuclar["0"] == sonuclar["1"] == sonuclar["2"])
for w in KELIMELER:
    dene(f"{w} geçerli (her tohumda)", all(v.get(w) == "1" for v in sonuclar.values()))
print("SONUC: " + ("HEPSI GECTI" if not kalan else "KALAN: " + ", ".join(kalan)))
