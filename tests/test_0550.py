"""0.5.50: kitap paketi (Mac Hazırlık için). Kitaba dokunmadan zip üretir: kaynak dosya, Surya OCR önbelleği, kitap.json.
  python tests/test_0550.py   (DATA_DIR geçici klasöre çevrilir; httpx/TestClient gerekmez)"""
import json
import os
import sys
import tempfile
import zipfile

KOK = tempfile.mkdtemp(prefix="t0550-")
os.environ["DATA_DIR"] = KOK
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException  # noqa: E402

from kutuphane import depo, kaynak  # noqa: E402
from kutuphane import main as M  # noqa: E402

hata = 0


def kontrol(ad, kosul):
    global hata
    print(("TAMAM " if kosul else "HATA  ") + ad)
    hata += not kosul


kid = "Deneme-Kitap-abc123"
pdf = os.path.join(KOK, "Deneme Kitap.pdf")
open(pdf, "wb").write(b"%PDF-1.4 deneme icerik")
depo.durum_yaz(kid, kaynak_kimlik=pdf, baslik="Deneme Kitap", yazar="Yazar")
json.dump({"surum": 1, "bloklar": []}, open(os.path.join(depo.klasor(kid), "kitap.json"), "w"))
onb = kaynak._ocr_onbellek_klasoru(pdf)
os.makedirs(onb)
for i in (1, 2):
    json.dump({"anahtar": kaynak._surya_anahtari(), "sayfa": i, "satirlar": [["satır", [0, 0, 1, 1]]]},
              open(os.path.join(onb, f"s{i:04d}.json"), "w"))
once = sorted(os.listdir(depo.klasor(kid)))
c = M.paket(kid)
with zipfile.ZipFile(c.path) as z:
    adlar = sorted(z.namelist())
    bilgi = json.loads(z.read("paket.json"))
    kontrol("kaynak dosya pakette ve aynı", z.read("kaynak/Deneme Kitap.pdf") == open(pdf, "rb").read())
kontrol("OCR önbelleği pakette", f"ocr_onbellek/{os.path.basename(onb)}/s0001.json" in adlar and
        f"ocr_onbellek/{os.path.basename(onb)}/s0002.json" in adlar)
kontrol("kitap.json pakette", "kitap.json" in adlar)
kontrol("paket bilgisi", bilgi["kimlik"] == kid and bilgi["ocr_dosya"] == 2 and bilgi["studyo"] == M.SURUM
        and bilgi["ocr_klasoru"] == os.path.basename(onb))
kontrol("kitap klasörüne dokunulmadı", sorted(os.listdir(depo.klasor(kid))) == once)
try:
    M.paket("Olmayan-kitap-000000")
    kontrol("olmayan kitap 404", False)
except HTTPException as e:
    kontrol("olmayan kitap 404", e.status_code == 404)
depo.durum_yaz(kid, kaynak_kimlik="0000.Openiti-kimligi")
try:
    M.paket(kid)
    kontrol("kaynak dosyası olmayan kitap 404", False)
except HTTPException as e:
    kontrol("kaynak dosyası olmayan kitap 404", e.status_code == 404)
print("SONUÇ:", "HATA" if hata else "TAMAM")
sys.exit(1 if hata else 0)
