"""0.5.82: köken adımı önce NVIDIA (STUDYO_KOKEN_NVIDIA), olmazsa Gemini."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["NVIDIA_API_KEY"] = "nvapi-deneme"
os.environ["STUDYO_KOKEN_NVIDIA"] = "a/model-1,b/model-2"
from kutuphane import koken, nvidia, yz  # noqa: E402

kayit = []
koken._bilinmeyenler = lambda metin: ["kalemler", "gelir"]
koken._kaydet = lambda k: (kayit.extend(k), {"onayli": len(k)})[1]
sorulan = []


def sahte_sor(self, sistem, kullanici, en_fazla=6000):
    sorulan.append(self.model)
    if self.model == "a/model-1":
        raise nvidia.SinirDoldu("kredi bitti")
    return '[{"no":1,"koken":"ar","kok":"kalem","yazilis":"قلم"},{"no":2,"koken":"tr","kok":"gel"}]', "nvidia/" + self.model


nvidia.Nvidia.sor = sahte_sor
yz.acik = lambda: False
oz = koken.kokenleri_sor(["kalemler gelir"])
assert sorulan == ["a/model-1", "b/model-2"], sorulan
assert [k["model"] for k in kayit] == ["nvidia/b/model-2"] * 2, kayit
assert oz["soruldu"] == 2 and oz["durum"] == "tamam", oz
print("SONUC: HEPSI GECTI")
