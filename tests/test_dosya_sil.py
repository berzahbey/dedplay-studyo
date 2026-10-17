"""0.5.39: kitap silinirken "Dosyalarını da sil": kitabın /dedplay'deki EPUB, PDF, DOCX, TXT, HTML, MP3, M4B ve seslendirme
klasörü silinir; adı benzeyen başka kitabın dosyalarına dokunulmaz; seçilmezse dosyalar kalır (eski davranış).
  docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/app:/k berzahbey/dedplay-studyo:latest python tests/test_dosya_sil.py"""
import json, os, sys, tempfile, time
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


def yaz(yol, icerik=b"x"):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "wb") as f:
        f.write(icerik)
    return yol


db.init()
D = os.environ["DEDPLAY_DIR"]
E = os.environ["CIKTI_DIR"]
S = os.environ["OUTPUT_DIR"]
A, BK = "Eser - Yazar", "Eser - Yazar Ek"   # B'nin adı A ile başlıyor: A silinirken B'ye dokunulmamalı
p = [{"name": "Parca_001", "tr": "Başlık\nİlk metin.", "osm": "باشلق\nایلك متن"}]
ja = studyo.kutuphane_isi(A, "اثر", p)
jb = studyo.kutuphane_isi(BK, "اثر", p)
BICIM = [(b, dk, u) for b, u in (("PDF", "pdf"), ("DOCX", "docx"), ("TXT", "txt"), ("HTML", "html"))
         for dk in ("Türkçe", "Osmanlıca", "Türkçe-Osmanlıca")]
ok(bekle(lambda: all(os.path.isfile(os.path.join(D, b, dk, f"{ad}.{u}")) for ad in (A, BK) for b, dk, u in BICIM)),
   "iki kitabın PDF/DOCX/TXT/HTML'i yazıldı")
time.sleep(1)
# ses ve EPUB dosyaları (Kitap Okuma ve Kütüphane taklidi)
for ad in (A, BK):
    yaz(os.path.join(S, ad, "Parca_001.mp3"))
    yaz(os.path.join(S, ad, ad + ".m4b"))
    yaz(os.path.join(D, "MP3", ad, ad + " - 001.mp3"))
    yaz(os.path.join(D, "EPUB", "Türkçe", ad + ".epub"))
    yaz(os.path.join(D, "EPUB", "Osmanlıca", ad + ".epub"))
    yaz(os.path.join(D, "EPUB", "Türkçe-Osmanlıca", ad + ".epub"))
yaz(os.path.join(D, "M4B", A + ".m4b"))
yaz(os.path.join(D, "M4B", A + " - 2.m4b"))
yaz(os.path.join(D, "M4B", BK + ".m4b"))
yaz(os.path.join(D, "M4B", A + " - Ek.m4b"))   # deseni tutmayan ad: silinmemeli
for kid, ad, jid, baslik, yazar in (("kitapa", A, ja, "Eser", "Yazar"), ("kitapb", BK, jb, "Eser", "Yazar Ek")):
    depo.durum_yaz(kid, asama="hazır", studyo={"is": jid}, cikti=[os.path.join("Türkçe", ad + ".epub")])
    with open(depo.kitap_yolu(kid), "w", encoding="utf-8") as f:
        json.dump({"kunye": {"asil_dil": "tr", "baslik": {"tr": baslik}, "yazar": {"tr": yazar}}}, f)


def a_dosyalari():
    l = [os.path.join(D, b, dk, f"{A}.{u}") for b, dk, u in BICIM]
    l += [os.path.join(D, "MP3", A), os.path.join(D, "M4B", A + ".m4b"), os.path.join(D, "M4B", A + " - 2.m4b"),
          os.path.join(S, A)] + [os.path.join(E, k, A + ".epub") for k in ("Türkçe", "Osmanlıca", "Türkçe-Osmanlıca")]
    return l


def b_dosyalari():
    l = [os.path.join(D, b, dk, f"{BK}.{u}") for b, dk, u in BICIM]
    l += [os.path.join(D, "MP3", BK), os.path.join(D, "M4B", BK + ".m4b"), os.path.join(S, BK),
          os.path.join(E, "Türkçe", BK + ".epub")]
    return l


