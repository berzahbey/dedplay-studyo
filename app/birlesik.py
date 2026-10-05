"""Dedplay Stüdyo: tek uygulama (Kütüphane + Stüdyo aynı süreçte).

Taban Kütüphane'nin uygulamasıdır ("/", "/oku", "/api/kitaplar*", "/api/kaynak", "/api/katalog*", "/api/durum").
Stüdyo'nun adresleri ("/api/jobs*", "/api/browse", "/api/services", "/static") olduğu gibi eklenir; Stüdyo'nun
eski arayüzü geçiş süresince "/studyo" adresindedir. Kütüphane önce yüklenir: zeyrek onarımı (kutuphane/zeyrek_onarim.py)
Stüdyo'nun duzelt.py'sinden önce devreye girer, böylece Stüdyo'nun kendi işleri de onarımlı zeyrek'le çalışır.
"""
import os

from fastapi.responses import FileResponse

from kutuphane.main import app  # noqa: E402  (önce Kütüphane)
from app import main as studyo  # noqa: E402

_KUTUPHANENIN = {"/", "/favicon.ico", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}

_var = {(getattr(r, "path", None), tuple(sorted(getattr(r, "methods", None) or ()))) for r in app.router.routes}
for r in studyo.app.router.routes:
    yol = getattr(r, "path", None)
    if yol in _KUTUPHANENIN:
        continue
    if (yol, tuple(sorted(getattr(r, "methods", None) or ()))) in _var:
        raise RuntimeError(f"Adres çakışması: {yol}")
    app.router.routes.append(r)

for h in studyo.app.router.on_startup:
    app.router.on_startup.append(h)


@app.get("/studyo", include_in_schema=False)
def studyo_arayuzu():
    return FileResponse(os.path.join(studyo.STATIC, "index.html"))
