"""Altın çıktı (11 Ekim kararı, 1-kutuphane.md açık iş 19).

Bütün kitaplar kaynak dosyalarından kodla yeniden işlenir (kuru deneme gibi: OCR yalnız önbellekten, hiçbir kitaba
yazılmaz) ve her kitap tek bir düz metin dosyasına dökülür: künye, başlıklar (seviyesiyle), paragraflar, sayfa
işaretleri ve her paragrafın dipnotları hemen altında. Dipnot kimlikleri (n0005) yazılmaz: bir dipnot eklenince
sonrakilerin hepsi fark gibi görünmesin. Bir yama derlenmeden önce yamalı kodla yeniden üretilir ve altınla
karşılaştırılır; beklenmeyen her değişiklik açıklanır. Kabul edilince yeni çıktı altın olur.

Komutlar:
  python -m kutuphane.altin uret <klasör> [kimlik ...]           kitapları işler, <klasör>/<kimlik>.txt yazar
  python -m kutuphane.altin karsilastir <altın> <yeni> [<rapor>]  farkları yazar (<rapor>/ozet.txt, <kimlik>.txt)
"""
import collections, difflib, os, re, sys, time

_NOT = re.compile(r"\{\{(n\d{4,})\}\}")
_SAYFA_IC = re.compile("\ue002([^\ue003]{1,20})\ue003")
_BOSLUK = re.compile(r"\s+")


def _tek(t):
    return _BOSLUK.sub(" ", t or "").strip()


def _metin(b, dil):
    m = b.get("metin") or {}
    return m.get(dil) or m.get("tr") or ""


def _sayfali(t, sayfalar, dil):
    """Paragrafın sayfa işaretleri yerlerine ⟦no⟧ olarak konur (konum yoksa paragraf başına)."""
    yerler = []
    for s in sayfalar or []:
        k = (s.get("konum") or {}).get(dil)
        yerler.append((k if isinstance(k, int) and 0 <= k <= len(t) else 0, str(s.get("no"))))
    for k, no in sorted(yerler, key=lambda x: -x[0]):
        t = t[:k] + "⟦" + no + "⟧" + t[k:]
    return _SAYFA_IC.sub(lambda m: "⟦" + m.group(1) + "⟧", t)


def dok(kit):
    """kitap sözlüğü -> satır listesi. Satır başı türü verir: K (künye), B1-B3 (başlık), P (paragraf), N (dipnot),
    Y (hiçbir paragrafa bağlı olmayan dipnot)."""
    kn = kit.get("kunye") or {}
    dil = kn.get("asil_dil") or "tr"
    s = [f"K| başlık: {_tek((kn.get('baslik') or {}).get('tr') or (kn.get('baslik') or {}).get(dil))}",
         f"K| yazar: {_tek((kn.get('yazar') or {}).get('tr') or (kn.get('yazar') or {}).get(dil))}",
         f"K| dil: {dil}"]
    notlar = kit.get("dipnotlar") or {}
    kullanilan = set()
    for b in kit.get("bloklar", []):
        if b.get("silindi"):
            continue
        t = _metin(b, dil)
        ids = _NOT.findall(t)
        t = _tek(_NOT.sub("[*]", _sayfali(t, b.get("sayfalar"), dil)))
        if b.get("tur") == "baslik":
            s.append(f"B{b.get('seviye') or 1}| {t}")
        else:
            s.append(f"P| {t}")
        for n in ids + [x for x in (b.get("notlar") or []) if x not in ids]:
            if n in kullanilan:
                continue
            kullanilan.add(n)
            s.append(f"N| {_tek(_NOT.sub('[*]', _metin(notlar.get(n) or {}, dil)))}" if n in notlar else f"N| (metni yok: {n})")
    for n in sorted(notlar):
        if n not in kullanilan:
            s.append(f"Y| {_tek(_metin(notlar[n], dil))}")
    return s


