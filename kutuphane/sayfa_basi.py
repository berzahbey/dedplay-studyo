"""0.5.88: sayfa başı temizliği (Zahir, 23 Kasım: "seslendirmede sayfa numaraları ve başlıklar cümlenin içine giriyor").

Taranmış kitaplarda her sayfanın başındaki sütun başlığı ("ÖNSÖZ", "EL-MEDİNETÜ'L FÂZILA") ve sayfa numarası ("16 olunca da") bazen
satır olarak ayrılamayıp paragrafın başına yapışır. kitap.json'da sayfa sınırları işaretli (blok["sayfalar"]: no + konum), bu adım:
  1. Sayfa başında o sayfanın numarası duruyorsa siler ("16 olunca da" -> "olunca da").
  2. Sayfa başında büyük harfli bir başlık duruyorsa ve aynı başlık (OCR farkıyla) en az 3 sayfanın başında geçiyorsa ya da kitabın
     adına / bir bölüm başlığına benziyorsa siler. Yalnız başlıktan ibaret paragraf tamamen silinir.
  3. Böylece sayfa sınırında bölünmüş cümle yeniden birleşir: önceki paragraf cümle sonu işaretiyle bitmiyor ve sonraki küçük harfle
     başlıyorsa iki paragraf birleştirilir.
Bütün kitaplara aynı kural. Silinenler ve birleştirmeler kitap klasöründe sayfa_basi.txt'ye yazılır. STUDYO_SAYFA_BASI=0 kapatır."""
import collections
import difflib
import os
import re

_BUYUK = re.compile(r"^\s*((?:[^\s]*[A-ZÇĞİÖŞÜÂÎÛ][^\s]*\s*){1,6})")
_HARF = re.compile(r"[^\W\d_]")


def acik() -> bool:
    return os.environ.get("STUDYO_SAYFA_BASI", "1") != "0"


def _buyuk_onek(t):
    """Metnin başındaki büyük harfli kelimeler (her kelimenin harflerinin en az %75'i büyük; OCR'ın küçük harfi: MEDtNETÜ)."""
    kelimeler = []
    i = 0
    for m in re.finditer(r"\S+", t):
        w = m.group(0)
        harf = _HARF.findall(w)
        if not harf:
            if kelimeler and w in ("-", "–"):
                continue
            break
        buyuk = sum(1 for h in harf if h.isupper())
        if buyuk / len(harf) < 0.75 or (len(harf) == 1 and not kelimeler):
            break
        kelimeler.append(w)
        i = m.end()
        if len(kelimeler) >= 6:
            break
    return (t[:i], i) if kelimeler and len(" ".join(kelimeler)) >= 3 else ("", 0)


def _anahtar(s):
    s = s.replace("I", "ı").replace("İ", "i").lower().translate(str.maketrans("âîûı", "aiui"))
    return re.sub(r"[^a-zçğöşü]", "", s)


def _icinde(a, x):
    """a'nın x içinde (OCR farkıyla) geçmesi: x'in a uzunluğundaki parçalarından birine en az %80 benzerlik."""
    x = _anahtar(x)
    if not a or len(x) < len(a):
        return False
    return max(difflib.SequenceMatcher(None, a, x[i:i + len(a)]).ratio() for i in range(len(x) - len(a) + 1)) >= 0.8


def _benzer(a, b):
    return difflib.SequenceMatcher(None, _anahtar(a), _anahtar(b)).ratio()


