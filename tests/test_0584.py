"""0.5.84: NVIDIA açıkken köken adımı Gemini'ye düşmez (STUDYO_KOKEN_GEMINI=1 ise düşer)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["NVIDIA_API_KEY"] = "nvapi-deneme"
os.environ["STUDYO_KOKEN_NVIDIA"] = "a/model-1"
from kutuphane import koken, nvidia, yz  # noqa: E402

koken._bilinmeyenler = lambda metin: ["kalemler", "gelir"]
koken._kaydet = lambda k: {"onayli": len(k)}
gemini = []


def nv_dolu(self, sistem, kullanici, en_fazla=6000):
    raise nvidia.SinirDoldu("kredi bitti")


def gem(self, sistem, kullanici, en_fazla=6000):
    gemini.append(1)
    return '[{"no":1,"koken":"ar","kok":"kalem","yazilis":"قلم"},{"no":2,"koken":"tr","kok":"gel"}]', "gemini-3.5-flash"


nvidia.Nvidia.sor = nv_dolu
yz.Gemini.sor = gem
yz.acik = lambda: True
oz = koken.kokenleri_sor(["kalemler gelir"])
assert gemini == [] and oz["soruldu"] == 0 and oz["durum"] == "gunluk_sinir", (gemini, oz)
os.environ["STUDYO_KOKEN_GEMINI"] = "1"
oz = koken.kokenleri_sor(["kalemler gelir"])
assert gemini == [1] and oz["soruldu"] == 2, (gemini, oz)
print("SONUC: HEPSI GECTI")
