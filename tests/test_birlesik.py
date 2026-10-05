"""Tek uygulama (app/birlesik.py) testleri: Kütüphane ve Stüdyo adresleri aynı süreçte, çakışmasız.
httpx gerektirmez (TestClient yok): adreslerin fonksiyonları doğrudan çağrılır.
Çalıştırma (sunucuda, kod klasöründe):
  docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/app:/k berzahbey/dedplay-studyo:latest python tests/test_birlesik.py"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
kok = tempfile.mkdtemp()
os.environ["DATA_DIR"] = os.path.join(kok, "kutuphane")
os.environ["STUDYO_DATA_DIR"] = os.path.join(kok, "studyo")
os.makedirs(os.environ["STUDYO_DATA_DIR"])

from app import birlesik
from app import db, worker
from kutuphane import depo
from kutuphane import kaynak

BASARI = []


def ok(kosul, ad):
    BASARI.append(bool(kosul))
    print(("GECTI " if kosul else "KALDI ") + ad)


def bul(yol, yontem="GET"):
    for r in birlesik.app.router.routes:
        if getattr(r, "path", None) == yol and yontem in (getattr(r, "methods", None) or ()):
            return r.endpoint
    return None


yollar = {getattr(r, "path", None) for r in birlesik.app.router.routes}
for y in ("/", "/oku/{kid}", "/api/kitaplar", "/api/kitaplar/{kid}/blok/{bid}", "/api/kaynak", "/api/durum",
          "/api/jobs", "/api/jobs/from-kutuphane", "/api/browse", "/api/services", "/static", "/studyo"):
    ok(y in yollar, f"Adres var: {y}")

ikiz = {}
for r in birlesik.app.router.routes:
    for m in (getattr(r, "methods", None) or {"MOUNT"}):
        ikiz[(getattr(r, "path", None), m)] = ikiz.get((getattr(r, "path", None), m), 0) + 1
ok(all(v == 1 for v in ikiz.values()), "Hiçbir adres iki kez tanımlı değil")

ok(db.DATA_DIR == os.environ["STUDYO_DATA_DIR"] and depo.VERI == os.environ["DATA_DIR"],
   "Stüdyo ve Kütüphane verileri ayrı klasörlerde (STUDYO_DATA_DIR / DATA_DIR)")

basla = [h.__module__ + "." + h.__name__ for h in birlesik.app.router.on_startup]
ok(any(h.startswith("kutuphane.") for h in basla) and any(h.startswith("app.") for h in basla),
   "Başlangıçta hem Kütüphane hem Stüdyo işleri çalışır")

# Başlangıç işlerini çalıştır (arka plan döngüleri açılmadan)
worker.worker.start = lambda: None
depo.baslat = lambda: None
for h in birlesik.app.router.on_startup:
    h()
ok(os.path.exists(db.DB_PATH), "Stüdyo veritabanı kendi klasöründe kuruldu")
ok(os.path.isdir(depo.KITAPLAR), "Kütüphane kitap klasörü kuruldu")

ok("Kütüphane" in bul("/")(), "Ana sayfa Kütüphane ekranı")
r = bul("/studyo")()
ok(r.path.endswith(os.path.join("app", "static", "index.html")) and "/api/jobs" in open(r.path, encoding="utf-8").read(),
   "Eski Stüdyo ekranı /studyo adresinde")
ok(bul("/api/jobs")() == [], "Stüdyo iş listesi çalışıyor (boş)")
ok(bul("/api/kitaplar")() == [], "Kütüphane kitap listesi çalışıyor (boş)")
mount = [r for r in birlesik.app.router.routes if getattr(r, "path", None) == "/static"][0]
ok(os.path.isfile(os.path.join(mount.app.directory, "index.html")), "Stüdyo'nun dosyaları (/static) sunuluyor")

# zeyrek onarımı Stüdyo'nun duzelt.py'sinde de geçerli (aynı modül)
from app import duzelt
ok(duzelt is kaynak.DZ, "Stüdyo ve Kütüphane aynı duzelt modülünü kullanır")
duzelt.gecerli_mi("olmak")
ok(all(duzelt.gecerli_mi(k) for k in ("olanlar", "olacak", "yapılacak")), "zeyrek onarımı Stüdyo tarafında da geçerli")

print("SONUC: HEPSI GECTI" if all(BASARI) else f"SONUC: {BASARI.count(False)} TEST KALDI")
