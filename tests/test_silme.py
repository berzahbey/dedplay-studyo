"""0.5.19 gerileme testi: sırada bekleyen kitap silinebilir; işi çalışan kitabın işi durur, kitap ardından silinir;
silinen kitap yeniden eklenince normal işlenir. Gerçek OCR çalıştırmaz (işler taklit)."""
import os, sys, tempfile, time, types, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
GECICI = tempfile.mkdtemp()
os.environ["DATA_DIR"] = GECICI
os.environ["OCR_ONBELLEK"] = os.path.join(GECICI, "ocr_onbellek")
from kutuphane import depo

kalan = []


def dene(ad, kosul):
    print(("GECTI " if kosul else "KALDI ") + ad)
    if not kosul:
        kalan.append(ad)


calisti, epub = [], []


def sahte_dosya(kid, yol):
    calisti.append(kid)
    for k in range(30):          # OCR taklidi: 0,1 sn'de bir ilerleme bildirimi
        depo.durum_asama(kid, f"OCR (Surya): sayfa {k + 1}/30")
        time.sleep(0.1)


def sahte_epub(kid):
    epub.append(kid)
    depo.durum_yaz(kid, asama="hazır", epublar=[{"dosya": "x.epub"}])


depo.kaynak.ocr_gerekir = lambda yol: True
depo._dosya_ekle = sahte_dosya
depo.epub_uret = sahte_epub
depo.K = types.SimpleNamespace(yukle=lambda p: {"kunye": {"asil_dil": "xx"}})
depo._osmanlica = lambda kid, zorla=False: None
# yeniden başlatma: silinmek istenirken kapanmış kitap açılışta silinir
depo.durum_yaz("eski", asama="OCR sırasında", silinecek=True, is_turu="dosya", is_arg="/x/eski.pdf")
depo.baslat()
time.sleep(0.3)
dene("Açılışta 'silinecek' işaretli kitap silindi", not os.path.isdir(depo.klasor("eski")) and "eski" not in calisti)

depo.is_ekle("dosya", "a", "/x/a.pdf", tur="dosya")
depo.is_ekle("dosya", "b", "/x/b.pdf", tur="dosya")
depo.is_ekle("dosya", "c", "/x/c.pdf", tur="dosya")
time.sleep(0.6)
dene("a çalışıyor, b ve c sırada", depo.durum_oku("a").get("asama", "").startswith("OCR (Surya)")
     and depo.durum_oku("c").get("asama") == "OCR sırasında")
dene("Sıradaki kitap hemen silinir", depo.sil_iste("c") == "silindi" and not os.path.isdir(depo.klasor("c")))
dene("Çalışan kitap: 'durduruluyor'", depo.sil_iste("a") == "durduruluyor" and os.path.isdir(depo.klasor("a")))
time.sleep(1.0)
dene("Çalışan kitabın işi durdu ve kitap silindi", not os.path.isdir(depo.klasor("a")) and "a" not in epub)
dene("Durdurulan işten sonra sıradaki kitap (b) başladı", "b" in calisti)
time.sleep(3.5)
dene("b normal bitti", depo.durum_oku("b").get("asama") == "hazır" and "b" in epub)
dene("Silinen c'nin kuyruktaki işi atlandı (hiç çalışmadı, klasörü yeniden oluşmadı)",
     "c" not in calisti and not os.path.isdir(depo.klasor("c")))
# aynı kitap yeniden eklenince normal işlenir
depo.is_ekle("dosya", "c", "/x/c.pdf", tur="dosya")
time.sleep(3.8)
dene("Silinen kitap yeniden eklenince işlendi", "c" in calisti and depo.durum_oku("c").get("asama") == "hazır")
dene("Hazır kitap silinir", depo.sil_iste("b") == "silindi" and not os.path.isdir(depo.klasor("b")))
dene("İşçiler hâlâ çalışıyor", all(t.is_alive() for t in threading.enumerate() if t.name.startswith("kutuphane-")))

print("SONUC: HEPSI GECTI" if not kalan else f"SONUC: {len(kalan)} TEST KALDI")
os._exit(1 if kalan else 0)
