"""0.5.61: seste kalan artıklar (2 Kasım, 32 kitabın ses metni ölçümü). Bütün kitaplar için; yalnız ses metni değişir."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.ses import ses_metni  # noqa: E402
VAKA = [
    ('kumarı kazandım1 dersin" dedi.', 'kumarı kazandım dersin" dedi.'),          # tırnak -> 1 (İslam Tarihi)
    ("Malik b. Eyfa1,", "Malik b. Eyfa,"),
    ("- A1manlar bize dediler ki:", "- Almanlar bize dediler ki:"),               # l -> 1 (Hayat ve Hatıratım)
    ("Lokrislilere söyle1395a diklerini söyleyebilir:", "Lokrislilere söylediklerini söyleyebilir:"),  # Bekker no (Retorik)
    ("yer almaktadir.[l6l] Çünkü hac", "yer almaktadir. Çünkü hac"),            # bozuk dipnot işareti (Şâtibî)
    ("şart koşulmaması hak-[i63j kindaki delil", "şart koşulmaması hakkindaki delil"),
    ("bir yemektir (Ahm ed b. Hanbel, c. 3, s. 99, Kâmûsu'l-muhft, c. 2, s. 217).", "bir yemektir."),
    ("Mesîhâ (Mesîh’e de bkz.):", "Mesîhâ:"),
    ("Cebrâil (Rûhü’l-Emin’e de bkz.): 369, 1172, 1632, 2042, 2117, 2290", ""),    # dizin satırı (Dîvân)
    # değişmemesi gerekenler
    ("kısa söz الله أكبر okunur", None),
    ("Allah buyurur: وَتَعَاوَنُوا عَلَى الْبِرِّ وَالتَّقْوَى yani iyilikte yardımlaşın.", None),   # harekeli âyet okunur (önceki karar)
    ("(yukarıda s. 182'de sözü edilen durum bunun dışında kalır)", None),
    ("Hz. Ali 1. Halife, 1.400 sene, 16x19 cm, M.Ö. 1200 yılında, H1N1 virüsü", None),
    ("olduğu gibi- mümkün değildir.", None),
    ("1923 yılında 3 kişi, 25 Mart 1453; sayfa 12 ve 13", None),
    ("feilâtün feilâtün feilâtün feilün", None),
]
hata = []
for girdi, bekle in VAKA:
    cikti = ses_metni(girdi)
    if cikti != (girdi if bekle is None else bekle):
        hata.append(f"{girdi!r}\n   -> {cikti!r}\n   beklenen {bekle if bekle is not None else girdi!r}")
# --- seslendirilmiş kitap yeni kurallarla yeniden gönderilir (yalnız değişenler)
import tempfile  # noqa: E402
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="t0561-")
from app import db, worker  # noqa: E402
from app import main as SM  # noqa: E402
db.init()
kitaplar = {}
for ad, metin in (("Degisen", "Başlık\nkumarı kazandım1 dersin dedi."), ("Ayni", "Başlık\nTemiz bir cümle.")):
    jid = db.create_job(ad + ".epub", "tr")
    db.update(jid, status="done", stage="done", ok_state="bitti", book_name=ad, title=ad)
    db.insert_parts_hazir(jid, [("Parca_001", metin, "")])
    eski = worker.ses_metni
    worker.ses_metni = lambda x: x          # eski kurallarla üretilmiş EPUB (bugünkü sunucu)
    worker.parts_to_epub([{"tr": metin}], ad, db.source_path(jid, ad + ".epub"))
    worker.ses_metni = eski
    kitaplar[ad] = jid
r = SM.ses_yenile()
if r["yenilenen"] != ["Degisen"] or r["ayni"] != 1:
    hata.append(f"ses_yenile: {r}")
j = dict(db.get(kitaplar["Degisen"]))
if (j["status"], j["ok_state"]) != ("active", "bekliyor"):
    hata.append(f"değişen kitap yeniden gönderilmiyor: {j['status']}/{j['ok_state']}")
if dict(db.get(kitaplar["Ayni"]))["status"] != "done":
    hata.append("değişmeyen kitap yeniden gönderildi")
if b"kazand\xc4\xb1m1" in b"".join(SM._epub_metni(db.source_path(kitaplar["Degisen"], "Degisen.epub"))):
    hata.append("EPUB yenilenmedi")
if SM.ses_yenile()["yenilenen"]:
    hata.append("ikinci çağrıda yine yenilendi")

print("\n".join(hata) or "test_0561: hepsi geçti")
sys.exit(1 if hata else 0)
