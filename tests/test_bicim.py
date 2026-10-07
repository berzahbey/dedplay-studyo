"""0.5.21: PDF/DOCX/TXT/HTML sesi beklemez: Stüdyo işi açılınca ve kitap düzeltilince hemen yazılır (MP3/M4B seslendirme
bitince). Kütüphane'den silinen kitabın Stüdyo işi de silinir.
  docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/app:/k berzahbey/dedplay-studyo:latest python tests/test_bicim.py"""
import os, sys, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
kok = tempfile.mkdtemp()
os.environ["DATA_DIR"] = os.path.join(kok, "k")
os.environ["STUDYO_DATA_DIR"] = os.path.join(kok, "s")
os.environ["DEDPLAY_DIR"] = os.path.join(kok, "dedplay")
os.environ["OUTPUT_DIR"] = os.path.join(kok, "dedplay", ".seslendirme")
os.environ["CIKTI_DIR"] = os.path.join(kok, "dedplay", "EPUB")
for d in ("s", "dedplay/.seslendirme"):
    os.makedirs(os.path.join(kok, d), exist_ok=True)
from app import birlesik  # noqa: F401
from app import db, worker
from app import main as studyo
from kutuphane import depo
from kutuphane import main as kmain

B = []


def ok(k, ad):
    B.append(bool(k))
    print(("GECTI " if k else "KALDI ") + ad)


def bekle(kosul, sure=60):
    son = time.time() + sure
    while time.time() < son:
        if kosul():
            return True
        time.sleep(0.2)
    return False


db.init()
D = os.environ["DEDPLAY_DIR"]
ad = "Eser - Yazar"
txt = os.path.join(D, "TXT", "Türkçe", ad + ".txt")
p = [{"name": "Parca_001", "tr": "Başlık\nİlk metin.", "osm": "باشلق\nایلك متن"}]
jid = studyo.kutuphane_isi(ad, "اثر", p)
ok(db.get(jid)["ok_state"] in (None, "", "bekliyor") and db.get(jid)["status"] == "active", "iş açıldı, seslendirme sırada")
ok(bekle(lambda: all(os.path.isfile(os.path.join(D, b, dk, f"{ad}.{u}"))
                     for b, u in (("PDF", "pdf"), ("DOCX", "docx"), ("TXT", "txt"), ("HTML", "html"))
                     for dk in ("Türkçe", "Osmanlıca", "Türkçe-Osmanlıca"))),
   "PDF/DOCX/TXT/HTML seslendirmeyi beklemeden yazıldı (3 dil)")
ok("İlk metin" in open(txt, encoding="utf-8").read(), "TXT'de kitabın metni var")
ok(not os.path.isdir(os.path.join(D, "MP3")) and not os.path.isdir(os.path.join(D, "M4B")), "MP3/M4B henüz yok (ses bitmedi)")
ok(not [f for r, _, fs in os.walk(D) for f in fs if f.endswith(".tmp")], "yarım (.tmp) dosya kalmadı")

# seslendirme sürerken Türkçe düzeltildi: biçimler hemen yenilenir
db.update(jid, ok_state="calisiyor")
p2 = [dict(p[0], tr="Başlık\nDüzeltilmiş metin.")]
studyo.kutuphane_guncelle(jid, "اثر", p2)
ok(bekle(lambda: "Düzeltilmiş metin" in open(txt, encoding="utf-8").read()), "düzeltmeden sonra TXT hemen yenilendi")
ok(db.get(jid)["yenile"] == 1, "ses, şu anki seslendirme bitince yeniden üretilecek")
# seslendirme sürerken yalnız Osmanlıca değişti
osm_txt = os.path.join(D, "TXT", "Osmanlıca", ad + ".txt")
p3 = [dict(p2[0], osm="باشلق\nیڭی متن")]
studyo.kutuphane_guncelle(jid, "اثر", p3)
ok(bekle(lambda: "یڭی متن" in open(osm_txt, encoding="utf-8").read()), "yalnız Osmanlıca değişti: biçimler hemen yenilendi")

# Kütüphane'den kitap silinince Stüdyo işi de silinir
depo.durum_yaz("kitap1", asama="hazır", studyo={"is": jid})
r = kmain.kitap_sil("kitap1")
ok(r.get("durum") == "silindi" and not os.path.isdir(depo.klasor("kitap1")), "Kütüphane kitabı silindi")
ok(db.get(jid) is None, "kitabın Stüdyo işi (seslendirme sırası) da silindi")
ok(os.path.isfile(txt), "dedplay klasöründeki çıktılar kaldı")
# Stüdyo işi olmayan kitap da silinir
depo.durum_yaz("kitap2", asama="sırada")
ok(kmain.kitap_sil("kitap2").get("durum") == "silindi", "Stüdyo işi olmayan kitap silindi")

print("SONUC: HEPSI GECTI" if all(B) else f"SONUC: {B.count(False)} TEST KALDI")
os._exit(0 if all(B) else 1)