ok(all(os.path.exists(y) for y in a_dosyalari() + b_dosyalari()), "kurulum: bütün dosyalar yerinde")
# güvenlik: adı boş/".." olan iş hiçbir şey silmez
ok(worker.ciktilari_sil({"book_name": "..", "title": ".."}) == [] and worker.ciktilari_sil({"book_name": "", "title": ""}) == []
   and os.path.isdir(os.path.join(D, "MP3")) and os.path.isdir(S), "adı '..' ya da boş olan iş hiçbir şey silmedi")

r = kmain.kitap_sil("kitapa", dosyalar=True)
ok(r.get("durum") == "silindi" and not os.path.isdir(depo.klasor("kitapa")) and db.get(ja) is None, "A silindi (kitap ve Stüdyo işi)")
kalan = [y for y in a_dosyalari() if os.path.exists(y)]
ok(not kalan, "A'nın bütün dosyaları silindi (EPUB 3 dil, PDF/DOCX/TXT/HTML 3 dil, MP3 klasörü, M4B 1 ve -2, seslendirme klasörü)" + (f" KALAN: {kalan}" if kalan else ""))
ok(r.get("silinen") == len(a_dosyalari()), f"silinen sayısı doğru ({r.get('silinen')} / {len(a_dosyalari())})")
ok(all(os.path.exists(y) for y in b_dosyalari()) and os.path.isfile(os.path.join(D, "M4B", A + " - Ek.m4b")),
   "adı benzeyen B'nin dosyalarına ve desene uymayan M4B'ye dokunulmadı")
ok(all(os.path.isdir(os.path.join(D, k)) for k in ("PDF", "MP3", "M4B", "EPUB", ".seslendirme")), "çıktı klasörlerinin kendisi duruyor")

r = kmain.kitap_sil("kitapb")
ok(r.get("durum") == "silindi" and db.get(jb) is None and r.get("silinen") == 0, "B dosyalar seçilmeden silindi (kitap ve iş)")
ok(all(os.path.exists(y) for y in b_dosyalari()), "seçilmeyince B'nin dosyaları kaldı (eski davranış)")
# Stüdyo işi olmayan kitap dosyalarıyla silinir (yalnız EPUB)
yaz(os.path.join(E, "Arapça", "Kitab - Muellif.epub"))
depo.durum_yaz("kitapc", asama="hazır", cikti=[os.path.join("Arapça", "Kitab - Muellif.epub")])
r = kmain.kitap_sil("kitapc", dosyalar=True)
ok(r.get("silinen") == 1 and not os.path.exists(os.path.join(E, "Arapça", "Kitab - Muellif.epub")),
   "Stüdyo işi olmayan (Arapça) kitabın EPUB'ı silindi (kitap.json yokken durumdaki yoldan)")
# durumdaki yol çıktı klasörünün dışını gösteriyorsa silinmez
dis = yaz(os.path.join(kok, "dis.epub"))
depo.durum_yaz("kitapd", asama="hazır", cikti=["../dis.epub"])
kmain.kitap_sil("kitapd", dosyalar=True)
ok(os.path.isfile(dis), "çıktı klasörü dışındaki dosya silinmedi")
# adres: DELETE /api/jobs/<no>?dosyalar=1
jc = studyo.kutuphane_isi("Tek - Kisi", "اثر", p)
ok(bekle(lambda: os.path.isfile(os.path.join(D, "TXT", "Türkçe", "Tek - Kisi.txt"))), "üçüncü iş yazıldı")
time.sleep(1)
r = studyo.delete_job(jc, dosyalar=True)
ok(r.get("silinen") == 12 and not os.path.exists(os.path.join(D, "TXT", "Türkçe", "Tek - Kisi.txt")), "iş adresinden dosyalarıyla silindi")

print("SONUC: HEPSI GECTI" if all(B) else f"SONUC: {B.count(False)} TEST KALDI")
os._exit(0 if all(B) else 1)
