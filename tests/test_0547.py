"""0.5.47: (1) Osmanlica seridi cikti uretimini (EPUB/PDF/DOCX, Studyo zinciri) beklemez: cikti isi hafif seride devredilir.
(2) DOCX: paragraflar dogrudan govdeye eklenir (karesel yavaslik yok), cikti eskisiyle ayni.
Calistirma: PYTHONPATH=. python3 tests/test_0547.py"""
import io, os, sys, tempfile, time, types, threading, zipfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
GECICI = tempfile.mkdtemp()
os.environ["DATA_DIR"] = GECICI
from kutuphane import depo

kalan = []


def dene(ad, kosul):
    print(("GECTI " if kosul else "KALDI ") + ad)
    if not kosul:
        kalan.append(ad)


olay = []
kl = threading.Lock()


def kayit(*a):
    with kl:
        olay.append(a + (time.time(),))


def sahte_osm(kid, zorla=False):
    kayit("osm_basla", kid)
    time.sleep(0.3)
    kayit("osm_bit", kid)


def sahte_epub(kid):
    kayit("cikti_basla", kid)
    time.sleep(2.0)            # buyuk kitabin PDF/DOCX'i gibi uzun
    depo.durum_yaz(kid, asama="hazır")
    kayit("cikti_bit", kid)


zincir = []
depo._osmanlica = sahte_osm
depo.epub_uret = sahte_epub
depo._studyoya_zincirle = lambda kid, **kw: zincir.append((kid, kw))
depo.K = types.SimpleNamespace(yukle=lambda p: {"kunye": {"asil_dil": "tr"}})
depo.durum_yaz("yarim", asama="Çıktılar sırada", is_turu="osm_cikti", is_arg=None, tur="epub")
depo.baslat()
for k in ("x", "y", "z"):
    depo.is_ekle("osmanlica", k, tur="epub")
time.sleep(1.2)
dene("Durum yazisi: 'Çıktılar sırada' ve isin turu saklanir",
     any(depo.durum_oku(k).get("is_turu") == "osm_cikti" for k in ("x", "y", "z")))
time.sleep(9)
t = {(o, k): z for o, k, z in olay}
dene("Osmanlica seridi x'in ciktisini beklemeden y'yi cevirdi", t[("osm_basla", "y")] < t[("cikti_bit", "x")])
dene("Uc kitabin Osmanlicasi, ilk kitabin ciktisi bitmeden bitti", t[("osm_bit", "z")] < t[("cikti_bit", "x")])
dene("Her kitabin ciktisi bir kez uretildi", sorted(k for o, k, _ in olay if o == "cikti_bit") == ["x", "y", "yarim", "z"])
dene("Cikti isi Osmanlicasi bittikten sonra basladi", all(t[("cikti_basla", k)] >= t[("osm_bit", k)] for k in ("x", "y", "z")))
dene("Studyo zinciri her kitap icin guncelle=True ile cagrildi", sorted(k for k, kw in zincir if kw.get("guncelle")) == ["x", "y", "yarim", "z"])
dene("Hepsi sonunda hazir", all(depo.durum_oku(k).get("asama") == "hazır" for k in ("x", "y", "z", "yarim")))
dene("Yeniden baslatmada yarim cikti isi surdu", ("cikti_bit", "yarim") in t)

# --- DOCX ---
from app import export
parts = [{"tr": "satır %d\nikinci %d" % (i, i), "osm": "سطر %d\nایكنجی %d" % (i, i)} for i in range(300)]
job = {"title": "Deneme", "status": "done", "osm_title": "دنمه"}
for v in ("tr", "osm", "iki"):
    z = zipfile.ZipFile(io.BytesIO(export.to_docx(job, parts, v)))
    xml = z.read("word/document.xml").decode("utf-8")
    dene("DOCX %s: sectPr govdenin sonunda" % v, xml.rstrip().endswith("</w:sectPr></w:body></w:document>"))
    dene("DOCX %s: paragraf sayisi" % v, xml.count("<w:p>") + xml.count("<w:p ") >= (600 if v != "iki" else 1200))
buyuk = [{"tr": "\n".join("satır %d" % j for j in range(50)), "osm": "\n".join("سطر %d" % j for j in range(50))} for i in range(600)]
t0 = time.time()
export.to_docx(job, buyuk, "iki")
dene("DOCX 60 bin paragraf 30 saniyeden kisa", time.time() - t0 < 30)

print("SONUC: HEPSI GECTI" if not kalan else f"SONUC: {len(kalan)} TEST KALDI")
os._exit(1 if kalan else 0)
