"""0.5.23: Kitap raporu (ölçüm). Kitap işlenirken metinde yapılan her değişiklik (kelime onarımı, birleştirme), silinen
her şey (üst bilgi satırı, çöp paragraf, atılan sayfa, bağlanamayan dipnot) kaydedilir; iş bitince yapı denetimi
(numaralı başlıklarda eksik, sayfa numarasında atlama, dipnot işareti/metni eşleşmesi), şüpheli kelimeler ve şüpheli
paragraflarla birlikte kitabın klasörüne rapor.json + rapor.txt olarak yazılır. Metni DEĞİŞTİRMEZ, yalnız kaydeder.

Komutlar (konteynerde):
  python -m kutuphane.rapor toplu        bütün kitapların raporlarının özeti (tek metin)
  python -m kutuphane.rapor kuru [kid]   kuru deneme: kitapları yeni kodla yeniden işler (OCR önbellekten), hiçbir şeyi
                                         kaydetmez; raporu ve şimdiki kitapla farkı /data/kuru_deneme altına yazar
"""
import collections, difflib, json, os, re, sys, threading, time

_yerel = threading.local()
_SAYFA = re.compile("\ue002([^\ue003]{1,20})\ue003")
_NOT = re.compile(r"\{\{n\d{4,}\}\}")
_ARAP = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
_KELIME = re.compile(r"[^\W\d_]{2,}")
SURUM = 1


# ======================= kayıt (iş sürerken) =======================
def basla():
    _yerel.k = {"degisiklik": {}, "noktalama": 0, "silinen": collections.defaultdict(collections.Counter),
                "silinen_ornek": {}, "sayfa": None}
    _yerel.son = None


def _k():
    return getattr(_yerel, "k", None)


def _temiz(t):
    return re.sub(r"\s+", " ", _NOT.sub("", _SAYFA.sub(" ", t or ""))).strip()


def fark(once, sonra, yer="metin"):
    """Bir paragrafın önceki ve sonraki hâli: kelime düzeyindeki değişiklikler kaydedilir."""
    k = _k()
    if k is None or once == sonra:
        return
    a, b = once.split(), sonra.split()
    sayfalar = []  # her kelimeye kadar görülen son sayfa
    son = k["sayfa"]
    for t in a:
        for m in _SAYFA.finditer(t):
            son = m.group(1)
        sayfalar.append(son)
    for t in b:
        for m in _SAYFA.finditer(t):
            k["sayfa"] = m.group(1)
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        x, y = _temiz(" ".join(a[i1:i2])), _temiz(" ".join(b[j1:j2]))
        if x == y:
            continue
        if re.sub(r"[\W_]", "", x) == re.sub(r"[\W_]", "", y):  # yalnız boşluk/noktalama
            k["noktalama"] += 1
            continue
        if len(x) > 60 or len(y) > 60:
            x, y = x[:60] + "…", y[:60] + "…"
        anahtar = (x, y, yer)
        d = k["degisiklik"].setdefault(anahtar, {"adet": 0, "sayfa": sayfalar[i1] if i1 < len(sayfalar) else son,
                                                 "baglam": _temiz(" ".join(b[max(0, j1 - 5):j2 + 5]))[:160]})
        d["adet"] += 1


def silindi(tur, metin):
    """Metinden atılan bir şey (tür: 'üst/alt bilgi satırı', 'çöp paragraf', 'atılan sayfa', 'bağlanamayan dipnot' ...)."""
    k = _k()
    if k is None:
        return
    t = _temiz(metin)[:160]
    if t:
        k["silinen"][tur][t] += 1


def bitir(kit, bilgi=None, uzanti=""):
    """İş bitti: raporu oluşturur (iş parçacığına özel; depo `al` ile alır)."""
    k = _k()
    _yerel.k = None
    try:
        _yerel.son = olustur(kit, k or {}, bilgi or {}, uzanti)
    except Exception as e:  # rapor kitabın işlenmesini asla durdurmaz
        _yerel.son = {"hata": f"{type(e).__name__}: {e}"}
    return _yerel.son


def al():
    r = getattr(_yerel, "son", None)
    _yerel.son = None
    return r


# ======================= rapor =======================
def _dz():
    from app import duzelt as DZ
    return DZ


_gecerli_onbellek = {}


def _gecerli(w):
    if w not in _gecerli_onbellek:
        DZ = _dz()
        try:
            _gecerli_onbellek[w] = bool(DZ.gecerli_mi(w) or DZ._kelime_mi(w))
        except Exception:
            _gecerli_onbellek[w] = True
    return _gecerli_onbellek[w]


