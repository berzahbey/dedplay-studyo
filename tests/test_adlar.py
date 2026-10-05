"""Tur 2/A-ek: ekran adları tek uygulamaya göre (eski "Kütüphane"/"Studio" adları kalmadı).
  docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/app:/k berzahbey/dedplay-studyo:latest python tests/test_adlar.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kutuphane import main as kmain

BASARI = []


def ok(kosul, ad):
    BASARI.append(bool(kosul))
    print(("GECTI " if kosul else "KALDI ") + ad)


k = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ana = open(os.path.join(k, "kutuphane/static/index.html"), encoding="utf-8").read()
oku = open(os.path.join(k, "kutuphane/static/oku.html"), encoding="utf-8").read()
eski = open(os.path.join(k, "app/static/index.html"), encoding="utf-8").read()
ok("<title>Dedplay Stüdyo</title>" in ana and "Dedplay Kütüphane" not in ana, "Ana ekranın adı Dedplay Stüdyo")
ok("Stüdyo'ya gönder" not in ana and "Stüdyo'da aç" not in ana, "Ana ekranda Stüdyo ayrı bir yer gibi anılmıyor")
ok("Dedplay Kütüphane" not in oku and "← Kitaplar" in oku, "Okuma ekranında eski ad yok")
ok("Dedplay Studio" not in eski and 'id="drop" style="display:none"' in eski, "Eski ekran yalnız seslendirme durumu (ekleme formu gizli)")
ok("Stüdyo" not in kmain.SERVISLER and any("Kitap Okuma" in a for a in kmain.SERVISLER), "Durum satırında Stüdyo değil Kitap Okuma")

ok('id="metinBtn"' in ana and "/api/kitaplar/metin" in ana, "Ana ekranda metin yapıştırma var")

print("SONUC:", "HEPSI GECTI" if all(BASARI) else f"{BASARI.count(False)} TEST KALDI")
sys.exit(0 if all(BASARI) else 1)
