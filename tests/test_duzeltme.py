"""Tur 2/C + tur 3: düzeltmeden sonra Stüdyo işi yenilenir (yalnız değişen bölümün sesi; art arda düzeltmede bekleme;
seslendirme sürüyorsa bitince bir kez daha), çıktılar /dedplay altında biçim/dil/kitap adı düzeninde.
  docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/app:/k berzahbey/dedplay-studyo:latest python tests/test_duzeltme.py"""
import glob, os, sys, tempfile, time, zipfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
kok = tempfile.mkdtemp()
os.environ["DATA_DIR"] = os.path.join(kok, "k")
os.environ["STUDYO_DATA_DIR"] = os.path.join(kok, "s")
os.environ["OUTPUT_DIR"] = os.path.join(kok, "okuma-ses")       # Kitap Okuma'nın ses klasörü (taklit)
os.environ["DEDPLAY_DIR"] = os.path.join(kok, "dedplay")
for d in ("s", "okuma-ses", "dedplay"):
    os.makedirs(os.path.join(kok, d), exist_ok=True)
from app import birlesik  # noqa: F401
from app import clients, db, worker
from app import main as studyo

B = []


def ok(k, ad):
    B.append(bool(k))
    print(("GECTI " if k else "KALDI ") + ad)


db.init()
parcalar = [{"name": "Parca_001", "tr": "Birinci Bölüm\nİlk paragraf.", "osm": "برنجی بولوم\nایلك"},
            {"name": "Parca_002", "tr": "İkinci Bölüm\nİkinci paragraf.", "osm": "ایكنجی بولوم\nایكنجی"}]
jid = studyo.kutuphane_isi("Eser Adı - Yazar", "اثر", parcalar)
j = db.get(jid)
ok(j["title"] == "Eser Adı - Yazar" and j["book_name"] == "Eser Adı - Yazar", "kitap adı yazarla birlikte (EPUB'la aynı)")
z = zipfile.ZipFile(db.source_path(jid, "Eser Adı - Yazar.epub"))
ok(any("<h1>Birinci Bölüm</h1>" in z.read(n).decode() for n in z.namelist() if n.endswith(".xhtml")),
   "seslendirme EPUB'unda bölüm başlığı <h1> (M4B bölüm adı)")

# seslendirme bitti (Kitap Okuma'nın çıktısı taklit) -> çıktılar yeni düzende
ses = os.path.join(kok, "okuma-ses", "Eser Adı - Yazar")
os.makedirs(ses)
for n in ("Bolum_001_Birinci_Bölüm", "Bolum_002_İkinci_Bölüm"):
    open(os.path.join(ses, n + ".mp3"), "wb").write(b"ID3")
open(os.path.join(ses, "Eser Adı - Yazar.m4b"), "wb").write(b"m4b")
worker._tag_mp3 = lambda *a, **k: None
db.update(jid, ok_state="bitti", stage="done", status="done")
worker.save_outputs(jid)
dd = os.environ["DEDPLAY_DIR"]
beklenen = [f"{b}/{d}/Eser Adı - Yazar.{e}" for b, e in (("PDF", "pdf"), ("DOCX", "docx"), ("TXT", "txt"), ("HTML", "html"))
            for d in ("Türkçe", "Osmanlıca", "Türkçe-Osmanlıca")]
eksik = [p for p in beklenen if not os.path.exists(os.path.join(dd, p))]
ok(not eksik, f"PDF/DOCX/TXT/HTML biçim/dil/kitap adı düzeninde {eksik[:3]}")
ok(sorted(os.listdir(os.path.join(dd, "MP3", "Eser Adı - Yazar"))) == ["Eser Adı - Yazar - 001.mp3", "Eser Adı - Yazar - 002.mp3"],
   "MP3/Kitap adı/Kitap adı - 001.mp3")