def _kucuk(w):
    return w.replace("I", "ı").replace("İ", "i").lower()


def _sayi(e):
    return int(e) if re.fullmatch(r"\d{1,4}", e or "") else None


def olustur(kit, k, bilgi, uzanti):
    ku = kit.get("kunye", {})
    bloklar = kit.get("bloklar", [])
    dil = ku.get("asil_dil", "tr")
    r = {"surum": SURUM, "tarih": int(time.time()),
         "kitap": {"ad": (ku.get("baslik") or {}).get("tr") or (ku.get("baslik") or {}).get(dil, ""),
                   "yazar": (ku.get("yazar") or {}).get("tr", ""), "kaynak": (ku.get("kaynak") or {}).get("ad", ""),
                   "tur": uzanti.lstrip(".") or "metin", "dil": dil},
         "cikarma": {"sayfa": bilgi.get("sayfa"), "ocr_sayfa": bilgi.get("ocr"), "ocr_motoru": bilgi.get("ocr_motoru"),
                     "bozuk_katman": bilgi.get("bozuk_katman"), "onarim": (ku.get("cikarma") or {}).get("onarim")}}
    metin = lambda b: (b.get("metin") or {}).get(dil) or (b.get("metin") or {}).get("tr") or ""
    paragraflar = [b for b in bloklar if b.get("tur") == "p"]
    basliklar = [b for b in bloklar if b.get("tur") == "baslik"]
    kelime = sum(len(_temiz(metin(b)).split()) for b in bloklar)
    r["ozet"] = {"paragraf": len(paragraflar), "baslik": len(basliklar), "kelime": kelime,
                 "dipnot": len(kit.get("dipnotlar") or {}),
                 "seviye": dict(collections.Counter(str(b.get("seviye", 1)) for b in basliklar))}
    # --- yapı denetimi ---
    yapi = {"basliklar": [[b.get("seviye", 1), _temiz(metin(b))[:90]] for b in basliklar][:400]}
    diziler = collections.defaultdict(list)  # "1. KUDSİ HADİS", "Birinci Söz" değil; yalnız rakamlı başlıklar
    for b in basliklar:
        m = re.match(r"^\s*(\d{1,3})\s*[.)\-–—:]?\s*(.*)$", _temiz(metin(b)))
        if m and m.group(2):
            anahtar = re.sub(r"[\W\d_]+", " ", m.group(2)).strip().lower()[:40]
            diziler[anahtar].append(int(m.group(1)))
    sorun = []
    for anahtar, nolar in diziler.items():
        if len(nolar) < 3:
            continue
        eksik = sorted(set(range(min(nolar), max(nolar) + 1)) - set(nolar))
        tekrar = sorted(n for n, c in collections.Counter(nolar).items() if c > 1)
        geri = sum(1 for x, y in zip(nolar, nolar[1:]) if y < x)
        if eksik or tekrar or geri:
            sorun.append({"dizi": anahtar, "adet": len(nolar), "aralik": [min(nolar), max(nolar)], "eksik": eksik[:50],
                          "tekrar": tekrar[:20], "geri_giden": geri})
    yapi["numarali_baslik_sorunlari"] = sorun
    yapi["numarali_baslik_dizileri"] = {a: len(n) for a, n in diziler.items() if len(n) >= 3}
    etiketler = [s.get("no") for b in bloklar for s in (b.get("sayfalar") or [])]
    sayilar = [_sayi(e) for e in etiketler if _sayi(e) is not None]
    atlama = [[x, y] for x, y in zip(sayilar, sayilar[1:]) if y != x + 1]
    yapi["sayfa"] = {"isaret": len(etiketler), "ilk": sayilar[0] if sayilar else None,
                     "son": sayilar[-1] if sayilar else None, "atlama": atlama[:40], "atlama_sayisi": len(atlama),
                     "sayisal_olmayan": [e for e in etiketler if _sayi(e) is None and not re.fullmatch(r"[ivxlcdm]{1,6}", e or "", re.I)][:20]}
    isaretler = [g for b in bloklar for g in re.findall(r"\{\{(n\d{4,})\}\}", metin(b))]
    dipnotlar = kit.get("dipnotlar") or {}
    yapi["dipnot"] = {"isaret": len(isaretler), "metin": len(dipnotlar),
                      "metni_olmayan_isaret": len([g for g in isaretler if g not in dipnotlar]),
                      "ayni_isaret_tekrar": len(isaretler) - len(set(isaretler))}
    # dipnota benzeyen gövde paragrafı ("12 Buhârî, Tevhîd, 35" / "1- Bk. ..."): dipnot gövdeye karışmış olabilir
    karisan = []
    for b in paragraflar:
        t = _temiz(metin(b))
        if re.match(r"^(\d{1,3}|\*)\s*[-.)]?\s+\S", t) and len(t) < 300 and \
                re.search(r"\b(bk\.|bkz\.|a\.g\.e|age\.|s\.\s*\d|c\.\s*\d|Buhârî|Buhari|Müslim|Tirmizî|Tirmizi|Ebû Dâvûd|Nesâî|İbn Mâce|Müsned|hadis no)", t, re.I):
            karisan.append(t[:140])
    yapi["dipnota_benzeyen_paragraf"] = karisan[:30]
    r["yapi"] = yapi
    # --- şüpheli kelimeler ve paragraflar (yalnız Türkçe kitapta) ---
    supheli, ornek, supheli_p = collections.Counter(), {}, []
    if dil == "tr":
        son_sayfa = None
        hepsi = [(b, "metin") for b in bloklar] + [({"metin": d.get("metin")}, "dipnot") for d in dipnotlar.values()]
        for sira, (b, yer) in enumerate(hepsi):
            ham = metin(b)
            for s in b.get("sayfalar") or []:
                son_sayfa = s.get("no") or son_sayfa
            t = _temiz(ham)
            kel = [w for w in _KELIME.findall(t) if not _ARAP.search(w)]
            gecersiz = [w for w in kel if not _gecerli(_kucuk(w))]
            for w in gecersiz:
                k2 = _kucuk(w)
                supheli[k2] += 1
                if k2 not in ornek:
                    i = t.find(w)
                    ornek[k2] = {"sayfa": son_sayfa, "baglam": t[max(0, i - 50):i + len(w) + 50]}
            harf = sum(1 for c in t if c.isalpha())
            dolu = len(re.sub(r"\s", "", t))
            if (len(kel) >= 2 and len(gecersiz) >= 0.6 * len(kel)) or (dolu >= 8 and harf < 0.6 * dolu and not _ARAP.search(t)):
                supheli_p.append({"sira": sira, "yer": yer, "sayfa": son_sayfa, "metin": t[:160]})
    r["supheli_kelime"] = [{"kelime": w, "adet": c, **ornek[w]} for w, c in supheli.most_common(400)]
    r["supheli_kelime_toplam"] = {"farkli": len(supheli), "gecis": sum(supheli.values())}
    r["supheli_paragraf"] = supheli_p[:80]
    # --- değişiklikler ve silinenler ---
    dg = sorted(((x, y, yer, d) for (x, y, yer), d in (k.get("degisiklik") or {}).items()), key=lambda t: -t[3]["adet"])
    r["degisiklik"] = [{"once": x, "sonra": y, "yer": yer, **d} for x, y, yer, d in dg[:1500]]
    r["degisiklik_toplam"] = {"farkli": len(dg), "gecis": sum(t[3]["adet"] for t in dg), "noktalama_bosluk": k.get("noktalama", 0)}
    r["silinen"] = {tur: [{"metin": t, "adet": c} for t, c in sayac.most_common(200)]
                    for tur, sayac in (k.get("silinen") or {}).items()}
    return r


