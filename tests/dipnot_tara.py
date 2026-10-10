"""0.5.35 taraması (salt okur): önbellekteki bütün Surya sayfalarında dipnot kararı eski (imaj, /app) ve yeni (/k) kodla."""
import glob, json, os, shutil, sys, types
shutil.rmtree("/tmp/yeni", ignore_errors=True)
shutil.copytree("/k/kutuphane", "/tmp/yeni/kutuphane_yeni")
sys.path[:0] = ["/app", "/tmp/yeni"]
from kutuphane import kaynak as ESKI
from kutuphane_yeni import kaynak as YENI
print("eski:", ESKI.__file__, "| yeni:", YENI.__file__, "| yeni kural:", hasattr(YENI, "_satir_araligi"), hasattr(ESKI, "_satir_araligi"))
toplam_s = toplam_d = 0
for kl in sorted(glob.glob("/data/ocr_onbellek/*/")):
    dos = sorted(glob.glob(kl + "s*.json"))
    if not dos:
        continue
    ad = open(kl + "kaynak.txt", encoding="utf-8").read().strip() if os.path.exists(kl + "kaynak.txt") else kl
    ham = []
    for f in dos:
        try:
            ham.append((f, json.load(open(f, encoding="utf-8"))["satirlar"]))
        except Exception:
            pass
    alt = max((b[3] for _, s in ham for _, b in s), default=2339)
    h = alt * 72 / 200 * 1.04
    sayfalar = []
    for f, s in ham:
        rows = YENI._surya_satirlari([types.SimpleNamespace(text=t, bbox=b) for t, b in s], 72 / 200, None)
        sayfalar.append((f, YENI._sayfa_no_ve_kenar(rows, h)[1]))
    temiz = YENI._tekrar_edenleri_at([r for _, r in sayfalar])
    g = YENI._govde_boyu(temiz, True) or 11
    degisen = []
    for (f, _), rows in zip(sayfalar, temiz):
        a1, d1 = ESKI._dipnot_ayir(rows, h, g)
        a2, d2 = YENI._dipnot_ayir(rows, h, g)
        if len(d1) != len(d2):
            degisen.append((os.path.basename(f)[1:5].lstrip("0"), len(rows), a1, d1, a2, d2))
    toplam_s += len(sayfalar); toplam_d += len(degisen)
    print(f"\n=== {ad} | {len(sayfalar)} sayfa | gövde {g:.1f} | değişen {len(degisen)}")
    for p, n, a1, d1, a2, d2 in degisen[:15]:
        print(f"  s.{p} ({n} satır): dipnot {len(d1)} -> {len(d2)} satır")
        ilk = (d2 or d1)
        sinir = (a2 if len(d2) > len(d1) else a1)
        print(f"     gövdenin son satırı: {sinir[-1]['text'][:75] if sinir else '-'}")
        fark = [r for r in (d2 if len(d2) > len(d1) else d1) if r not in (d1 if len(d2) > len(d1) else d2)]
        print(f"     {'dipnota geçen' if len(d2) > len(d1) else 'gövdeye dönen'} ilk satır: {fark[0]['text'][:75] if fark else '-'}")
    if len(degisen) > 15:
        print(f"  … ve {len(degisen) - 15} sayfa daha")
print(f"\nTOPLAM: {toplam_s} sayfa, {toplam_d} sayfada karar değişti")