ok(os.path.exists(os.path.join(dd, "M4B", "Eser Adı - Yazar.m4b")), "M4B/Kitap adı.m4b")
ok(len(glob.glob(os.path.join(ses, "*.mp3"))) == 2, "Kitap Okuma'nın kendi ses dosyaları yerinde (düzeltmede yeniden kullanılır)")
ok(not os.path.exists(os.path.join(dd, "EPUB")), "EPUB'ları Stüdyo yazmaz (Kütüphane yazar)")

# düzeltme: parçalar yenilenir, iş yeniden seslendirmeye gider (bekleme süresinden sonra)
yeni = [dict(parcalar[0]), dict(parcalar[1], tr="İkinci Bölüm\nDüzeltilmiş paragraf.")]
ok(studyo.kutuphane_guncelle(jid, "اثر", yeni), "kutuphane_guncelle çalıştı")
j = db.get(jid)
ok(j["status"] == "active" and j["ok_state"] == "bekliyor" and j["degisti"],
   "düzeltilen kitap yeniden seslendirme sırasına girdi")
ok([p["tr"] for p in db.all_parts(jid)][1].endswith("Düzeltilmiş paragraf."), "Stüdyo parçaları yeni metinle")
gonderilen = []
clients.ok_submit = lambda path, ad: gonderilen.append(ad)
w = worker.Worker()
w.step_okuma(db.get(jid), "")
ok(gonderilen == [], "art arda düzeltme: 2 dakika dolmadan gönderilmez")
db.update(jid, degisti=time.time() - 999)
w.step_okuma(db.get(jid), "")
ok(gonderilen == ["Eser Adı - Yazar.epub"] and db.get(jid)["ok_state"] == "sirada", "bekleme bitince Kitap Okuma'ya gitti")

# Kitap Okuma işlerken eski M4B "bitti" sayılmaz
clients.ok_status = lambda ad: ("processing", 1, 2)
clients.ok_library_entry = lambda ad: {"title": ad, "m4b": "/x.m4b"}
w.step_okuma(db.get(jid), "")
ok(db.get(jid)["ok_state"] == "calisiyor", "işlenirken eski M4B bitti sayılmaz")
# seslendirme sürerken yeni düzeltme -> bitince bir kez daha
studyo.kutuphane_guncelle(jid, "اثر", yeni)
ok(db.get(jid)["yenile"] == 1 and db.get(jid)["ok_state"] == "calisiyor", "seslendirme sürerken düzeltme: işaretlendi")
clients.ok_status = lambda ad: ("completed", 2, 2)
w.step_okuma(db.get(jid), "")
ok(db.get(jid)["ok_state"] == "bekliyor" and db.get(jid)["yenile"] == 0, "bitince yeniden gönderilmek üzere sıraya girdi")

# Kütüphane: düzeltmeden sonraki EPUB işi var olan Stüdyo işini günceller
from kutuphane import cikti, depo
cagrilar = []
cikti.studyo_isi_var = lambda i: True
cikti.studyoyu_guncelle = lambda kit, i: cagrilar.append(i) or {"is": i}
depo.K.yukle = lambda yol: {"kunye": {"asil_dil": "tr", "baslik": {"tr": "x"}}, "bloklar": [{"metin": {"tr": "x"}}]}
depo.K.diller = lambda kit: ["tr"]
depo.durum_oku = lambda kid: {"studyo": {"is": 7}}
depo.durum_yaz = lambda kid, **k: None
depo._studyoya_zincirle("kitap", guncelle=True, yalniz_var_olan=True)
ok(cagrilar == [7], "okuma ekranında düzeltme -> Stüdyo işi güncellendi")
depo.durum_oku = lambda kid: {}
yeni_is = []
cikti.studyoya_gonder = lambda kit: yeni_is.append(1)
depo._studyoya_zincirle("kitap", guncelle=True, yalniz_var_olan=True)
ok(yeni_is == [], "Stüdyo işi olmayan kitap düzeltmede yeni iş açmaz")

print("SONUC:", "HEPSI GECTI" if all(B) else f"{B.count(False)} TEST KALDI")
sys.exit(0 if all(B) else 1)