def kaydet(klasor, rapor):
    if not rapor or not klasor:
        return
    os.makedirs(klasor, exist_ok=True)
    with open(os.path.join(klasor, "rapor.json.tmp"), "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=1)
    os.replace(os.path.join(klasor, "rapor.json.tmp"), os.path.join(klasor, "rapor.json"))
    with open(os.path.join(klasor, "rapor.txt"), "w", encoding="utf-8") as f:
        f.write(metin_hali(rapor))


# ======================= okunur metin =======================
def metin_hali(r, kisa=False):
    if r.get("hata"):
        return f"RAPOR HATASI: {r['hata']}\n"
    s = []
    ki, c, o = r["kitap"], r["cikarma"], r["ozet"]
    s.append(f"### {ki['ad']} — {ki['yazar']}  [{ki['tur']}, dil {ki['dil']}]  kaynak: {ki['kaynak']}")
    s.append(f"sayfa {c.get('sayfa')}, OCR sayfa {c.get('ocr_sayfa')} ({c.get('ocr_motoru') or '-'}), bozuk katman: {c.get('bozuk_katman')}, "
             f"onarım: {c.get('onarim')}")
    s.append(f"paragraf {o['paragraf']}, başlık {o['baslik']} (seviye {o['seviye']}), kelime {o['kelime']}, dipnot {o['dipnot']}")
    y = r["yapi"]
    s.append("-- Yapı")
    for d in y["numarali_baslik_sorunlari"]:
        s.append(f"  NUMARALI BAŞLIK '{d['dizi']}': {d['adet']} başlık {d['aralik']}, eksik {d['eksik']}, tekrar {d['tekrar']}, geri giden {d['geri_giden']}")
    if y["numarali_baslik_dizileri"]:
        s.append(f"  numaralı başlık dizileri: {y['numarali_baslik_dizileri']}")
    sy = y["sayfa"]
    s.append(f"  sayfa işareti {sy['isaret']} ({sy['ilk']}–{sy['son']}), atlama {sy['atlama_sayisi']}: {sy['atlama'][:15]}"
             + (f", sayısal olmayan: {sy['sayisal_olmayan']}" if sy["sayisal_olmayan"] else ""))
    dn = y["dipnot"]
    s.append(f"  dipnot işareti {dn['isaret']}, dipnot metni {dn['metin']}, metni olmayan işaret {dn['metni_olmayan_isaret']}, tekrar {dn['ayni_isaret_tekrar']}")
    for t in y["dipnota_benzeyen_paragraf"][:10 if kisa else 30]:
        s.append(f"  DİPNOTA BENZEYEN PARAGRAF: {t}")
    if not kisa:
        s.append("  başlıklar: " + " | ".join(f"{sv}:{t}" for sv, t in y["basliklar"][:120]))
    dt = r["degisiklik_toplam"]
    s.append(f"-- Değişiklikler: {dt['farkli']} farklı, {dt['gecis']} kez (ayrıca boşluk/noktalama {dt['noktalama_bosluk']})")
    for d in r["degisiklik"][:60 if kisa else 400]:
        s.append(f"  {d['adet']:4}  {d['once']}  ->  {d['sonra']}   [{d['yer']}, s.{d['sayfa']}]  « {d['baglam'][:100]} »")
    for tur, liste in r["silinen"].items():
        s.append(f"-- Silinen ({tur}): {sum(x['adet'] for x in liste)}")
        for x in liste[:15 if kisa else 60]:
            s.append(f"  {x['adet']:4}  {x['metin'][:140]}")
    st = r["supheli_kelime_toplam"]
    s.append(f"-- Şüpheli kelimeler (sözlükte yok): {st['farkli']} farklı, {st['gecis']} kez")
    for d in r["supheli_kelime"][:80 if kisa else 400]:
        s.append(f"  {d['adet']:4}  {d['kelime']}   [s.{d['sayfa']}]  « {d['baglam'][:110]} »")
    s.append(f"-- Şüpheli paragraflar: {len(r['supheli_paragraf'])}")
    for p in r["supheli_paragraf"][:20 if kisa else 80]:
        s.append(f"  #{p['sira']} [{p['yer']}, s.{p['sayfa']}]  {p['metin'][:140]}")
    return "\n".join(s) + "\n"


def _kitaplar_klasoru():
    return os.path.join(os.environ.get("DATA_DIR", "/data"), "kitaplar")


def toplu(klasor=None, kisa=True):
    """Bütün kitapların raporları: önce kitaplar arası ortak değişiklikler (aynı kural birçok kitabı etkiliyorsa), sonra
    her kitabın kısa raporu."""
    klasor = klasor or _kitaplar_klasoru()
    raporlar = []
    for kid in sorted(os.listdir(klasor)) if os.path.isdir(klasor) else []:
        yol = os.path.join(klasor, kid, "rapor.json")
        if os.path.exists(yol):
            try:
                raporlar.append((kid, json.load(open(yol, encoding="utf-8"))))
            except Exception:
                pass
    s = [f"DEDPLAY TOPLU RAPOR — {len(raporlar)} kitap — {time.strftime('%Y-%m-%d %H:%M')}"]
    ortak = collections.defaultdict(lambda: [0, set()])
    for kid, r in raporlar:
        for d in r.get("degisiklik", []):
            o = ortak[(d["once"], d["sonra"])]
            o[0] += d["adet"]
            o[1].add(kid)
    s.append("== Birden çok kitapta yapılan değişiklikler (kitap sayısı, toplam)")
    for (x, y), (n, kitaplar) in sorted(ortak.items(), key=lambda t: (-len(t[1][1]), -t[1][0]))[:150]:
        if len(kitaplar) >= 2:
            s.append(f"  {len(kitaplar):3} kitap {n:5}  {x}  ->  {y}")
    for kid, r in raporlar:
        s.append("")
        s.append(f"[{kid}]")
        s.append(metin_hali(r, kisa=kisa))
    return "\n".join(s) + "\n"


# ======================= kuru deneme =======================
def _kelime_farki(eski, yeni):
    c = collections.Counter()
    a, b = eski.split(), yeni.split()
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != "equal":
            x, y = _temiz(" ".join(a[i1:i2]))[:60], _temiz(" ".join(b[j1:j2]))[:60]
            if x != y:
                c[(x, y)] += 1
    return c


def kuru_deneme(kidler=None, cikti=None):
    """Kitapları kaynak dosyalarından yeni kodla yeniden işler; OCR yalnız önbellekten (önbellekte olmayan sayfa varsa
    kitap atlanır). Hiçbir kitaba yazmaz. Her kitap için rapor ve şimdiki kitap.json ile Türkçe metin farkı yazılır."""
    from kutuphane import kaynak, kitap as K
    klasor = _kitaplar_klasoru()
    cikti = cikti or os.path.join(os.environ.get("DATA_DIR", "/data"), "kuru_deneme")
    os.makedirs(cikti, exist_ok=True)
    ozet = [f"KURU DENEME — {time.strftime('%Y-%m-%d %H:%M')}"]
    for kid in sorted(kidler or os.listdir(klasor)):
        yol_k = os.path.join(klasor, kid, "kitap.json")
        if not os.path.exists(yol_k):
            continue
        try:
            eski = K.yukle(yol_k)
            kaynak_yol = ((eski.get("kunye") or {}).get("kaynak") or {}).get("yol")
            if not kaynak_yol or not os.path.exists(kaynak_yol):
                ozet.append(f"[{kid}] ATLANDI: kaynak dosya yok ({kaynak_yol})")
                continue
            if kaynak.ocr_gerekir(kaynak_yol):
                ozet.append(f"[{kid}] ATLANDI: OCR önbellekte değil (önce kitap bir kez işlenmeli)")
                continue
            bas = time.time()
            yeni = kaynak.cevir(kaynak_yol, None, {"yol": kaynak_yol})
            # 0.5.30: "python -m kutuphane.rapor" bu dosyayı __main__ olarak da yükler; kaynak.py raporu
            # kutuphane.rapor'a yazar: oradan alınır (eskiden boş kalıyor, fark.txt yazılamıyordu)
            from kutuphane import rapor as _R
            rapor = _R.al() or {}
            hedef = os.path.join(cikti, kid)
            os.makedirs(hedef, exist_ok=True)
            kaydet(hedef, rapor)
            dil = (yeni.get("kunye") or {}).get("asil_dil", "tr")
            tm = lambda kit: "\n".join(_temiz((b.get("metin") or {}).get(dil) or (b.get("metin") or {}).get("tr") or "")
                                       for b in kit.get("bloklar", []))
            fark_c = _kelime_farki(tm(eski), tm(yeni))
            satir = [f"[{kid}] {time.time() - bas:.0f} sn, şimdiki kitapla {sum(fark_c.values())} kelime farkı"]
            for (x, y), n in fark_c.most_common(60):
                satir.append(f"  {n:4}  {x or '∅'}  ->  {y or '∅'}")
            with open(os.path.join(hedef, "fark.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join([satir[0]] + [f"  {n:4}  {x or '∅'}  ->  {y or '∅'}" for (x, y), n in fark_c.most_common()]) + "\n")
            ozet += satir
            print(satir[0], file=sys.stderr, flush=True)
        except Exception as e:
            ozet.append(f"[{kid}] HATA: {type(e).__name__}: {str(e)[:200]}")
            print(ozet[-1], file=sys.stderr, flush=True)
    metin = "\n".join(ozet) + "\n"
    with open(os.path.join(cikti, "ozet.txt"), "w", encoding="utf-8") as f:
        f.write(metin)
    with open(os.path.join(cikti, "toplu.txt"), "w", encoding="utf-8") as f:
        f.write(toplu(cikti))
    return metin


if __name__ == "__main__":
    komut = sys.argv[1] if len(sys.argv) > 1 else "toplu"
    if komut == "toplu":
        sys.stdout.write(toplu(kisa="--uzun" not in sys.argv))
    elif komut == "kuru":
        sys.stdout.write(kuru_deneme([a for a in sys.argv[2:] if not a.startswith("-")] or None))
    else:
        sys.exit("kullanım: python -m kutuphane.rapor toplu [--uzun] | kuru [kitap kimliği ...]")
