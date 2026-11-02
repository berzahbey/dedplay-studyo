"""0.5.60: (1) günlük sınır yüzünden bekleyen denetim yeniden başlatmada kaybolmaz (aşaması "hazır" görünse de);
(2) sesi olmayan parça seslendirme EPUB'unu düşürmez."""
import json, os, sys, tempfile, time, zipfile
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="t0560-")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
hata = []

# (2) boş parça
from app.worker import parts_to_epub  # noqa: E402
out = os.path.join(os.environ["DATA_DIR"], "s.epub")
try:
    parts_to_epub([{"tr": "Başlık\nBir cümle."}, {"tr": "  \n"}, {"tr": "İkinci\nBaşka cümle."}], "Deneme", out)
    adlar = zipfile.ZipFile(out).namelist()
    if not any(a.endswith("b0001.xhtml") for a in adlar) or not any(a.endswith("b0003.xhtml") for a in adlar):
        hata.append(f"bölümler eksik: {adlar}")
except Exception as e:
    hata.append(f"boş parça EPUB'u düşürdü: {type(e).__name__}: {e}")

# (1) bekleyen denetim
from kutuphane import depo  # noqa: E402
kid = "k" + "0" * 11
os.makedirs(depo.klasor(kid), exist_ok=True)
eklenen = []
depo.is_ekle = lambda *a, **k: eklenen.append(a)
depo.durum_yaz(kid, asama="hazır", denetim={"durum": "bekliyor", "devam": int(time.time()) - 10})
depo._bekleyen_denetim({"kimlik": kid, "asama": "hazır"})
time.sleep(6)
if ("denetim", kid, None) not in eklenen:
    hata.append(f"bekleyen denetim sıraya girmedi: {eklenen}")
eklenen.clear()
depo.durum_yaz(kid, denetim={"durum": "hazir"})
depo._bekleyen_denetim({"kimlik": kid, "asama": "hazır"})
time.sleep(6)
if eklenen:
    hata.append("bitmiş denetim yeniden sıraya girdi")
print("\n".join(hata) or "test_0560: hepsi geçti")
sys.exit(1 if hata else 0)
