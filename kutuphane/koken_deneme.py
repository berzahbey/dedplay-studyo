"""0.5.82: köken modeli sınavı. Bilinen cevaplı 119 kelime (55 Arapça ekli kelime: kök yazımı Hayrat'tan; 12 Farsça; 37 Türkçe —
Lite'ın Arapça sandığı gerek/değer/getir ve modern kelimeler; 15 Batı dili) köken adımının AYNI istemiyle modele sorulur.
Kullanım (stüdyo konteynerinde):
  python -m kutuphane.koken_deneme --liste [arama]          NVIDIA hesabındaki model adları (ör. --liste deepseek)
  python -m kutuphane.koken_deneme nvidia:<model> [gemini:<model> ...]
Çıktı: köken doğruluğu (Türkçe / Arapça-Farsça / Batı ayrı), Arapça-Farsça kök yazımı doğruluğu, yanlışlar."""
import json, os, re, sys, time, unicodedata
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import requests
from kutuphane import koken, nvidia, yz

VERI = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "koken_deneme.json"), encoding="utf-8"))


def n(s):
    s = (s or "").strip().replace("ة", "ه").replace("ي", "ی").replace("ى", "ی").replace("ك", "ك").replace("ک", "ك") \
        .replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("‌", "")
    s = "".join(c for c in s if not unicodedata.category(c).startswith("M"))
    if s.startswith("ال") and len(s) > 4:
        s = s[2:]
    return s[:-1] if s.endswith("اء") else s


def sor(saglayici, model, kelimeler):
    kullanici = "KÖKEN GÖREVİ\n" + "\n".join(f"{i}. {w}" for i, w in enumerate(kelimeler, 1))
    if saglayici == "nvidia":
        n = nvidia.Nvidia(model)
        cevap, ad = n.sor(koken.SISTEM, kullanici, en_fazla=6000)
        if not koken.cevaplari_coz(kelimeler, cevap, ad):
            print(f"  (cevapsız parti: bitiş {n.son_bitis or '?'}, {len(cevap or '')} karakter, başı: {(cevap or '')[:120]!r})")
        return cevap, ad
    g = yz.Gemini(lambda m: None)
    g.zaman, g.deneme, g.json_kipi, g.liste = 240, 5, False, [model]
    return g.sor(koken.SISTEM, kullanici, en_fazla=6000)


def sinav(ad):
    saglayici, model = ad.split(":", 1)
    kel = [v["kelime"] for v in VERI]
    t0 = time.time()
    cevaplar = {}
    for i in range(0, len(kel), 60):      # 60'lık iki grup (köken adımı 100'lük gönderir)
        cevap, _ = sor(saglayici, model, kel[i:i + 60])
        for r in koken.cevaplari_coz(kel[i:i + 60], cevap, ad):
            cevaplar[r["kelime"]] = r
    sure = time.time() - t0
    say = {"tr": [0, 0], "arfa": [0, 0], "bati": [0, 0], "yazim": [0, 0], "cevapsiz": 0}
    yanlis = []
    for v in VERI:
        r = cevaplar.get(v["kelime"])
        if not r:
            say["cevapsiz"] += 1
            continue
        k = r["koken"]
        if v["koken"] == "tr":
            say["tr"][1] += 1; ok = k == "tr"; say["tr"][0] += ok
        elif v["koken"] in ("ar", "fa"):
            say["arfa"][1] += 1; ok = k in ("ar", "fa"); say["arfa"][0] += ok
            if ok:
                say["yazim"][1] += 1
                yok = n(r["yazilis"]) == n(v["yazilis"])
                say["yazim"][0] += yok
                if not yok:
                    yanlis.append(f'yazım  {v["kelime"]}: {r["yazilis"]} (doğrusu {v["yazilis"]})')
        else:
            say["bati"][1] += 1; ok = k not in ("tr", "ar", "fa"); say["bati"][0] += ok
        if not ok:
            yanlis.append(f'köken  {v["kelime"]}: {k} (doğrusu {v["koken"]})')
    o = lambda a: f"{a[0]}/{a[1]} (%{100 * a[0] / max(1, a[1]):.0f})"
    print(f"\n=== {ad}  ({sure:.0f} sn)")
    print(f"  Türkçe köken {o(say['tr'])} | Arapça-Farsça köken {o(say['arfa'])} | Batı köken {o(say['bati'])} | "
          f"Arapça-Farsça kök yazımı {o(say['yazim'])} | cevapsız {say['cevapsiz']}")
    for y in yanlis[:40]:
        print("   ", y)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--liste":
        r = requests.get(nvidia.URL + "/models", headers={"Authorization": "Bearer " + nvidia.anahtar()}, timeout=60)
        ara = (sys.argv[2] if len(sys.argv) > 2 else "").lower()
        for m in sorted(x["id"] for x in r.json().get("data", [])):
            if ara in m.lower():
                print(m)
        sys.exit()
    for ad in sys.argv[1:]:
        try:
            sinav(ad)
        except Exception as e:      # noqa: BLE001
            print(f"\n=== {ad}: HATA {type(e).__name__}: {e}")
