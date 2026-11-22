"""0.5.82 (22 Kasım 2026): NVIDIA API (build.nvidia.com) köken sağlayıcısı.
OpenAI uyumlu uç: https://integrate.api.nvidia.com/v1/chat/completions, anahtar NVIDIA_API_KEY (nvapi-...).
Köken adımı STUDYO_KOKEN_NVIDIA'daki modelleri (virgülle, sırayla) önce dener; hepsi başarısızsa Gemini'ye düşer.
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
        govde = {"model": self.model, "temperature": 0, "max_tokens": max(2048, en_fazla * 2),
                 "messages": [{"role": "system", "content": sistem}, {"role": "user", "content": kullanici}]}
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
                metin = (ch.get("message") or {}).get("content") or ""
                return _DUSUNCE.sub("", metin).strip(), "nvidia/" + self.model
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
