"""Tur 2/D: okuma ekranında yalnız Türkçe, Kaydet'ten sonra kutu kapanır, elle "Seslendirmeye gönder" düğmesi yok (seslendirme
durumu ana ekranda); metin aynıysa ses yeniden üretilmez, yalnız Osmanlıca değiştiyse yalnız biçimler yenilenir; aynı adlı
kitaplar üst üste yazılmaz; EPUB klasörü kendiliğinden açılır.
  docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/app:/k berzahbey/dedplay-studyo:latest python tests/test_2d.py"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
kok = tempfile.mkdtemp()
os.environ["DATA_DIR"] = os.path.join(kok, "k")
os.environ["STUDYO_DATA_DIR"] = os.path.join(kok, "s")
os.environ["OUTPUT_DIR"] = os.path.join(kok, "okuma-ses")
os.environ["DEDPLAY_DIR"] = os.path.join(kok, "dedplay")
os.environ["CIKTI_DIR"] = os.path.join(kok, "dedplay", "EPUB")
for d in ("s", "okuma-ses", "dedplay"):
    os.makedirs(os.path.join(kok, d), exist_ok=True)
from app import birlesik  # noqa: F401
from app import db, worker
from app import main as studyo
from kutuphane import cikti

B = []


def ok(k, ad):
    B.append(bool(k))
    print(("GECTI " if k else "KALDI ") + ad)


kod = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kutuphane", "static")
oku = open(os.path.join(kod, "oku.html"), encoding="utf-8").read()
ana = open(os.path.join(kod, "index.html"), encoding="utf-8").read()
ok('b.metin.tr != null ? ["tr"]' in oku, "okuma ekranında yalnız Türkçe düzeltilir")
ok("kutu.replaceWith(yeni); ed.remove();" in oku, "Kaydet'ten sonra düzenleme kutusu kapanır")
ok("Seslendirmeye gönder" not in ana and "sesYazisi" in ana and "/api/jobs" in ana,
   "elle gönderme düğmesi yok; seslendirme durumu ana ekranda")

db.init()
p = [{"name": "Parca_001", "tr": "Başlık\nMetin.", "osm": "باشلق\nمتن"}]
j1 = studyo.kutuphane_isi("Aynı Ad", "", p)
j2 = studyo.kutuphane_isi("Aynı Ad", "", p)
ok(db.get(j2)["book_name"] == "Aynı Ad (2)", f"aynı adlı ikinci kitap ayrı ad alır ({db.get(j2)['book_name']})")

db.update(j1, status="done", stage="done", ok_state="bitti")
ok(studyo.kutuphane_guncelle(j1, "", p) and db.get(j1)["ok_state"] == "bitti" and db.get(j1)["status"] == "done",
   "metin aynı: ses yeniden üretilmez")
kaydedilen = []
worker.save_outputs = lambda jid: kaydedilen.append(jid)
p2 = [dict(p[0], osm="باشلق\nیڭی متن")]
studyo.kutuphane_guncelle(j1, "", p2)
ok(db.get(j1)["ok_state"] == "bitti" and kaydedilen == [j1] and db.all_parts(j1)[0]["osm"].endswith("یڭی متن"),
   "yalnız Osmanlıca değişti: ses yok, biçimler yenilendi")
p3 = [dict(p2[0], tr="Başlık\nDüzeltilmiş metin.")]
studyo.kutuphane_guncelle(j1, "", p3)
ok(db.get(j1)["ok_state"] == "bekliyor" and db.get(j1)["status"] == "active", "Türkçe değişti: seslendirme yenilenir")

# EPUB klasörü kendiliğinden; aynı adlı başka kitabın EPUB'u üstüne yazılmaz
ep = os.path.join(kok, "ep"); os.makedirs(ep)
open(os.path.join(ep, "a.epub"), "wb").write(b"1")
kit = {"kunye": {"asil_dil": "tr", "baslik": {"tr": "Eser"}, "yazar": {"tr": "Yazar"}}}
y1 = cikti.ciktiya_yaz(kit, [{"dosya": "a.epub", "diller": ["tr"]}], ep)
ok(y1 == [os.path.join("Türkçe", "Eser - Yazar.epub")], f"EPUB klasörü kendiliğinden açıldı {y1}")
y1b = cikti.ciktiya_yaz(kit, [{"dosya": "a.epub", "diller": ["tr"]}], ep, y1)
ok(y1b == y1, "aynı kitabın yeniden yazımı aynı adı kullanır")
y2 = cikti.ciktiya_yaz(kit, [{"dosya": "a.epub", "diller": ["tr"]}], ep)
ok(y2 == [os.path.join("Türkçe", "Eser - Yazar (2).epub")], f"aynı adlı başka kitap (2) ile yazılır {y2}")

# dinleme: M4B audio/mp4, satır içi, Range ile parça parça
from starlette.requests import Request
os.makedirs(os.path.join(kok, "dedplay", "M4B"), exist_ok=True)
open(os.path.join(kok, "dedplay", "M4B", "Aynı Ad.m4b"), "wb").write(b"0123456789")
db.update(j1, saved="Aynı Ad")
def istek(range_=None):
    h = [(b"range", range_.encode())] if range_ else []
    return Request({"type": "http", "headers": h, "method": "GET", "path": "/"})
def govde(r):
    import asyncio
    async def topla():
        return b"".join([c async for c in r.body_iterator])
    return asyncio.run(topla())
r = studyo.dinle(j1, istek())
ok(r.status_code == 200 and r.media_type == "audio/mp4" and r.headers["accept-ranges"] == "bytes"
   and r.headers["content-disposition"].startswith("inline") and govde(r) == b"0123456789", "dinleme: audio/mp4, satır içi")
r = studyo.dinle(j1, istek("bytes=2-5"))
ok(r.status_code == 206 and r.headers["content-range"] == "bytes 2-5/10" and govde(r) == b"2345", "dinleme: ileri sarma (Range 206)")
ok(studyo.dinle_parcalar(j1) == {"parca": 1} and 'dinle?part=' in open(os.path.join(kod, "index.html"), encoding="utf-8").read(),
   "ana ekrandaki çalar yeni adresi kullanır")

print("SONUC:", "HEPSI GECTI" if all(B) else f"{B.count(False)} TEST KALDI")
sys.exit(0 if all(B) else 1)
