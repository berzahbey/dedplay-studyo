"""Tur 1/B testleri: Translate tamamen çıktı; Türkçe olmayan kitap Stüdyo'da açık bir hatayla durur;
OpenITI (Arapça) kitap yalnız kendi dilinde EPUB olur. httpx gerektirmez. Çalıştırma (sunucuda, kod klasöründe):
  docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/app:/k berzahbey/dedplay-studyo:latest python tests/test_ceviri_yok.py"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
kok = tempfile.mkdtemp()
os.environ["DATA_DIR"] = os.path.join(kok, "kutuphane")
os.environ["STUDYO_DATA_DIR"] = os.path.join(kok, "studyo")
os.makedirs(os.environ["STUDYO_DATA_DIR"])

from app import birlesik, clients, db, worker
from app import main as studyo
from kutuphane import depo
from kutuphane import kitap as K
from kutuphane import main as kmain

BASARI = []


def ok(kosul, ad):
    BASARI.append(bool(kosul))
    print(("GECTI " if kosul else "KALDI ") + ad)


yollar = {getattr(r, "path", None) for r in birlesik.app.router.routes}
ok("/api/jobs/{job_id}/translation" not in yollar and "/api/kitaplar/{kid}/cevir" not in yollar,
   "Çeviri adresleri yok (/translation, /cevir)")
ok(not any(a.startswith("tr_") for a in dir(clients)) and not hasattr(clients, "TRANSLATE"), "Stüdyo'da Translate istemcisi yok")
ok("Translate" not in kmain.SERVISLER, "Kütüphane durum ekranında Translate yok")
ok(not any(hasattr(depo, a) for a in ("_otomatik_ceviri", "ceviri_izleyici", "_studyo_bekleyen", "ceviri")),
   "Kütüphane'de çeviri işleri yok")

# Stüdyo servis kontrolü yalnız Kitap Okuma ve Osmanlıca'ya bakar
sorulan = []
class _Cevap:
    status_code = 200
clients.requests.get, _eski_get = (lambda url, timeout=4: sorulan.append(url) or _Cevap()), clients.requests.get
s = studyo.services()
clients.requests.get = _eski_get
ok(sorted(s) == ["okuma", "osmanlica"] and not any("8060" in u for u in sorulan), "Servis kontrolü: Kitap Okuma ve Osmanlıca")

# Türkçe olmayan kitap: açık hata, Translate'e gitmez
db.init()
w = worker.Worker()
jid = db.create_job("kitab.txt", "ar")
with open(db.source_path(jid, "kitab.txt"), "w", encoding="utf-8") as f:
    f.write("الحمد لله رب العالمين")
try:
    w.step(db.get(jid))
    ok(False, "Türkçe olmayan kitap hata verir")
except RuntimeError as e:
    ok("Türkçe değil" in str(e) and db.get(jid)["stage"] == "detect", "Türkçe olmayan kitap açık bir hatayla durur")

# Türkçe kitap eskisi gibi seslendirme/Osmanlıca aşamasına geçer
jid2 = db.create_job("kitap.txt", "tr")
with open(db.source_path(jid2, "kitap.txt"), "w", encoding="utf-8") as f:
    f.write("Bu bir Türkçe kitaptır.")
w.step(db.get(jid2))
ok(db.get(jid2)["stage"] == "produce", "Türkçe kitap seslendirme ve Osmanlıca aşamasına geçer")

# Translate'te kalmış eski iş: anlaşılır hata
db.update(jid, stage="translate", tr_state="hata", tr_job=7)
try:
    w.step(db.get(jid))
    ok(False, "Eski çeviri işi hata verir")
except RuntimeError as e:
    ok("çeviri kaldırıldı" in str(e), "Translate'te kalmış eski iş anlaşılır bir hatayla durur")
worker.resume(jid)  # eski tr_state'li işte Translate'e gitmeden sürdür
ok(db.get(jid)["status"] == "active", "Eski işte 'Sürdür' Translate'e gitmeden çalışır")
ok(worker._original_parts(db.get(jid)) == [], "Türkçe olmayan işten metin parçası çıkmaz")

# OpenITI (Arapça) kitap: yalnız Arapça EPUB
kit = K.yeni({"baslik": {"ar": "الاقتصاد في الاعتقاد"}, "yazar": {"ar": "الغزالي"}, "asil_dil": "ar", "kaynak": {"tur": "openiti"}})
K.blok_ekle(kit, "p", {"ar": "الحمد لله رب العالمين"})
ok(depo.surumler(kit) == [("arapca", ["ar"])], "Arapça kitaptan yalnız Arapça EPUB sürümü")

print("SONUC: HEPSI GECTI" if all(BASARI) else f"SONUC: {BASARI.count(False)} TEST KALDI")
