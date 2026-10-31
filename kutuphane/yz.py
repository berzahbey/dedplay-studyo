"""0.5.53: Yapay zekâ (Google Gemini API) — kitap denetimi (kutuphane/denetim.py) için.

Ayar /data/yz_ayar.json: {"anahtar": "...", "acik": true, "seslendirme_otomatik": false}. Anahtar yalnız bu dosyada durur;
istekte "x-goog-api-key" başlığında gider (adreste değil), sayfaya ve günlüğe yalnız son 4 hanesi çıkar.
Modeller: hesabın gördüğü kararlı Flash-Lite modelleri, yeniden eskiye (Zahir'in ücretsiz hesabı, 28 Ekim: 3.5 ve 3.1 Flash-Lite,
her biri dakikada 15, günde 500 istek; sınır her model için ayrı sayılır). Biri günlük sınıra varınca sıradakine geçilir; hepsi
dolunca GunlukSinir (denetim Pasifik gece yarısından sonra kaldığı yerden sürer). Dakika sınırı bütün iş parçacıklarında ortak
sayılır (aynı anda 3 kitap). Sayaç /data/yz_sayac.json (Pasifik günü; Google'ın günlük sınırı o saatte sıfırlanır).
Sınamada STUDYO_YZ_SAHTE=1: kurallı sahte cevaplar (akışın sınanması için)."""
import collections
import datetime
import json
import os
import re
import threading
import time

