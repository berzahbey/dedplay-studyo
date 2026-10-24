"""Metin kaynaklı kitapların (EPUB/DOCX/TXT) eski/yeni kodla karşılaştırması (0.5.46, ana metin planı adım 5).

uret: Stüdyo'daki her EPUB/DOCX/TXT kitabı kaynak dosyasından o anki kodla (OLCU_KOD) okur, <çıktı>/<kimlik>.json yazar. Kitaplara dokunmaz.
  docker run --rm -v "$PWD":/k:ro -v /DATA/AppData/dedplay-studyo/kutuphane:/data:ro -v /media/ZimaOS-HD/Kitap:/kaynak:ro \
    -v /DATA/AppData/dedplay-studyo/rapor:/rapor -e OLCU_KOD=/app ... python /k/araclar/kaynak_karsilastir.py uret /data/kitaplar /rapor/kk_eski
karsilastir: iki çıktıyı kitap kitap karşılaştırır. Düz dipnotlar (0.5.46) için ayrıca denetler: dipnot işaretleri ve not paragrafları
  çıkarıldıktan sonra metin aynı mı (yalnız notlar taşınmış olmalı), örnek bağlantılar.
  python araclar/kaynak_karsilastir.py karsilastir /rapor/kk_eski /rapor/kk_yeni
"""
import glob
import hashlib
import json
import os
import re
import sys
import time

NOT = re.compile(r"\{\{(n\d+)\}\}")
DUZ = re.compile(r"\s?\[\d{1,4}\]")
DUZ_BAS = re.compile(r"^\s*\[(\d{1,4})\]\s+(?=\S)")


def uret(kitaplar, cikti):
    sys.path.insert(0, os.environ.get("OLCU_KOD", "/app"))
    from kutuphane import kaynak as K
    os.makedirs(cikti, exist_ok=True)
    for j in sorted(glob.glob(os.path.join(kitaplar, "*", "kitap.json"))):
        kid = os.path.basename(os.path.dirname(j))
        yol = ((json.load(open(j, encoding="utf-8")).get("kunye") or {}).get("kaynak") or {}).get("yol") or ""
        if not yol.lower().endswith((".epub", ".docx", ".txt")):
            continue
        if not os.path.exists(yol):
            print(f"{kid}: kaynak yok ({yol})", flush=True)
            continue
        t0 = time.time()
        try:
            kit = K.cevir(yol)
        except Exception as e:
            print(f"{kid}: HATA {type(e).__name__}: {e}", flush=True)
            continue
        veri = json.dumps(kit, ensure_ascii=False).encode("utf-8")
        with open(os.path.join(cikti, kid + ".json"), "wb") as f:
            f.write(veri)
        print(f"{hashlib.md5(veri).hexdigest()}  {kid}  ({len(kit['bloklar'])} blok, {len(kit.get('dipnotlar') or {})} dipnot, "
              f"{time.time() - t0:.0f} sn)", flush=True)


def _metin(b):
    return (b.get("metin") or {}).get("tr") or next(iter((b.get("metin") or {}).values()), "")


def karsilastir(eski, yeni, ornek=int(os.environ.get("ORNEK", "4"))):
    for f in sorted(glob.glob(os.path.join(yeni, "*.json"))):
        kid = os.path.basename(f)[:-5]
        e_yol = os.path.join(eski, kid + ".json")
        if not os.path.exists(e_yol):
            print(f"== {kid}: eskisi yok")
            continue
        a, b = json.load(open(e_yol, encoding="utf-8")), json.load(open(f, encoding="utf-8"))
        if a == b:
            print(f"== {kid}: AYNI")
            continue
        da, db = a.get("dipnotlar") or {}, b.get("dipnotlar") or {}
        print(f"== {kid}: FARKLI | blok {len(a['bloklar'])} -> {len(b['bloklar'])} | dipnot {len(da)} -> {len(db)}")
        # yalnız notlar mı taşındı: eski metinden "[n] …" not paragrafları (yeni dipnot metniyle aynı olanlar) ve işaretler çıkarılınca aynı mı
        yeni_not = {re.sub(r"\s+", " ", (v.get("metin") or {}).get("tr", "") if isinstance(v, dict) else str(v)).strip()
                    for k, v in db.items() if k not in da}
        ea = []
        for x in a["bloklar"]:
            t = _metin(x)
            m = DUZ_BAS.match(t)
            if m and re.sub(r"\s+", " ", t[m.end():]).strip() in yeni_not:
                continue
            ea.append(re.sub(r"\s+", " ", DUZ.sub("", NOT.sub("", t))).strip())
        eb = [re.sub(r"\s+", " ", DUZ.sub("", NOT.sub("", _metin(x)))).strip() for x in b["bloklar"]]
        if ea == eb:
            print("   metin: notlar ve işaretler dışında AYNI")
        else:
            import difflib
            fark = [o for o in difflib.SequenceMatcher(None, ea, eb, autojunk=False).get_opcodes() if o[0] != "equal"]
            print(f"   metin: notlar dışında {len(fark)} yerde FARKLI")
            for op, i1, i2, j1, j2 in fark[:ornek]:
                print(f"     - {' / '.join(ea[i1:i2])[:200]}")
                print(f"     + {' / '.join(eb[j1:j2])[:200]}")
        n = 0
        for x in b["bloklar"]:
            t = _metin(x)
            for m in NOT.finditer(t):
                if m.group(1) in da or n >= ornek:
                    continue
                n += 1
                v = db[m.group(1)]
                v = (v.get("metin") or {}).get("tr", "") if isinstance(v, dict) else str(v)
                print(f"   bağlantı: …{t[max(0, m.start() - 90):m.start()]}[*]  →  {v[:120]}")
        # kaybolan metin: eski kitabın her paragrafı (işaretsiz) yeni kitabın metninde ya da dipnotlarında geçmeli
        dz = lambda s: re.sub(r"^[\s.,;:]+", "", re.sub(r"\s+", " ", DUZ.sub("", NOT.sub("", DUZ_BAS.sub("", s))))).strip()
        hepsi = " ".join([dz(_metin(x)) for x in b["bloklar"]] +
                         [dz((v.get("metin") or {}).get("tr", "") if isinstance(v, dict) else str(v)) for v in db.values()])
        kayip = [dz(_metin(x)) for x in a["bloklar"] if len(dz(_metin(x))) >= 15 and dz(_metin(x)) not in hepsi]
        print(f"   kaybolan paragraf: {len(kayip)}" + "".join(f"\n     ! {k[:150]}" for k in kayip[:ornek]))
        kalan = sum(1 for x in b["bloklar"] if DUZ_BAS.match(_metin(x)))
        print(f"   yeni kitapta '[n] …' ile başlayan paragraf: {kalan}")


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "uret":
        uret(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 4 and sys.argv[1] == "karsilastir":
        karsilastir(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
