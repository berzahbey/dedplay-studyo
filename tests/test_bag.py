"""dedplay/MP3 ve M4B: Kitap Okuma'nın dosyalarına sabit bağlantı (ek yer kaplamaz); kaynak yenilenince çıktı da yenilenir;
çıktı silinince kaynak kalır. Gerçek seslendirme yok."""
import os, sys, tempfile, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
G = tempfile.mkdtemp()
os.environ["DEDPLAY_DIR"] = os.path.join(G, "dedplay")
os.environ["OUTPUT_DIR"] = os.path.join(G, "dedplay", ".seslendirme")
os.environ["STUDYO_DATA_DIR"] = os.path.join(G, "studyo")
os.makedirs(os.environ["DEDPLAY_DIR"])
from app import worker, export
worker.DEDPLAY_DIR = os.environ["DEDPLAY_DIR"]
worker.OUTPUT_DIR = os.environ["OUTPUT_DIR"]
export.build = lambda j, parts, fmt, variant: (b"veri", None, None)
worker._tag_mp3 = lambda *a, **k: None

kalan = []


def dene(ad, kosul):
    print(("GECTI " if kosul else "KALDI ") + ad)
    if not kosul:
        kalan.append(ad)


ad = "Kitap - Yazar"
kaynak = os.path.join(worker.OUTPUT_DIR, ad)
os.makedirs(kaynak)
for i in (1, 2):
    open(os.path.join(kaynak, f"Bolum_00{i}_Baslik.mp3"), "wb").write(b"ses%d" % i)
open(os.path.join(kaynak, ad + ".m4b"), "wb").write(b"m4b-eski")
j = {"book_name": ad}
worker.save_outputs_yeni(j, [], ad)
mp3 = os.path.join(worker.DEDPLAY_DIR, "MP3", ad, ad + " - 001.mp3")
m4b = os.path.join(worker.DEDPLAY_DIR, "M4B", ad + ".m4b")
dene("MP3 sabit bağlantı (aynı dosya)", os.path.samefile(mp3, os.path.join(kaynak, "Bolum_001_Baslik.mp3")))
dene("M4B sabit bağlantı", os.path.samefile(m4b, os.path.join(kaynak, ad + ".m4b")))
dene("Biçimler yazıldı", os.path.isfile(os.path.join(worker.DEDPLAY_DIR, "PDF", "Türkçe", ad + ".pdf")))
# Kitap Okuma düzeltmede bölümü siler ve yeniden yazar, M4B'yi yeniden kurar
os.remove(os.path.join(kaynak, "Bolum_001_Baslik.mp3"))
open(os.path.join(kaynak, "Bolum_001_Baslik.mp3"), "wb").write(b"ses-yeni")
os.remove(os.path.join(kaynak, ad + ".m4b"))
open(os.path.join(kaynak, ad + ".m4b"), "wb").write(b"m4b-yeni")
worker.save_outputs_yeni(j, [], ad)
dene("Yenilenen bölüm çıktıya geldi", open(mp3, "rb").read() == b"ses-yeni")
dene("Yenilenen M4B çıktıya geldi", open(m4b, "rb").read() == b"m4b-yeni")
# kullanıcı çıktıyı silerse kaynak kalır
os.remove(m4b)
dene("Çıktı silinince Kitap Okuma'nın dosyası kalır", os.path.isfile(os.path.join(kaynak, ad + ".m4b")))
# farklı diskte (bağlantı kurulamazsa) kopya
eski_link = os.link
os.link = lambda a, b: (_ for _ in ()).throw(OSError(18, "Invalid cross-device link"))
worker.save_outputs_yeni(j, [], ad)
os.link = eski_link
dene("Bağlantı kurulamazsa kopyalanır", os.path.isfile(m4b) and not os.path.samefile(m4b, os.path.join(kaynak, ad + ".m4b")))

print("SONUC: HEPSI GECTI" if not kalan else f"SONUC: {len(kalan)} TEST KALDI")
