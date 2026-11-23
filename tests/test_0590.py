"""0.5.90: denetim NVIDIA ile (köken modeli; STUDYO_DENETIM_NVIDIA=0 Gemini); cevapsızlık GeciciHata; küçük gruplar."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["NVIDIA_API_KEY"] = "nvapi-deneme"
os.environ["STUDYO_KOKEN_NVIDIA"] = "nvidia/model-1"
from kutuphane import denetim as D, nvidia, yz  # noqa: E402

assert D.nvidia_modeli() == "nvidia/model-1"
os.environ["STUDYO_DENETIM_NVIDIA"] = "0"
assert D.nvidia_modeli() is None
os.environ["STUDYO_DENETIM_NVIDIA"] = "z-ai/glm-5.3-flash"
assert D.nvidia_modeli() == "z-ai/glm-5.3-flash"
istekler = []
def sor(self, sistem, kullanici, en_fazla=6000):
    istekler.append(kullanici.count("\n"))
    return "[]", "nvidia/" + self.model
nvidia.Nvidia.sor = sor
dn = D.Denetci(tempfile.mkdtemp(), model=D.NvidiaDenetim("nvidia/model-1"), on_ek="n:")
dn._sor("kelime", "{maddeler}", [(f"a{i}", f"madde {i}") for i in range(250)], 20, "hata", "kelime")
assert len(istekler) == 3, istekler            # 100'lük gruplar
def dolu(self, *a, **k):
    raise nvidia.SinirDoldu("yok")
nvidia.Nvidia.sor = dolu
try:
    D.NvidiaDenetim("x").sor("s", "k")
    raise AssertionError("GeciciHata bekleniyordu")
except yz.GeciciHata:
    pass
print("SONUC: HEPSI GECTI")
