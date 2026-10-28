"""0.5.51: sayfa düzeni (Surya LayoutPredictor kutuları) ile resim içindeki yazıların ve resim altı yazısının metinden çıkması.
  python tests/test_0551.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kutuphane import kaynak as K  # noqa: E402

hata = 0


def kontrol(ad, kosul):
    global hata
    print(("TAMAM " if kosul else "HATA  ") + ad)
    hata += not kosul


def satir(t, x0, top, x1, bot):
    return {"text": t, "x0": x0, "x1": x1, "top": top, "bot": bot, "h": bot - top, "n": len(t.split())}


# Tahrif 1 s.393 benzeri: el yazısı mektup (Arapça satırlar) + resim altı yazısı + gövde
govde = [satir("masonlar arasında Efgânî de yer almış ve onlar tarafından, her yerde", 27, 355, 328, 366),
         satir("her zaman aydınlık saçan bir zât, dikkate değer bir yazar ve usta bir", 27, 369, 328, 380),
         satir("hatip olarak tavsif ve medhedilmiştir ve bu iş böylece bitmiştir.", 27, 384, 328, 396)]
mektup = [satir("ہے۔بعد ل مرکس سوم احاسے بے اور", 84, 73, 271, 98), satir("ا .الدئ تجامع توسيعة اوتيون", 84, 105, 299, 132)]
alt = [satir("Cemâleddin-i Efgânî'nin Mason locasına mürâcaat mektûbu", 55, 337, 302, 347)]
rows = mektup + alt + govde
bolge = [("Handwriting", 43.1, 62.7, 300.5, 321.7, 1.0), ("Caption", 54.2, 336.0, 302.6, 346.9, 0.947),
         ("Text", 27.2, 354.0, 327.6, 426.5, 1.0)]
sil = K._resim_satirlari(rows, bolge, 391)
kontrol("el yazısı (Handwriting) içindeki satırlar çıkar", {0, 1} <= sil)
kontrol("resim altı yazısı çıkar", 2 in sil)
kontrol("gövde satırlarına dokunulmaz", not ({3, 4, 5} & sil))
# model yanılıp gövdeyi resim saydıysa: kutunun içindeki satırların çoğu tam genişlikte, 6+ kelime -> dokunulmaz
kontrol("gövdeye benzeyen resim kutusu yok sayılır", not K._resim_satirlari(govde, [("Picture", 20, 340, 330, 400, 0.9)], 391))
# yan çevrilmiş sayfa (satırlar dikey): kutular metinle örtüşmez -> dokunulmaz
yan = [satir("Bu tezvirâttan sonra merhum Süleyman Hilmi Tunahan Hazretlerinin", 61, 46, 75, 545),
       satir("Bir devrin Diyanet İşleri Başkanı Tayyar Altıkulaç", 99, 47, 113, 545)]
kontrol("yan çevrilmiş sayfaya dokunulmaz", not K._resim_satirlari(yan, [("Figure", 37, 45, 240, 554, 0.76)], 386))
# uzun resim altı (3+ satır ya da 15+ kelime) çıkmaz
uzun = [satir("Bir iki üç dört beş altı yedi sekiz", 30, 300, 300, 310), satir("dokuz on on bir on iki on üç", 30, 312, 300, 322),
        satir("on dört on beş on altı", 30, 324, 300, 334)]
kontrol("uzun resim altı yazısı çıkmaz", not K._resim_satirlari(uzun, [("Picture", 30, 50, 300, 290, 0.9), ("Caption", 25, 298, 305, 336, 0.9)], 391))
kontrol("resim olmayan sayfada hiçbir şey çıkmaz", not K._resim_satirlari(govde, [("Text", 27, 354, 328, 426, 1.0)], 391))
print("SONUÇ:", "HATA" if hata else "TAMAM")
sys.exit(1 if hata else 0)
