"""0.5.82 (22 Kasım 2026): NVIDIA API (build.nvidia.com) köken sağlayıcısı.
OpenAI uyumlu uç: https://integrate.api.nvidia.com/v1/chat/completions, anahtar NVIDIA_API_KEY (nvapi-...).
Köken adımı STUDYO_KOKEN_NVIDIA'daki modelleri (virgülle, sırayla) önce dener; hepsi başarısızsa grup sonraki çeviride yeniden sorulur
(0.5.84; STUDYO_KOKEN_GEMINI=1 ise Gemini'ye düşer).
Model adı kayda "nvidia/<model>" diye yazılır (çevirici yz_kayit.guvenilir: adında "lite" yoksa güvenilir sayılır)."""
import os
import re
import time

import requests

URL = os.environ.get("STUDYO_NVIDIA_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")


def anahtar():
    return (os.environ.get("NVIDIA_API_KEY") or "").strip()


def modeller():
    return [m.strip() for m in os.environ.get("STUDYO_KOKEN_NVIDIA", "").split(",") if m.strip()]


def acik():
    return bool(anahtar() and modeller())


class SinirDoldu(Exception):
    """Hesabın kredisi / günlük sınırı bitti (402, ya da 429 ve bekleme işe yaramadı)."""


_DUSUNCE = re.compile(r"<think>.*?</think>", re.S)


class Nvidia:
    def __init__(self, model):
        self.model = model
        self.zaman = 300
        self.deneme = 5
        self.son_bitis = ""

    def sor(self, sistem, kullanici, en_fazla=6000):
        """(cevap metni, "nvidia/<model>")"""
        govde = {"model": self.model, "temperature": 0, "max_tokens": max(4096, en_fazla * 3),
                 "messages": [{"role": "system", "content": sistem}, {"role": "user", "content": kullanici}]}
        dus = os.environ.get("STUDYO_NVIDIA_DUSUNME", "").strip()      # 0.5.83: düşünen modellerde "low" / "none"
        if dus:
            govde["reasoning_effort"] = dus
        bas = {"Authorization": "Bearer " + anahtar(), "Content-Type": "application/json", "Accept": "application/json"}
        for deneme in range(self.deneme):
            try:
                r = requests.post(URL + "/chat/completions", headers=bas, json=govde, timeout=self.zaman)
            except requests.RequestException:
                time.sleep(15 * (deneme + 1))
                continue
            if r.status_code == 200:
                d = r.json()
                ch = (d.get("choices") or [{}])[0]
                self.son_bitis = str(ch.get("finish_reason") or "")
                msj = ch.get("message") or {}
                metin = _DUSUNCE.sub("", msj.get("content") or "").strip()
                if "[" not in metin:          # 0.5.83: düşünen model cevabı düşünme alanında bırakmış olabilir
                    dusunce = msj.get("reasoning_content") or msj.get("reasoning") or ""
                    i = dusunce.rfind("[{")
                    if i >= 0:
                        metin = dusunce[i:]
                self.son_uzunluk = len(metin)
                return metin, "nvidia/" + self.model
            if r.status_code == 402:
                raise SinirDoldu(f"{self.model}: kredi bitti (402)")
            if r.status_code == 429:
                time.sleep(min(30 * (deneme + 1), 120))
                continue
            if r.status_code in (500, 502, 503, 504):
                time.sleep(10 * (deneme + 1))
                continue
            raise RuntimeError(f"NVIDIA hatası {r.status_code}: {r.text[:300]}")
        raise SinirDoldu(f"{self.model}: {self.deneme} denemede cevap yok (sınır ya da yoğunluk)")
