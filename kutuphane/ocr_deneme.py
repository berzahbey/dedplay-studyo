"""0.5.87: OCR düzeltme modeli sınavı (Zahir, 23 Kasım: kuralın çözemediğini ayrı bir yapay zekâ cümlesiyle düzeltsin; her adıma ayrı model).
97 kelime cümlesiyle: 62 OCR bozuğu (İdeal Devlet; doğrusu biliniyor: aym -> aynı, krıldığı -> kırıldığı) + 35 doğru ama seyrek kelime
(Ahlak, Fusûsu'l-Hikem: takyit, itâbı, Gnostisizm, mücevheratı — dokunulmamalı). Model her kelime için doğrusunu yazar.
Kullanım (stüdyo konteynerinde):
  python -m kutuphane.ocr_deneme --liste [arama]           NVIDIA hesabındaki model adları
  python -m kutuphane.ocr_deneme <model> [<model> ...]     ör. nvidia/nemotron-3-ultra-550b-a55b qwen/qwen3-…
Çıktı: bozuk düzeltilen / doğru korunan / süre ve yanlışlar."""
import json, os, re, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import requests
from kutuphane import nvidia

VERI = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ocr_deneme.json"), encoding="utf-8"))
SISTEM = """Sen Türkçe bir yazım düzeltme uzmanısın. Metinler eski kitapların OCR (tarama) çıktısıdır; OCR bazı harfleri karıştırır
(ör. "nı/ri/rn" yerine "m" ya da "n", "H" yerine "Fi", "t" yerine "ü"). Her maddede « » içindeki TEK kelimeye bak:
- OCR bozuksa cümleye uyan doğru Türkçe kelimeyi yaz (aynı ekleriyle).
- Kelime doğruysa (eski, Arapça/Farsça kökenli, nadir ya da özel ad olabilir) AYNEN yaz; emin değilsen değiştirme.
Yalnız JSON dizi döndür: [{"no": 1, "dogru": "..."}, ...]. Açıklama yazma."""


def _kucuk(w):
    return (w or "").replace("I", "ı").replace("İ", "i").lower().strip(" .,;:«»\"'")


def sor(model, ogeler):
    kullanici = "\n".join(f'{i}. {o["once"][-80:]} «{o["kelime"]}» {o["sonra"][:80]}' for i, o in enumerate(ogeler, 1))
    cevap, _ = nvidia.Nvidia(model).sor(SISTEM, kullanici, en_fazla=3000)
    m = re.search(r"\[.*\]", cevap or "", re.S)
    try:
        return {int(x["no"]): str(x.get("dogru", "")) for x in json.loads(m.group(0))} if m else {}
    except (ValueError, KeyError, TypeError):
        return {}


def sinav(model):
    t0 = time.time()
    cevap = {}
    for i in range(0, len(VERI), 50):
        try:
            c = sor(model, VERI[i:i + 50])
        except Exception as e:     # noqa: BLE001
            print(f"  grup cevapsız: {type(e).__name__}: {str(e)[:120]}")
            c = {}
        for no, d in c.items():
            cevap[i + no - 1] = d
    say = {"bozuk": [0, 0], "dogru": [0, 0]}
    yanlis = []
    for j, v in enumerate(VERI):
        say[v["tur"]][1] += 1
        d = cevap.get(j)
        ok = d is not None and _kucuk(d) == _kucuk(v["dogru"])
        say[v["tur"]][0] += ok
        if not ok:
            yanlis.append(f'{v["tur"]}: {v["kelime"]} -> {d!r} (doğrusu {v["dogru"]})')
    print(f"== {model}: bozuk düzeltilen {say['bozuk'][0]}/{say['bozuk'][1]}, doğru korunan {say['dogru'][0]}/{say['dogru'][1]}, "
          f"cevapsız {len(VERI) - len(cevap)}, {time.time() - t0:.0f} sn")
    for y in yanlis[:25]:
        print("   ", y)


def liste(arama=""):
    r = requests.get(nvidia.URL + "/models", headers={"Authorization": "Bearer " + nvidia.anahtar()}, timeout=60)
    for m in sorted(x["id"] for x in r.json().get("data", [])):
        if arama.lower() in m.lower():
            print(m)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--liste":
        liste(sys.argv[2] if len(sys.argv) > 2 else "")
    else:
        for m in sys.argv[1:]:
            sinav(m)