def temizle(kit, klasor=None):
    if not acik():
        return {}
    bloklar = kit.get("bloklar", [])
    basliklar = [b["metin"].get("tr", "") for b in bloklar if b.get("tur") == "baslik"]
    kitap_adi = (kit.get("kunye", {}).get("baslik") or {}).get("tr", "")
    # sayfa başlarındaki büyük harfli önekler
    onekler = []
    for b in bloklar:
        if b.get("tur") == "baslik":
            continue
        t = b["metin"].get("tr", "")
        for s in b.get("sayfalar", []):
            k = s.get("konum", {}).get("tr", 0)
            on, _ = _buyuk_onek(re.sub(r"^\s*\d{1,4}\s+", "", t[k:k + 120]))
            if on:
                onekler.append(on.strip())
    sik = []
    for o in onekler:
        if sum(1 for p in onekler if _benzer(o, p) >= 0.75) >= 3:
            sik.append(o)

    def baslik_mi(on):
        if any(_benzer(on, s) >= 0.75 for s in sik):
            return True
        aday = [kitap_adi] + basliklar
        a = _anahtar(on)
        return len(a) >= 4 and any(_benzer(on, x) >= 0.8 or (len(a) >= 6 and _icinde(a, x)) for x in aday if x)

    silinen = collections.Counter()
    # 0.5.92 (İdeal Devlet: "26 oldukça ona daha çok yaklaşırız"): sayfa bir başlıkla başlıyorsa sayfa işareti başlıkta kalır, OCR'ın
    # sayfa numarası satırı başlıktan sonraki paragrafın başına düşer. Başlığın sayfa numarasıyla başlayan sonraki paragraftan silinir.
    for i, b in enumerate(bloklar[:-1]):
        if b.get("tur") != "baslik" or not b.get("sayfalar"):
            continue
        nolar = {str(s.get("no")) for s in b["sayfalar"]}
        n = bloklar[i + 1]
        if n.get("tur") != "p" or (n.get("elle") or {}).get("tr"):
            continue
        t = n["metin"].get("tr", "")
        m = re.match(r"\s*(\d{1,4})\s+(?=\S)", t)
        if not m or m.group(1) not in nolar or (n.get("sayfalar") and n["sayfalar"][0].get("konum", {}).get("tr", 1) == 0):
            continue
        n["metin"]["tr"] = t[m.end():]
        for s2 in n.get("sayfalar", []):
            s2["konum"]["tr"] = max(0, s2.get("konum", {}).get("tr", 0) - m.end())
        silinen[f"sayfa numarası {m.group(1)} (başlıktan sonra)"] += 1
    for b in bloklar:
        if b.get("tur") == "baslik" or not b.get("sayfalar") or (b.get("elle") or {}).get("tr"):
            continue
        t = b["metin"].get("tr", "")
        # sondan başa: konumlar kaymasın
        for s in sorted(b["sayfalar"], key=lambda s: -s.get("konum", {}).get("tr", 0)):
            k = s.get("konum", {}).get("tr", 0)
            parca = t[k:]
            kes = 0
            m = re.match(r"\s*(\d{1,4})(?=\s|$)", parca)
            if m and m.group(1) == str(s.get("no")):
                kes = m.end()
                silinen[f"sayfa numarası {m.group(1)}"] += 1
            on, son = _buyuk_onek(parca[kes:])
            if on and baslik_mi(on.strip()):
                silinen[on.strip()] += 1
                kes += son
            if kes:
                while kes < len(parca) and parca[kes] == " ":
                    kes += 1
                t = t[:k] + parca[kes:]
                fark = kes
                for s2 in b["sayfalar"]:
                    k2 = s2.get("konum", {}).get("tr", 0)
                    if k2 > k:
                        s2["konum"]["tr"] = k2 - fark
        b["metin"]["tr"] = t
    # yalnız başlıktan ibaret kalan (boş) paragraflar ve sayfa sınırında bölünmüş paragraflar
    yeni = []
    birlesen = 0
    for b in bloklar:
        t = b["metin"].get("tr", "")
        if b.get("tur") != "baslik" and b["metin"].get("tr") is not None and not t.strip():
            if yeni and b.get("sayfalar"):          # sayfa işareti önceki paragrafın sonuna taşınır
                o = yeni[-1]
                for s in b["sayfalar"]:
                    s["konum"]["tr"] = len(o["metin"].get("tr", ""))
                    o.setdefault("sayfalar", []).append(s)
            continue
        if yeni and b.get("tur") == "p" and yeni[-1].get("tur") == "p" and b.get("sayfalar") \
                and not (b.get("elle") or {}).get("tr") and not (yeni[-1].get("elle") or {}).get("tr") \
                and b["sayfalar"][0].get("konum", {}).get("tr", 1) == 0:
            o = yeni[-1]
            ot = o["metin"].get("tr", "").rstrip()
            if ot and not re.search(r"[.!?:;…\"”’»)\]]$", ot) and re.match(r"[a-zçğıöşüâîû]", t.lstrip()):
                bos = 0 if ot.endswith("-") else 1
                ot = ot[:-1] if ot.endswith("-") else ot
                taban = len(ot) + bos
                o["metin"]["tr"] = ot + (" " if bos else "") + t.lstrip()
                for s in b.get("sayfalar", []):
                    s["konum"]["tr"] = s.get("konum", {}).get("tr", 0) + taban
                    o.setdefault("sayfalar", []).append(s)
                birlesen += 1
                continue
        yeni.append(b)
    kit["bloklar"] = yeni
    ozet = {"silinen": sum(silinen.values()), "birlesen": birlesen}
    kit.setdefault("kunye", {})["sayfa_basi"] = ozet
    if klasor:
        try:
            with open(os.path.join(klasor, "sayfa_basi.txt"), "w", encoding="utf-8") as f:
                f.write(f"Sayfa başı temizliği: {ozet['silinen']} silinen, {birlesen} paragraf birleştirildi\n")
                for w, n in silinen.most_common():
                    f.write(f"{n}\t{w}\n")
        except OSError:
            pass
    return ozet
