# Stüdyo önce/sonra karşılaştırması (0.5.40, v3: hızlı dosya seçimi, en çok 150 sayfalık kitaplar, ilerleme yazar): aynı kitapları eski kodla (/app) ve yamalı kodla (/k) okur, paragrafları karşılaştırır.
#   uret <kod klasoru> <cikti.json> [en cok dosya]   -> /kaynak altındaki metin katmanlı PDF'ler ve EPUB'lar + /bakara.pdf
#   karsilastir <eski.json> <yeni.json>
import sys, os, json, re, time, difflib


def uret(kod, cikti, sinir):
    bu = os.path.dirname(os.path.abspath(__file__))
    sys.path[:] = [kod] + [p for p in sys.path if os.path.abspath(p or ".") not in (bu, os.path.abspath(kod))]
    from kutuphane import kaynak as K
    import fitz
    dosyalar = ["/bakara.pdf"] if os.path.exists("/bakara.pdf") else []
    adaylar = []
    for kok, _, adlar in os.walk("/kaynak"):
        secilen = [a for a in sorted(adlar) if a.lower().endswith((".pdf", ".epub"))][:2]   # klasör başına en çok 2 (çeşit olsun)
        adaylar += [os.path.join(kok, a) for a in secilen]
    adaylar.sort()
    print("aday dosya:", len(adaylar), flush=True)
    bakilan = 0
    for yol in adaylar:
        if len(dosyalar) >= sinir or bakilan >= 200:
            break
        bakilan += 1
        try:
            if os.path.getsize(yol) > 40_000_000:
                continue
            if yol.lower().endswith(".pdf"):   # hızlı denetim: ilk 6 sayfada metin katmanı var mı (taranmış PDF atlanır: OCR uzun sürer)
                doc = fitz.open(yol)
                if len(doc) > int(os.environ.get("EN_COK_SAYFA", "150")):
                    continue
                harf = sum(len(doc[i].get_text().strip()) for i in range(min(6, len(doc))))
                if harf < 300 * min(6, len(doc)):
                    continue
        except Exception:
            continue
        dosyalar.append(yol)
    print("secilen dosya:", len(dosyalar), flush=True)
    out = {}
    for yol in dosyalar:
        t = time.time()
        try:
            if yol.lower().endswith(".pdf"):
                og, notlar, bilgi = K.pdf_oku(yol)
            else:
                og, notlar, bilgi = K.epub_oku(yol)
            out[yol] = {"p": K._duzelt([o.get("metin", "") for o in og]), "asili": bilgi.get("asili_girinti")}
        except Exception as e:
            out[yol] = {"hata": repr(e)[:200]}
        print(f"{time.time() - t:6.1f} sn  {yol}", flush=True)
    json.dump(out, open(cikti, "w"), ensure_ascii=False)
    print("KOD:", os.path.dirname(os.path.dirname(os.path.abspath(K.__file__))), "| dosya:", len(out))


def karsilastir(a_yol, b_yol):
    a, b = json.load(open(a_yol)), json.load(open(b_yol))
    toplam = 0
    for k in a:
        x, y = a[k], b.get(k, {})
        if "hata" in x or "hata" in y:
            print("HATA", k, x.get("hata"), y.get("hata"))
            continue
        if x["p"] == y["p"]:
            print("AYNI", k, len(x["p"]), "paragraf")
            continue
        xs, ys = " ¶ ".join(x["p"]).split(), " ¶ ".join(y["p"]).split()
        yerler = [o for o in difflib.SequenceMatcher(None, xs, ys, autojunk=False).get_opcodes() if o[0] != "equal"]
        toplam += len(yerler)
        print("FARK", k, len(x["p"]), "->", len(y["p"]), "paragraf,", len(yerler), "yer | asili girinti:", y.get("asili"))
        for op, i1, i2, j1, j2 in yerler[:12]:
            print("     ", " ".join(xs[max(0, i1 - 3):i2 + 3])[:150], " => ", " ".join(ys[max(0, j1 - 3):j2 + 3])[:150])
    print("OZET: dosya", len(a), "| farkli yer", toplam)


if __name__ == "__main__":
    if sys.argv[1] == "uret":
        uret(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 25)
    else:
        karsilastir(sys.argv[2], sys.argv[3])
