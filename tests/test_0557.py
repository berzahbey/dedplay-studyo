"""0.5.57: Gemini zaman aşımı/bağlantı hatası/5xx denemeyi bitirmez; 10 denemede cevap yoksa GeciciHata ve kitap denetimsiz
sürmez: denetim "bekliyor" olur, bir süre sonra yeniden sıraya girer (en çok 8 kez; sonra eskisi gibi hata ve devam)."""
import json, os, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
KOK = tempfile.mkdtemp(prefix="t0557-"); os.environ["DATA_DIR"] = KOK; os.environ["STUDYO_DENETIM_BEKLE"] = "3600"; os.environ["STUDYO_GEMINI_RPM"] = "10000"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KIP = {"k": "kopuk"}; SAY = {"post": 0}


class S(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _yaz(self, kod, v):
        b = json.dumps(v).encode(); self.send_response(kod); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        self._yaz(200, {"models": [{"name": "models/gemini-9.5-flash-lite", "supportedGenerationMethods": ["generateContent"]}]})
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"])); SAY["post"] += 1
        if KIP["k"] == "kopuk":
            self.connection.close(); return          # bağlantı koptu (requests.ConnectionError)
        if KIP["k"] == "503":
            return self._yaz(503, {"error": {"code": 503}})
        if KIP["k"] == "bir_kopuk" and SAY["post"] == 1:
            self.connection.close(); return
        self._yaz(200, {"candidates": [{"content": {"parts": [{"text": "[]"}]}}]})


s = HTTPServer(("127.0.0.1", 0), S); threading.Thread(target=s.serve_forever, daemon=True).start()
os.environ["STUDYO_GEMINI_URL"] = f"http://127.0.0.1:{s.server_port}/v1beta"
from kutuphane import yz, depo  # noqa: E402
yz.time.sleep = lambda x: None
yz.ayar_yaz(anahtar="AIzaTEST")
hata = []
KIP["k"] = "bir_kopuk"; SAY["post"] = 0
try:
    _, veren = yz.Gemini().sor("s", "k")
    if SAY["post"] != 2:
        hata.append(f"kopuk bağlantıdan sonra yeniden denenmedi ({SAY['post']})")
except Exception as e:
    hata.append(f"tek kopuk bağlantı hata verdi: {e}")
for k in ("kopuk", "503"):
    KIP["k"] = k; SAY["post"] = 0
    try:
        yz.Gemini().sor("s", "k"); hata.append(f"{k}: hata yok")
    except yz.GeciciHata:
        if SAY["post"] != 10:
            hata.append(f"{k}: {SAY['post']} deneme")
    except Exception as e:
        hata.append(f"{k}: yanlış hata {type(e).__name__}")
# depo: GeciciHata -> bekliyor, sıradaki iş yok (Osmanlıca'ya geçmez)
KIP["k"] = "kopuk"
kid = "Deneme-d0557"; txt = os.path.join(KOK, "Deneme.txt")
open(txt, "w", encoding="utf-8").write("BİRİNCİ BÖLÜM\n\nKimine göre (B. Lewis, The Middle East and the West) değil. Bu kitapx güzeldir. Bu kitap okunur.")
depo.durum_yaz(kid, kaynak_kimlik=txt, baslik="Deneme"); depo._dosya_ekle(kid, txt)
zaman = []
depo.threading.Timer = lambda t, f: type("T", (), {"start": lambda self: zaman.append(t)})()
sonra = depo._denetim(kid)
d = depo.durum_oku(kid).get("denetim") or {}
if sonra is not None or d.get("durum") != "bekliyor" or d.get("gecici") != 1 or zaman != [3600]:
    hata.append(f"bekleme yok: {sonra} {d} {zaman}")
depo.durum_yaz(kid, denetim={"durum": "bekliyor", "gecici": 8})
sonra = depo._denetim(kid)
if sonra != ("osmanlica", kid) or (depo.durum_oku(kid).get("denetim") or {}).get("durum") != "hata":
    hata.append(f"8 denemeden sonra devam etmedi: {sonra}")
print("test_0557:", "HEPSI GECTI" if not hata else "KALDI: " + "; ".join(hata))
sys.exit(1 if hata else 0)
