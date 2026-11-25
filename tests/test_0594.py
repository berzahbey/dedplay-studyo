"""0.5.94 (25 Kasım 2026): OCR bozuğu kelime köken sorusuna gönderilmez (çevirici Tur YZ5 ölçümü: bulri -> bulur بلور gibi uydurma kökler).
Çalıştırma: docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/app:/k berzahbey/dedplay-studyo:latest python tests/test_0594.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kutuphane.koken import ocr_bozuk
B = []
def ok(w, b):
    c = ocr_bozuk(w); B.append(bool(c) == b); print(("GECTI " if bool(c) == b else "KALDI ") + f"{w} -> {c}")
for w in ["tYstadı", "siJah", "MilPin", "çdnkü", "zümrcdcndirler", "gcrçekleşmemesinden", "şckilılc", "çcvede",
          "Kitclbü", "öaevlcrini", "Müsntd", "dı5ında"]:
    ok(w, True)
for w in ["Türkçe", "Türkische", "Schmölders", "Schopenhauer", "Nakşibendîliğin", "kahramanları", "el-Mülûk", "Kur'ân'ın", "İbn-i Sînâ",
          "Hıfzı", "Batha", "dergâh", "Dârakutnî", "üstlenmek", "çiftçilik", "Lûtfda", "Zarflıoğlu", "Fârâbî'nin", "HALDUN"]:
    ok(w, False)
print("SONUC:", "HEPSI GECTI" if all(B) else f"{B.count(False)} KALDI")
sys.exit(0 if all(B) else 1)