# ======================= üretme =======================
def uret(cikti, kidler=None):
    from kutuphane import kaynak, kitap as K, rapor as R
    klasor = R._kitaplar_klasoru()
    os.makedirs(cikti, exist_ok=True)
    try:  # main.py içeri alınmaz (uygulamayı kurar): sürüm dosyadan okunur
        with open(os.path.join(os.path.dirname(os.path.abspath(kaynak.__file__)), "main.py"), encoding="utf-8") as f:
            SURUM = re.search(r'^SURUM\s*=\s*"([^"]+)"', f.read(), re.M).group(1)
    except Exception:
        SURUM = "?"
    ozet = [f"ALTIN ÇIKTI — {time.strftime('%Y-%m-%d %H:%M')} — sürüm {SURUM} — kod {os.path.dirname(os.path.dirname(os.path.abspath(kaynak.__file__)))}"]
    for kid in sorted(kidler or os.listdir(klasor)):
        yol_k = os.path.join(klasor, kid, "kitap.json")
        if not os.path.exists(yol_k):
            continue
        try:
            eski = K.yukle(yol_k)
            ky = ((eski.get("kunye") or {}).get("kaynak") or {}).get("yol")
            if not ky or not os.path.exists(ky):
                ozet.append(f"[{kid}] ATLANDI: kaynak dosya yok ({ky})")
                continue
            if kaynak.ocr_gerekir(ky):
                ozet.append(f"[{kid}] ATLANDI: OCR önbellekte değil")
                continue
            bas = time.time()
            yeni = kaynak.cevir(ky, None, {"yol": ky})
            satirlar = dok(yeni)
            gecici = os.path.join(cikti, kid + ".txt.yaziliyor")
            with open(gecici, "w", encoding="utf-8") as f:
                f.write("\n".join(satirlar) + "\n")
            os.replace(gecici, os.path.join(cikti, kid + ".txt"))
            say = collections.Counter(x[:1] for x in satirlar)
            ozet.append(f"[{kid}] {time.time() - bas:.0f} sn: {say['B']} başlık, {say['P']} paragraf, {say['N'] + say['Y']} dipnot")
        except Exception as e:
            ozet.append(f"[{kid}] HATA: {type(e).__name__}: {str(e)[:200]}")
        print(ozet[-1], file=sys.stderr, flush=True)
    metin = "\n".join(ozet) + "\n"
    with open(os.path.join(cikti, "_ozet.txt"), "w", encoding="utf-8") as f:
        f.write(metin)
    return metin


# ======================= karşılaştırma =======================
_TUR = {"K": "künye", "B": "başlık", "P": "gövde", "N": "dipnot", "Y": "dipnot"}


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read().split("\n")[:-1]


def _yazi(satir):
    return satir.split("| ", 1)[1] if "| " in satir else satir


def _son_sayfa(satirlar, i):
    for j in range(min(i, len(satirlar) - 1), -1, -1):
        m = re.findall("⟦([^⟧]+)⟧", satirlar[j])
        if m:
            return m[-1]
    return "?"


def _kelime_farklari(a, b):
    """İki satırın kelime farkları: [(eski, yeni, bağlam)]."""
    x, y = a.split(), b.split()
    cikti = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, x, y, autojunk=False).get_opcodes():
        if op != "equal":
            baglam = " ".join(x[max(0, i1 - 4):i1] + ["«" + " ".join(x[i1:i2]) + "»"] + x[i2:i2 + 4])
            cikti.append((" ".join(x[i1:i2]), " ".join(y[j1:j2]), baglam))
    return cikti


