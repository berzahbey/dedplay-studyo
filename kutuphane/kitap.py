"""Dedplay Kütüphane'nin ortak kitap biçimi (kitap.json).

Bütün çıktılar (Türkçe, Osmanlıca, iki dilli, asıllı EPUB) bu tek dosyadan üretilir.

{
  "surum": 1,
  "kunye": {"baslik": {"ar": "...", "tr": "...", "osm": "..."}, "yazar": {...},
            "asil_dil": "ar", "vefat_hicri": 505,
            "kaynak": {"tur": "openiti", "kimlik": "...", "adres": "...", "baski": "...", "lisans": "..."},
            "sayfa_kaynagi": "Beyrut 1993 baskısı"},
  "bloklar": [
     {"id": "b00001", "tur": "baslik", "seviye": 1, "metin": {"ar": "..."}},
     {"id": "b00002", "tur": "p", "metin": {"ar": "...", "tr": "...", "osm": "..."},
      "sayfalar": [{"no": "27", "konum": {"ar": 512}}],   # sayfa bu paragrafın içinde başlıyor
      "notlar": ["n0003"],                                 # paragraftaki dipnot atıfları (sırayla)
      "elle": {"tr": true},                                # elle düzeltildi: yeniden çeviri üzerine yazmaz
      "gecmis": [{"dil": "tr", "eski": "...", "zaman": 1760000000}]}
  ],
  "dipnotlar": {"n0003": {"metin": {"tr": "..."}}}
}

Dipnot atıfı metinde {{n0003}} işaretiyle durur; EPUB üretici bunu tıklanabilir nota çevirir.
Sayfa işaretinin "konum"u o dildeki karakter konumudur; bir dilde konum yoksa işaret paragraf başına konur.
"""
import json
import os
import re
import tempfile
import time

SURUM = 1
NOT_ISARETI = re.compile(r"\{\{(n\d{4,})\}\}")

# 0.5.52: seslendirmede okunmayacak parça (Dedplay Hazırlık'ın temiz EPUB'unda <span class="okunmaz" data-ses="yok">):
# blokta "ses_yok": {"tr": [{"once": "…", "metin": "…"}]} olarak saklanır (metin değişmez, bütün çıktılarda görünür);
# yalnız Stüdyo parçalarında \ue020…\ue021 ile işaretlenir, seslendirme (app/ses.ses_metni) bunu atlar, biçimler siler.
SES_AC, SES_KAPA = "\ue020", "\ue021"
_SES_PARCA = re.compile("\ue020([^\ue020\ue021]*)\ue021")


def _ses_sade(s):
    s = re.sub("\ue002[^\ue003]{0,20}\ue003", "", s or "")
    return re.sub(r"\s+", " ", NOT_ISARETI.sub("", s))


def ses_yok_ayir(metin):
    """İşaretli metin -> (işaretsiz metin, [{"once", "metin"}]). Bağlam ("once") parçanın önündeki son 30 harf."""
    if SES_AC not in (metin or ""):
        return metin, []
    metin = re.sub("\ue021(\\s*)\ue020", r"\1", metin)   # bitişik parçalar tek parça
    liste = []
    for m in _SES_PARCA.finditer(metin):
        parca = _ses_sade(m.group(1)).strip()
        if parca:
            once = _ses_sade(metin[:m.start()].replace(SES_AC, "").replace(SES_KAPA, "")).rstrip()
            liste.append({"once": once[-30:], "metin": parca})
    return metin.replace(SES_AC, "").replace(SES_KAPA, ""), liste


def ses_yok_isaretle(t, liste):
    """Stüdyo parçasının satırına (boşlukları sadeleşmiş blok metni) okunmaz işaretlerini koyar. Bulunamayan parça atlanır."""
    if not liste or not t:
        return t
    out, poz = [], 0
    for x in liste:
        s = x.get("metin") or ""
        adaylar, i = [], t.find(s, poz)
        while s and i >= 0:
            adaylar.append(i)
            i = t.find(s, i + 1)
        if not adaylar:
            continue
        once = (x.get("once") or "")[-20:]
        i = next((a for a in adaylar if t[:a].rstrip().endswith(once)), adaylar[0])
        out += [t[poz:i], SES_AC, s, SES_KAPA]
        poz = i + len(s)
    return "".join(out) + t[poz:]


def ses_isaretsiz(t):
    return (t or "").replace(SES_AC, "").replace(SES_KAPA, "")


def yeni(kunye):
    return {"surum": SURUM, "kunye": kunye, "bloklar": [], "dipnotlar": {}}


def blok_ekle(kitap, tur, metin, **kw):
    b = {"id": "b%05d" % (len(kitap["bloklar"]) + 1), "tur": tur, "metin": metin}
    b.update({k: v for k, v in kw.items() if v})
    kitap["bloklar"].append(b)
    return b


def diller(kitap):
    """Kitapta metni bulunan diller (blokların çoğunda dolu olanlar)."""
    say = {}
    ps = [b for b in kitap["bloklar"] if b["tur"] == "p" and not b.get("silindi")]  # silinen satırlar sayılmaz
    for b in ps:
        for d, t in b["metin"].items():
            if t and t.strip():
                say[d] = say.get(d, 0) + 1
    return [d for d, n in say.items() if n >= 0.9 * max(1, len(ps))]


def duzelt(kitap, blok_id, dil, yeni_metin):
    """Okuma ekranından gelen düzeltme: eski hâl geçmişe yazılır, 'elle' işaretlenir."""
    for b in kitap["bloklar"]:
        if b["id"] == blok_id:
            eski = b["metin"].get(dil, "")
            if eski == yeni_metin:
                return False
            b.setdefault("gecmis", []).append({"dil": dil, "eski": eski, "zaman": int(time.time())})
            b["metin"][dil] = yeni_metin
            b.setdefault("elle", {})[dil] = True
            return True
    raise KeyError(blok_id)


