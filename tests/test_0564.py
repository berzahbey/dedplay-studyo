"""0.5.64: seslendirmeye gönderirken parçalar veritabanı satırı (sqlite3.Row) olarak gelir; parts_to_epub onlarla da çalışır
(0.5.63: "'sqlite3.Row' object has no attribute 'get'" seslendirme hatası)."""
import os, sys, tempfile
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="t0564-")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import db  # noqa: E402
from app.worker import parts_to_epub  # noqa: E402
db.init()
jid = db.create_job("Kitap.epub", "tr")
db.insert_parts_hazir(jid, [("Parca_001", "Başlık\nBir cümle.", ""), ("Parca_002", "İkinci\nBaşka cümle.", "")])
ana = [p for p in db.all_parts(jid) if p["name"].startswith("Parca_")]     # step_okuma ile aynı
try:
    parts_to_epub(ana, "Kitap - Yazar", os.path.join(os.environ["DATA_DIR"], "k.epub"))
    print("test_0564: hepsi geçti")
except Exception as e:
    print(f"HATA: {type(e).__name__}: {e}")
    sys.exit(1)
