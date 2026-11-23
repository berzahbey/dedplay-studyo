"""0.5.85: köken adımı süre dolunca Osmanlıcayı bekletmez; yoldaki grup arka planda biter ve kaydedilir."""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["NVIDIA_API_KEY"] = "nvapi-deneme"
os.environ["STUDYO_KOKEN_NVIDIA"] = "nvidia/model-1"
os.environ["STUDYO_KOKEN_SURE"] = "30"
from kutuphane import koken, nvidia, yz  # noqa: E402

koken.GRUP = 1
koken._bilinmeyenler = lambda metin: ["kalemler", "gelir", "kitaplar", "masalar"]
kayit = []
koken._kaydet = lambda k: kayit.extend(k) or {"onayli": len(k)}
yavas = {"gelir"}


def sor(self, sistem, kullanici, en_fazla=6000):
    w = kullanici.split(". ", 1)[1]
    time.sleep(60 if w in yavas else 0.1)
    return '[{"no":1,"koken":"tr","kok":"%s"}]' % w, "nvidia/model-1"


nvidia.Nvidia.sor = sor
yz.acik = lambda: True
bas = time.time()
durumlar = []
oz = koken.kokenleri_sor(["x"], durumlar.append)
sure = time.time() - bas
assert 29 <= sure < 40, sure
assert oz["durum"] == "sure_doldu" and oz["soruldu"] == 3, oz
assert nvidia.Nvidia("nvidia/x").model == "nvidia/x"
print("SONUC: HEPSI GECTI", round(sure), oz)