def blok_bul(kitap, blok_id):
    for b in kitap["bloklar"]:
        if b["id"] == blok_id:
            return b
    raise KeyError(blok_id)


def tur_degistir(kitap, blok_id, tur, seviye=None):
    """Paragraf <-> başlık (fihrist onarımı). Eski hâl geçmişe yazılır."""
    if tur not in ("p", "baslik"):
        raise ValueError("tür 'p' ya da 'baslik' olmalı")
    b = blok_bul(kitap, blok_id)
    seviye = min(max(int(seviye or 1), 1), 3) if tur == "baslik" else None
    if b["tur"] == tur and b.get("seviye") == seviye:
        return False
    b.setdefault("gecmis", []).append({"tur": b["tur"], "seviye": b.get("seviye"), "zaman": int(time.time())})
    b["tur"] = tur
    if seviye:
        b["seviye"] = seviye
    else:
        b.pop("seviye", None)
    return True


def sil(kitap, blok_id, silindi=True):
    """Blok silinmiş işaretlenir (kitaptan kalkmaz; geri alınabilir). EPUB'da görünmez."""
    b = blok_bul(kitap, blok_id)
    if bool(b.get("silindi")) == silindi:
        return False
    b.setdefault("gecmis", []).append({"silindi": bool(b.get("silindi")), "zaman": int(time.time())})
    if silindi:
        b["silindi"] = True
    else:
        b.pop("silindi", None)
    return True


def geri_al(kitap, blok_id):
    """Bloğun son değişikliğini geri alır (metin, tür ya da silme). Geri alınacak bir şey yoksa False."""
    b = blok_bul(kitap, blok_id)
    if not b.get("gecmis"):
        return False
    g = b["gecmis"].pop()
    if "dil" in g:
        b["metin"][g["dil"]] = g["eski"]
        if "osm_eski" in g:  # Türkçe düzeltmeyle otomatik yenilenen Osmanlıca da geri döner
            b["metin"]["osm"] = g["osm_eski"]
        if not any(x.get("dil") == g["dil"] for x in b["gecmis"]):
            b.get("elle", {}).pop(g["dil"], None)  # o dilde başka elle düzeltme kalmadı
    elif "tur" in g:
        b["tur"] = g["tur"]
        if g.get("seviye"):
            b["seviye"] = g["seviye"]
        else:
            b.pop("seviye", None)
    elif "silindi" in g:
        if g["silindi"]:
            b["silindi"] = True
        else:
            b.pop("silindi", None)
    if not b["gecmis"]:
        del b["gecmis"]
    if not b.get("elle"):
        b.pop("elle", None)
    return True


def gorunur(kitap):
    """EPUB ve okuma için görünür kopya: silinen bloklar çıkar, sayfa işaretleri sonraki bloğa geçer,
    görünür metinde atfı kalmayan dipnotlar düşer."""
    import copy
    k = copy.deepcopy(kitap)
    bloklar, tasinan = [], []
    for b in k["bloklar"]:
        if b.get("silindi"):
            tasinan += [{"no": s["no"], "konum": {d: 0 for d in (s.get("konum") or {"tr": 0})}} for s in b.get("sayfalar", [])]
            continue
        if tasinan:
            b["sayfalar"] = tasinan + b.get("sayfalar", [])
            tasinan = []
        bloklar.append(b)
    if tasinan and bloklar:
        bloklar[-1].setdefault("sayfalar", []).extend(tasinan)
    k["bloklar"] = bloklar
    atif = set()
    for b in bloklar:
        for t in b["metin"].values():
            atif |= set(NOT_ISARETI.findall(t or ""))
    k["dipnotlar"] = {g: n for g, n in k.get("dipnotlar", {}).items() if g in atif}
    return k


def kaydet(kitap, yol):
    """Önce geçici dosyaya yazılır, sonra yerine konur: yarıda kesilirse eski dosya bozulmaz."""
    klasor = os.path.dirname(os.path.abspath(yol))
    os.makedirs(klasor, exist_ok=True)
    fd, gecici = tempfile.mkstemp(dir=klasor, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(kitap, f, ensure_ascii=False, indent=1)
    os.replace(gecici, yol)


def yukle(yol):
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def denetle(kitap):
    """Yapısal hatalar listesi (boşsa kitap sağlam)."""
    hatalar = []
    idler = set()
    notlar_atif = []
    for b in kitap["bloklar"]:
        if b["id"] in idler:
            hatalar.append("tekrar eden blok kimliği: " + b["id"])
        idler.add(b["id"])
        if b["tur"] not in ("baslik", "p"):
            hatalar.append(f"{b['id']}: bilinmeyen tür {b['tur']}")
        if b["tur"] == "baslik" and not (1 <= b.get("seviye", 0) <= 6):
            hatalar.append(f"{b['id']}: başlık seviyesi hatalı")
        for d, t in b["metin"].items():
            notlar_atif += NOT_ISARETI.findall(t or "")
    for n in set(notlar_atif):
        if n not in kitap["dipnotlar"]:
            hatalar.append("atfı olan ama metni olmayan dipnot: " + n)
    for n in kitap["dipnotlar"]:
        if n not in notlar_atif:
            hatalar.append("metinde atfı olmayan dipnot: " + n)
    onceki = None
    for b in kitap["bloklar"]:
        for s in b.get("sayfalar", []):
            try:
                no = int(s["no"])
            except ValueError:
                continue  # roma rakamı vb.
            if onceki is not None and no <= onceki:
                hatalar.append(f"{b['id']}: sayfa sırası bozuk ({onceki} → {no})")
            onceki = no
    return hatalar
