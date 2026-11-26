"""0.5.95 (26 Kasım 2026, Zahir: "iPhone'da Stüdyo'da kitap okurken ekran kapanıyor"): okuma ekranlarında (oku.html, raf.html) ekran açık
tutulur: Screen Wake Lock + görünmez sessiz döngülü video (iOS ana ekran uygulaması ve eski iOS için). Video geçerli bir MP4 olmalı.
Çalıştırma: docker run --rm -v "$PWD":/k -w /k berzahbey/dedplay-studyo:latest python tests/test_0595.py"""
import base64, os, re, sys
kok = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kutuphane", "static")
B = []
for ad in ("oku.html", "raf.html"):
    s = open(os.path.join(kok, ad), encoding="utf-8").read()
    ok = ('navigator.wakeLock.request("screen")' in s and 'id="uyanik-video"' in s and "playsinline" in s and "muted" in s
          and "visibilitychange" in s and s.index('id="uyanik-video"') < s.index("</body>"))
    m = re.search(r'src="data:video/mp4;base64,([A-Za-z0-9+/=]+)"', s)
    mp4 = base64.b64decode(m.group(1)) if m else b""
    ok = ok and mp4[4:8] == b"ftyp" and len(mp4) > 500
    B.append(ok); print(("GECTI " if ok else "KALDI ") + ad)
print("SONUC:", "HEPSI GECTI" if all(B) else f"{B.count(False)} KALDI")
sys.exit(0 if all(B) else 1)