def kitap_farki(eski, yeni):
    """İki dökümün farkı: (sayaç {tür: adet}, satırlar, kelime çiftleri sayacı)."""
    say, satir, cift = collections.Counter(), [], collections.Counter()
    sm = difflib.SequenceMatcher(None, eski, yeni, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        a, b = eski[i1:i2], yeni[j1:j2]
        sayfa = _son_sayfa(eski, i1)
        # aynı türden, aynı sayıda satır: satır satır kelime farkı
        if op == "replace" and len(a) == len(b) and all(p[:1] == q[:1] for p, q in zip(a, b)):
            for p, q in zip(a, b):
                tur = _TUR.get(p[:1], "?")
                pm, qm = _yazi(p), _yazi(q)
                if p[:1] == "B" and p[:2] != q[:2]:
                    say["başlık seviyesi"] += 1
                    satir.append(f"  [s.{sayfa}] başlık seviyesi: {p[:2]} -> {q[:2]}  « {pm[:100]} »")
                    if pm == qm:
                        continue
                if tur == "gövde" and re.sub("⟦[^⟧]*⟧", "", pm) == re.sub("⟦[^⟧]*⟧", "", qm):
                    tur = "sayfa işareti"
                for x, y, bg in _kelime_farklari(pm, qm):
                    say[tur] += 1
                    cift[(tur, x[:60], y[:60])] += 1
                    satir.append(f"  [s.{sayfa}] {tur}: {x or '∅'}  ->  {y or '∅'}   « {bg[:140]} »")
            continue
        for p in a:
            say[_TUR.get(p[:1], "?") + " satırı gitti"] += 1
            satir.append(f"  [s.{sayfa}] - {p[:200]}")
        for q in b:
            say[_TUR.get(q[:1], "?") + " satırı geldi"] += 1
            satir.append(f"  [s.{sayfa}] + {q[:200]}")
    return say, satir, cift


def karsilastir(altin, yeni, rapor=None):
    for k in (altin, yeni):  # üretimi bitmemiş klasör karşılaştırılmaz (_ozet.txt en son yazılır)
        if not os.path.exists(os.path.join(k, "_ozet.txt")):
            return f"HATA: {k} içinde _ozet.txt yok: üretim bitmemiş ya da yarıda kalmış (docker ps ile bakın)\n"
    rapor = rapor or os.path.join(os.path.dirname(os.path.abspath(yeni)), "altin_fark")
    os.makedirs(rapor, exist_ok=True)
    ka = {f[:-4] for f in os.listdir(altin) if f.endswith(".txt") and not f.startswith("_")}
    ky = {f[:-4] for f in os.listdir(yeni) if f.endswith(".txt") and not f.startswith("_")}
    ozet = [f"ALTIN KARŞILAŞTIRMA — {time.strftime('%Y-%m-%d %H:%M')}", f"altın: {altin}", f"yeni:  {yeni}", ""]
    aynı = degisen = 0
    toplu = collections.Counter()
    for kid in sorted(ka | ky):
        if kid not in ky:
            ozet.append(f"[{kid}] YENİDE YOK (atlandı ya da hata: yeni klasördeki _ozet.txt)")
            continue
        if kid not in ka:
            ozet.append(f"[{kid}] ALTINDA YOK (yeni kitap)")
            continue
        e, y = _oku(os.path.join(altin, kid + ".txt")), _oku(os.path.join(yeni, kid + ".txt"))
        if e == y:
            aynı += 1
            continue
        degisen += 1
        say, satir, cift = kitap_farki(e, y)
        toplu.update(cift)
        ozet.append(f"[{kid}] " + ", ".join(f"{k} {n}" for k, n in sorted(say.items())))
        with open(os.path.join(rapor, kid + ".txt"), "w", encoding="utf-8") as f:
            f.write(f"[{kid}]\n" + "\n".join(satir) + "\n")
    ozet.insert(4, f"aynı {aynı} kitap, değişen {degisen} kitap")
    ozet.insert(5, "")
    ortak = [(k, n) for k, n in toplu.most_common() if n >= 2]
    if ortak:
        ozet += ["", "-- En sık değişiklikler (bütün kitaplar):"]
        ozet += [f"  {n:4}  {t}: {x or '∅'}  ->  {y or '∅'}" for (t, x, y), n in ortak[:80]]
    metin = "\n".join(ozet) + "\n"
    with open(os.path.join(rapor, "ozet.txt"), "w", encoding="utf-8") as f:
        f.write(metin)
    return metin


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["uret"] and len(a) >= 2:
        sys.stdout.write(uret(a[1], a[2:] or None))
    elif a[:1] == ["karsilastir"] and len(a) >= 3:
        sys.stdout.write(karsilastir(a[1], a[2], a[3] if len(a) > 3 else None))
    else:
        sys.exit(__doc__)
