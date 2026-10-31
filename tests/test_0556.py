"""0.5.56: Google'ın kapattığı Gemini modeli (404 "no longer available") kalıcı olarak atlanır, sıradaki modele geçilir;
hepsi doluysa GunlukSinir (denetim hata vermez, ertesi gün sürer)."""
import json, os, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="t0556-")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KAPALI, DOLU, ISTEK = {"gemini-9.1-flash-lite"}, set(), []


class S(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _yaz(self, kod, v):
        b = json.dumps(v).encode(); self.send_response(kod); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        self._yaz(200, {"models": [{"name": f"models/gemini-{v}-flash-lite", "supportedGenerationMethods": ["generateContent"]}
                                   for v in ("9.5", "9.1", "8.0")]})
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        m = self.path.split("/models/")[1].split(":")[0]; ISTEK.append(m)
        if m in KAPALI:
            return self._yaz(404, {"error": {"code": 404, "message": f"This model models/{m} is no longer available to new users."}})
        if m in DOLU:
            return self._yaz(429, {"error": {"details": [{"@type": "QuotaFailure", "violations": [{"quotaId": "PerDay"}]}]}})
        self._yaz(200, {"candidates": [{"content": {"parts": [{"text": "[]"}]}}]})


s = HTTPServer(("127.0.0.1", 0), S); threading.Thread(target=s.serve_forever, daemon=True).start()
os.environ["STUDYO_GEMINI_URL"] = f"http://127.0.0.1:{s.server_port}/v1beta"
from kutuphane import yz  # noqa: E402
yz.ayar_yaz(anahtar="AIzaTEST")
hata = []
DOLU.add("gemini-9.5-flash-lite")
_, veren = yz.Gemini().sor("s", "k")
if veren != "gemini-8.0-flash-lite":
    hata.append(f"kapalı model atlanmadı: {veren}")
if yz.ayarlar().get("kullanilamaz") != ["gemini-9.1-flash-lite"]:
    hata.append(f"kalıcı kayıt yok: {yz.ayarlar().get('kullanilamaz')}")
if "gemini-9.1-flash-lite" in yz.modeller():
    hata.append("kapalı model listede")
ISTEK.clear()
yz.Gemini().sor("s", "k")
if "gemini-9.1-flash-lite" in ISTEK:
    hata.append("kapalı model yeniden soruldu")
DOLU.add("gemini-8.0-flash-lite")
try:
    yz.Gemini().sor("s", "k"); hata.append("hepsi doluyken GunlukSinir yok")
except yz.GunlukSinir:
    pass
print("test_0556:", "HEPSI GECTI" if not hata else "KALDI: " + "; ".join(hata))
sys.exit(1 if hata else 0)
