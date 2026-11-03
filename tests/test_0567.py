"""0.5.67: Kütüphane: işlenmiş kitap "Kitaplarım"dan Kütüphane'ye kaldırılır (silinmez), geri alınır; yeniden verilen
kitap listeye döner; 0.5.66 uyarısı "Kütüphane'de zaten var" der. (fastapi gerekir: sunucuda konteyner içinde değil, bulutta.)"""
import json, os, sys, tempfile
kok = tempfile.mkdtemp(prefix="t0567-")
os.environ.update(DATA_DIR=os.path.join(kok, "data"), DEDPLAY_DIR=os.path.join(kok, "dedplay"),
                  CIKTI_DIR=os.path.join(kok, "dedplay", "EPUB"), KAYNAK_DIR=os.path.join(kok, "kaynak"))
os.makedirs(os.path.join(kok, "kaynak"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient  # noqa: E402
from kutuphane import depo, kaynak, main as M  # noqa: E402

c = TestClient(M.app)
hata = []
yol = os.path.join(depo.VERI, "yuklenen", "Gazzali - Filozoflarin Tutarsizligi.pdf")
kid = kaynak.kimlik_uret(yol)
depo.durum_yaz(kid, baslik="Filozofların Tutarsızlığı", yazar="Gazzâlî", asama="hazır", kaynak_kimlik=yol,
               epublar=[{"dosya": "a.epub", "diller": ["tr"]}], eklendi=1)
depo.durum_yaz("Yarim-abc123", baslik="Yarım", asama="Osmanlıca sırada", eklendi=2)

r = c.post(f"/api/kitaplar/{kid}/kutuphane", json={"kutuphanede": True})
if r.status_code != 200: hata.append(f"kaldırılamadı: {r.status_code} {r.text}")
if c.post("/api/kitaplar/Yarim-abc123/kutuphane", json={}).status_code != 409: hata.append("işlenmemiş kitap kaldırıldı")
if c.post("/api/kitaplar/yok-abc123/kutuphane", json={}).status_code != 404: hata.append("olmayan kitap: 404 değil")
liste = {k["kimlik"]: k for k in c.get("/api/kitaplar").json()}
if not liste.get(kid, {}).get("kutuphanede"): hata.append("listede kutuphanede yok")
if liste.get("Yarim-abc123", {}).get("kutuphanede"): hata.append("öteki kitap da kütüphanede")
if not os.path.exists(depo.kitap_yolu(kid).replace("kitap.json", "durum.json")): hata.append("kitap silinmiş")
v = c.get("/api/arsiv-kontrol", params={"ad": "Gazzali - Filozoflarin Tutarsizligi.pdf"}).json()
if v.get("nerede") != "kutuphane" or "Kütüphane'de zaten var" not in v.get("mesaj", ""): hata.append(f"uyarı: {v}")
c.post(f"/api/kitaplar/{kid}/kutuphane", json={"kutuphanede": False})
if depo.durum_oku(kid).get("kutuphanede"): hata.append("geri alınamadı")
c.post(f"/api/kitaplar/{kid}/kutuphane", json={"kutuphanede": True})
M._dosya_isi(yol, "Gazzali - Filozoflarin Tutarsizligi.pdf")   # yeniden verildi -> listeye döner
if depo.durum_oku(kid).get("kutuphanede"): hata.append("yeniden verilen kitap Kütüphane'de kaldı")
html = c.get("/").text
for p in ('id="t-kutuphane"', 'id="kutuphane"', "topluKutuphane", "Kütüphane'ye kaldır"):
    if p not in html: hata.append("arayüzde yok: " + p)

print("\n".join(hata) or "test_0567: hepsi geçti")
sys.exit(1 if hata else 0)
