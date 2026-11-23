"""0.5.86: OCR onarımı (Zahir, 23 Kasım: "kitap eklenince önce hataları düzeltilip Türkçe hâli hatasız olmalı").

Kitap eklenince (kaynaktan okunduktan hemen sonra, yapay zekâ denetiminden ve Osmanlıcadan önce) Türkçe metindeki OCR'ın her taramada
aynı biçimde bozduğu kelimeler düzeltilir. Bütün kitaplara aynı kural; kitaba özel düzeltme yok.

Kural:
  * Kelime bilinmiyor (Zemberek + Türkçe sıklık listesi + Osmanlıca sözlükte tam kayıt yok) ve OCR karışıklığı tersine çevrilince
    (m <- nı/ni/rn/nr/ru/ın, n <- rı/ri, H <- Fi/Fl kelime başında, ü <- tı/t, ii <- ü) bilinen bir kelime çıkıyorsa o alınır.
    Adaylar arasında önce kitapta geçen, sonra genel sıklıkta yaygın olan seçilir; iki aday yakınsa kelimeye dokunulmaz.
  * Geçerli ama çok seyrek kelime (aym, soma, onlan): yalnız m/n karışıklığıyla, aday en az 500 kez ve 100 kat daha yaygınsa.
Korumalar: yaygın kelime (Zemberek tanımasa da: yapacağım), 1. kişi ortaç (edildiğim), Osmanlıca sözlükte tam kaydı olan kelime (azm,
fîmâ, Dimne), Arapça tamlama parçası (cennetü), 3 harfli kelime yalnız çok yaygın adayla (aym -> aynı).
Ölçüm (23 Kasım): İdeal Devlet 406 düzeltme (aym -> aynı 52, soma -> sonra 49, onlann -> onların 25…); temiz kitaplarda 43 bin kelimede 8,
147 bin kelimede 2. Her düzeltme kitap klasöründe ocr_onarim.txt'ye yazılır. STUDYO_OCR_ONARIM=0 kapatır."""
import collections
import gzip
import itertools
import os
import re

_YER = os.path.dirname(os.path.abspath(__file__))
KELIME = re.compile(r"[^\W\d_]+")
ESLER = [("m", "nı"), ("m", "ni"), ("m", "rn"), ("m", "ın"), ("m", "in"), ("m", "nu"), ("m", "nü"), ("m", "un"), ("m", "ün"),
         ("n", "rı"), ("n", "ri"), ("n", "ru"), ("n", "rü"), ("fi", "h"), ("fl", "h"), ("ü", "tı"), ("ü", "ti"), ("ü", "t"),
         ("ii", "ü"), ("rn", "m"), ("ıı", "n"), ("m", "ru"), ("m", "rü"), ("m", "nr")]
GERCEK_ESLER = {("m", "nı"), ("m", "ni"), ("m", "rn"), ("m", "ın"), ("m", "in"), ("n", "rı"), ("n", "ri"), ("m", "ru"), ("m", "nr")}
UNLU = set("aeıioöuüâîû")
_F = None
_OSM = None


def acik() -> bool:
    return os.environ.get("STUDYO_OCR_ONARIM", "1") != "0"


def _frekans():
    global _F
    if _F is None:
        _F = {}
        try:
            with gzip.open(os.path.join(_YER, "tr_frekans.tsv.gz"), "rt", encoding="utf-8") as f:
                for satir in f:
                    w, _, c = satir.rstrip("\n").partition("\t")
                    _F[w] = int(c or 0)
        except OSError:
            pass
    return _F


def _osm():
    global _OSM
    if _OSM is None:
        try:
            with gzip.open(os.path.join(_YER, "osm_kelime.txt.gz"), "rt", encoding="utf-8") as f:
                _OSM = set(f.read().split("\n"))
        except OSError:
            _OSM = set()
    return _OSM


def kucuk(w):
    return w.replace("I", "ı").replace("İ", "i").lower()


def _gecerli(w):
    from . import rapor as R
    return R._gecerli(w)