VERI = os.environ.get("DATA_DIR", "/data")
AYAR = os.path.join(VERI, "yz_ayar.json")
SAYAC = os.path.join(VERI, "yz_sayac.json")
GEMINI_URL = os.environ.get("STUDYO_GEMINI_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
DAKIKA_SINIRI = int(os.environ.get("STUDYO_GEMINI_RPM", "12"))      # 15'in altında: başka kullanım için pay
GUNLUK_SINIR = int(os.environ.get("STUDYO_GEMINI_RPD", "490"))      # 500'ün altında
_kilit = threading.Lock()
_zamanlar = collections.defaultdict(collections.deque)              # model -> son istek zamanları (dakika sınırı)
_model_onbellek = {"zaman": 0, "liste": []}


class GunlukSinir(Exception):
    """Bütün modellerin günlük ücretsiz sınırı doldu."""


class GeciciHata(RuntimeError):
    """0.5.57: Gemini şu an cevap vermiyor (zaman aşımı, bağlantı, 5xx; 10 denemede): denetim bir süre sonra yeniden denenir."""


# ---------------------------------------------------------------- ayar
def ayarlar():
    try:
        with open(AYAR, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def ayar_yaz(**kw):
    with _kilit:
        a = ayarlar()
        a.update(kw)
        os.makedirs(os.path.dirname(AYAR), exist_ok=True)
        tmp = AYAR + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(a, f, ensure_ascii=False)
        os.chmod(tmp, 0o600)
        os.replace(tmp, AYAR)
        return a


def acik():
    """Denetim kendiliğinden çalışır mı: anahtar kayıtlı ve kapatılmamış."""
    a = ayarlar()
    return bool((a.get("anahtar") or os.environ.get("STUDYO_YZ_SAHTE")) and a.get("acik", True))


def ozet():
    """Sayfa için: anahtarın yalnız son 4 hanesi, bugünkü sayaç."""
    a = ayarlar()
    s = _sayac()
    return {"anahtar_son": (a.get("anahtar") or "")[-4:], "acik": acik(), "anahtar_var": bool(a.get("anahtar")),
            "seslendirme_otomatik": bool(a.get("seslendirme_otomatik", False)),
            "gun": s["gun"], "istek": s["istek"], "tukenen": s["tukenen"], "gunluk_sinir": GUNLUK_SINIR}


# ---------------------------------------------------------------- günlük sayaç (Pasifik günü)
def _pasifik_gunu():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()
    except Exception:
        return (datetime.datetime.utcnow() - datetime.timedelta(hours=8)).date().isoformat()


def sifirlanma():
    """Günlük sınırın sıfırlanacağı an (yerel saat, epoch): Pasifik gece yarısı + 5 dk."""
    try:
        from zoneinfo import ZoneInfo
        p = datetime.datetime.now(ZoneInfo("America/Los_Angeles"))
        yarin = (p + datetime.timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
        return yarin.timestamp()
    except Exception:
        return time.time() + 6 * 3600


def _sayac():
    try:
        with open(SAYAC, encoding="utf-8") as f:
            s = json.load(f)
    except (OSError, ValueError):
        s = {}
    if s.get("gun") != _pasifik_gunu():
        s = {"gun": _pasifik_gunu(), "istek": {}, "tukenen": []}
    s.setdefault("istek", {})
    s.setdefault("tukenen", [])
    return s


def _sayac_yaz(s):
    os.makedirs(os.path.dirname(SAYAC), exist_ok=True)
    tmp = SAYAC + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(s, f)
    os.replace(tmp, SAYAC)


def _say(model, tukendi=False):
    with _kilit:
        s = _sayac()
        if tukendi:
            if model not in s["tukenen"]:
                s["tukenen"].append(model)
        else:
            s["istek"][model] = s["istek"].get(model, 0) + 1
            if s["istek"][model] >= GUNLUK_SINIR and model not in s["tukenen"]:
                s["tukenen"].append(model)
        _sayac_yaz(s)


def _bekle_dakika(model):
    """Dakika sınırı (bütün iş parçacıklarında ortak): son 60 sn'de DAKIKA_SINIRI istek varsa sıra gelene kadar bekler."""
    while True:
        with _kilit:
            q = _zamanlar[model]
            simdi = time.time()
            while q and simdi - q[0] > 60:
                q.popleft()
            if len(q) < DAKIKA_SINIRI:
                q.append(simdi)
                return
            bekle = 60 - (simdi - q[0]) + 0.5
        time.sleep(max(0.5, bekle))


def kullanilamaz_ekle(model):
    """0.5.56: modeli kalıcı olarak atla (ayarda "kullanilamaz"); model listesi önbelleği silinir."""
    with _kilit:
        yok = list(ayarlar().get("kullanilamaz") or [])
    if model not in yok:
        ayar_yaz(kullanilamaz=yok + [model])
    _model_onbellek.update(zaman=0, liste=[])


# ---------------------------------------------------------------- Gemini
def _istek(yol, govde=None, anahtar=None, zaman=120):
    import requests
    anahtar = anahtar or ayarlar().get("anahtar") or ""
    if not anahtar:
        raise RuntimeError("Gemini anahtarı kayıtlı değil (Yapay zekâ ayarı)")
    bas = {"x-goog-api-key": anahtar, "Content-Type": "application/json"}   # anahtar başlıkta, adreste değil
    url = f"{GEMINI_URL}/{yol}"
    return requests.post(url, headers=bas, json=govde, timeout=zaman) if govde is not None else \
        requests.get(url, headers=bas, timeout=zaman)


def modeller(anahtar=None):
    """Hesabın gördüğü kararlı Flash-Lite modelleri, yeniden eskiye (günde bir kez sorulur)."""
    if not anahtar and _model_onbellek["liste"] and time.time() - _model_onbellek["zaman"] < 86400:
        return _model_onbellek["liste"]
    r = _istek("models?pageSize=200", anahtar=anahtar, zaman=30)
    if r.status_code != 200:
        raise RuntimeError(f"Gemini model listesi alınamadı ({r.status_code}): {r.text[:200]}")
    out = []
    for m in r.json().get("models", []):
        ad = m.get("name", "").split("/")[-1]
        g = re.fullmatch(r"gemini-(\d+(?:\.\d+)?)-flash-lite", ad)
        if g and "generateContent" in (m.get("supportedGenerationMethods") or []):
            out.append((float(g.group(1)), ad))
    yok = set(ayarlar().get("kullanilamaz") or [])   # 0.5.56: Google'ın kapattığı modeller (404 "no longer available")
    liste = [ad for _, ad in sorted(out, reverse=True) if ad not in yok]
    if not liste:
        raise RuntimeError("Hesapta kullanılabilir Gemini Flash-Lite modeli bulunamadı")
    if not anahtar:
        _model_onbellek.update(zaman=time.time(), liste=liste)
    return liste


def _bekleme(r):
    """429 cevabından: (günlük mü, beklenecek saniye)."""
    try:
        e = r.json().get("error", {})
    except ValueError:
        return False, 30
    gun, bekle = False, 30
    for d in e.get("details", []):
        if "RetryInfo" in d.get("@type", "") and d.get("retryDelay"):
            try:
                bekle = float(str(d["retryDelay"]).rstrip("s")) + 1
            except ValueError:
                pass
        for v in d.get("violations", []) if "QuotaFailure" in d.get("@type", "") else []:
            if "PerDay" in (v.get("quotaId") or "") or "per_day" in (v.get("quotaMetric") or "").lower():
                gun = True
    return gun, bekle


class Gemini:
    """Bir denetimin modeli. .ad o anki model ("gemini:<ad>"); sınır dolunca sıradaki Flash-Lite modeline geçer."""

    def __init__(self, ilerleme=None):
        self.ilerleme = ilerleme or (lambda m: None)
        self.sayac = {"cagri": 0, "giris": 0, "cikis": 0, "sure": 0.0, "bekleme": 0.0}
        self.kullanilan = collections.Counter()
        self.sahte = bool(os.environ.get("STUDYO_YZ_SAHTE"))
        self._ad = None

    @property
    def ad(self):
        if self.sahte:
            return "gemini:sahte-lite"
        if self._ad is None:
            self._ad = self._sec()
        return "gemini:" + self._ad

    def _sec(self):
        tukenen = set(_sayac()["tukenen"])
        for m in modeller():
            if m not in tukenen:
                return m
        raise GunlukSinir("Gemini'nin bütün Flash-Lite modellerinin günlük ücretsiz sınırı doldu")

    def sor(self, sistem, kullanici, en_fazla=800):
        """Tek soru, tek cevap (ısı 0). Dönen: (cevap metni, cevabı veren model adı)."""
        t0 = time.time()
        if self.sahte:
            cevap, model = sahte_cevap(kullanici), "sahte-lite"
        else:
            cevap, model = self._gemini(sistem, kullanici, en_fazla)
        self.sayac["cagri"] += 1
        self.sayac["sure"] += time.time() - t0
        self.kullanilan[model] += 1
        return cevap, model

    def _gemini(self, sistem, kullanici, en_fazla):
        govde = {"systemInstruction": {"parts": [{"text": sistem}]},
                 "contents": [{"role": "user", "parts": [{"text": kullanici}]}],
                 "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                      "maxOutputTokens": max(1024, en_fazla * 2)}}
        for deneme in range(10):
            model = self.ad[7:]
            _bekle_dakika(model)
            try:
                r = _istek(f"models/{model}:generateContent", govde, zaman=240)
            except Exception as e:      # 0.5.57: zaman aşımı/bağlantı hatası denemeyi bitirmez (31 Ekim: 18 kitapta ReadTimeout)
                import requests
                if not isinstance(e, requests.RequestException):
                    raise
                _say(model)
                self.ilerleme(f"Gemini cevap vermedi ({type(e).__name__}); yeniden deneniyor")
                time.sleep(15 * (deneme + 1))
                self.sayac["bekleme"] += 15 * (deneme + 1)
                continue
            _say(model)
            if r.status_code == 200:
                d = r.json()
                u = d.get("usageMetadata") or {}
                self.sayac["giris"] += u.get("promptTokenCount", 0)
                self.sayac["cikis"] += u.get("candidatesTokenCount", 0)
                try:
                    return "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"]), model
                except (KeyError, IndexError):
                    return "", model       # güvenlik filtresi vb.: bu grup cevapsız kalır (sonra yeniden sorulur)
            if r.status_code == 429:
                gun, bekle = _bekleme(r)
                if gun:
                    _say(model, tukendi=True)
                    self._ad = None            # sıradaki model (yoksa GunlukSinir)
                    self.ilerleme(f"{model} günlük sınırı doldu; sıradaki modele geçiliyor")
                    continue
                time.sleep(min(bekle, 90))
                self.sayac["bekleme"] += min(bekle, 90)
                continue
            if r.status_code in (500, 502, 503, 504):
                time.sleep(10 * (deneme + 1))
                continue
            if r.status_code == 404 or (r.status_code == 400 and "no longer available" in r.text):
                # 0.5.56: model listede görünüyor ama hesaba kapalı (Tahrif 3, 31 Ekim: gemini-2.5-flash-lite "no longer available
                # to new users"): kalıcı olarak atlanır, sıradaki modele geçilir (yoksa GunlukSinir: denetim ertesi gün sürer)
                kullanilamaz_ekle(model)
                self._ad = None
                self.ilerleme(f"{model} kullanılamıyor (Google kapatmış); sıradaki modele geçiliyor")
                continue
            raise RuntimeError(f"Gemini hatası {r.status_code}: {r.text[:300]}")
        raise GeciciHata("Gemini cevap vermedi (10 deneme)")


def dene(anahtar=None):
    """Anahtarı dener: model listesi + tek kısa soru (kitap metni gönderilmez)."""
    try:
        m = modeller(anahtar=anahtar)[0]
        r = _istek(f"models/{m}:generateContent", {"contents": [{"role": "user", "parts": [{"text": "Yalnız TAMAM yaz."}]}],
                                                    "generationConfig": {"temperature": 0, "maxOutputTokens": 10}},
                   anahtar=anahtar, zaman=60)
        if r.status_code == 429:
            return {"ok": True, "model": m, "mesaj": "Anahtar çalışıyor (şu an sınırda)"}
        if r.status_code in (500, 502, 503, 504):
            return {"ok": True, "model": m, "mesaj": f"Anahtar çalışıyor; model şu an yoğun ({r.status_code}), denetim bekleyip yeniden dener"}
        if r.status_code != 200:
            return {"ok": False, "model": m, "mesaj": f"Hata {r.status_code}: {r.text[:300]}"}
        return {"ok": True, "model": m, "mesaj": "Anahtar çalışıyor"}
    except Exception as e:
        return {"ok": False, "model": "", "mesaj": f"{type(e).__name__}: {str(e)[:300]}"}


def json_al(metin):
    """Cevaptaki ilk JSON dizisi/nesnesi (```json ... ``` çiti olsa da). Okunamazsa None."""
    m = re.search(r"```(?:json)?\s*(.*?)```", metin or "", re.S)
    if m:
        metin = m.group(1)
    metin = metin or ""
    for ac, kapa in (("[", "]"), ("{", "}")):
        i, j = metin.find(ac), metin.rfind(kapa)
        if i >= 0 and j > i:
            try:
                return json.loads(metin[i:j + 1])
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------- sınama için sahte model
def sahte_cevap(kullanici):
    """Görev türünü istemden anlar; basit kurallarla cevap verir (yalnız akışın sınanması için)."""
    maddeler = re.findall(r"^(\d+)\. (.*)$", kullanici, re.M)
    if "PARANTEZ GÖREVİ" in kullanici:
        out = []
        for no, satir in maddeler:
            ic = re.search(r"«\((.*?)\)»", satir)
            ic = ic.group(1) if ic else ""
            out.append({"no": int(no), "tur": "kaynak" if re.search(r"\d{4}|sh[:.]|mecmua|The |a\.g\.e|Yay", ic) else "aciklama"})
        return json.dumps(out, ensure_ascii=False)
    if "KELİME GÖREVİ" in kullanici:
        out = []
        for no, satir in maddeler:
            k = re.search(r"«(.*?)»", satir)
            k = k.group(1) if k else ""
            out.append({"no": int(no), "hata": k.endswith("x"), "dogru": k[:-1] if k.endswith("x") else k})
        return json.dumps(out, ensure_ascii=False)
    if "RESİM GÖREVİ" in kullanici:
        return json.dumps([{"no": int(no), "tur": "resim" if re.search(r"[äåЀ-ӿ]", s) else "ana_metin"}
                           for no, s in maddeler])
    if "SATIR GÖREVİ" in kullanici:
        return json.dumps([{"no": int(no), "tur": "kaynak" if "a.g.e" in s else "ana_metin"} for no, s in maddeler])
    if "SAYI GÖREVİ" in kullanici:
        return json.dumps([{"no": int(no), "dipnot_isareti": True} for no, _ in maddeler])
    return "[]"