def adaylar(w, en_cok=3, yalniz=None):
    yerler = [(i, a, b) for i in range(len(w)) for a, b in ESLER if w.startswith(a, i)
              and (a not in ("fi", "fl") or i == 0) and (yalniz is None or (a, b) in yalniz)]
    out = {}
    for n in range(1, en_cok + 1):
        for sec in itertools.combinations(yerler, n):
            s = sorted(sec)
            if any(s[j][0] + len(s[j][1]) > s[j + 1][0] for j in range(len(s) - 1)):
                continue
            k = w
            for i, a, b in reversed(s):
                k = k[:i] + b + k[i + len(a):]
            if k not in out and len(k) >= 3 and any(c in UNLU for c in k):
                out[k] = n
    return out


def karar_ver(w, kitap):
    """Küçük harfli kelime -> doğrusu ya da None."""
    F = _frekans()
    if len(w) < 3 or not F:
        return None
    kisa = len(w) == 3
    if re.search(r"(ğ[ıiuü]m|[cç][ae]ğ[ıi]m)$", w):
        return None
    osm = _osm()
    if w[-1] in "üuıi" and w[:-1] in osm:
        return None
    gec = _gecerli(w)
    if F.get(w, 0) >= (30 if gec else 20):
        return None
    if not gec and w in osm:
        return None
    ad = adaylar(w, yalniz=GERCEK_ESLER if gec else None)
    puan = []
    for k, n in ad.items():
        fk, kk = F.get(k, 0), kitap.get(k, 0)
        if kisa and fk < 2000:
            continue
        if not _gecerli(k) and fk < 50:
            continue
        if gec:
            if fk >= 500 and fk >= 100 * max(F.get(w, 0), 1):
                puan.append((fk + 1000 * kk, -n, k))
        elif fk >= 3 or kk >= 1:
            puan.append((kk * 1000 + fk, -n, k))
    if not puan:
        return None
    puan.sort(reverse=True)
    if len(puan) > 1 and (puan[0][:2] == puan[1][:2] or (puan[1][0] * 3 > puan[0][0] and puan[1][1] == puan[0][1])):
        return None
    return puan[0][2]


def _bicim(asil, dogru):
    if asil.isupper() and len(asil) > 1:
        return dogru.replace("i", "İ").replace("ı", "I").upper()
    if asil[:1].isupper():
        return (dogru[:1].replace("i", "İ").replace("ı", "I").upper()) + dogru[1:]
    return dogru


def kitabi_onar(kit, klasor=None):
    """kitap.json sözlüğünde Türkçe metni (bloklar, dipnotlar) onarır. Dönen: {yanlış: (doğru, adet)}."""
    if not acik() or kit.get("kunye", {}).get("asil_dil") != "tr":
        return {}
    alanlar = []
    for b in kit.get("bloklar", []):
        if b.get("metin", {}).get("tr") and not (b.get("elle") or {}).get("tr"):
            alanlar.append(b["metin"])
    for n in (kit.get("dipnotlar") or {}).values():
        if n.get("metin", {}).get("tr"):
            alanlar.append(n["metin"])
    kitap = collections.Counter(kucuk(w) for m in alanlar for w in KELIME.findall(m["tr"]))
    duzelt = {}
    for w in kitap:
        d = karar_ver(w, kitap)
        if d and d != w:
            duzelt[w] = d
    if not duzelt:
        return {}
    say = collections.Counter()

    def degis(mt):
        asil = mt.group(0)
        d = duzelt.get(kucuk(asil))
        if not d:
            return asil
        say[kucuk(asil)] += 1
        return _bicim(asil, d)
    for m in alanlar:
        m["tr"] = KELIME.sub(degis, m["tr"])
    sonuc = {w: (duzelt[w], say[w]) for w in say}
    kit["kunye"]["ocr_onarim"] = {"tur": len(sonuc), "gecis": sum(say.values())}
    if klasor:
        try:
            with open(os.path.join(klasor, "ocr_onarim.txt"), "w", encoding="utf-8") as f:
                f.write(f"OCR onarımı: {len(sonuc)} kelime, {sum(say.values())} geçiş\n")
                for w, (d, n) in sorted(sonuc.items(), key=lambda x: -x[1][1]):
                    f.write(f"{n}\t{w} -> {d}\n")
        except OSError:
            pass
    return sonuc
