"""Stüdyo 0.5.41 önce/sonra karşılaştırması (depoya girmez; kod klasöründe durur).
Aynı kitapları eski kodla (imajdaki /app = 0.5.40) ve yamalı kodla (/k) okur, paragraf paragraf karşılaştırır.
Kitaplar: kaynak_8 arşivindeki 8 kitap, /bakara.pdf ve /kaynak altındaki öteki EPUB'lar ile metin katmanlı PDF'ler (toplam en çok 30).
Çalıştırma (kod klasöründe):
  docker run --rm -v "$PWD":/k -w /k -v /media/ZimaOS-HD/Kitap:/kaynak:ro \
    -v /DATA/AppData/dedplay-studyo/osmanlica/olcum/girdi/002_Bakara_Suresi.pdf:/bakara.pdf:ro \
    -v /DATA/AppData/dedplay-studyo/rapor:/rapor -e OCR_MOTORU=tesseract -e TR_KELIME=/app/app/data/tr_kelime.txt \
    berzahbey/dedplay-studyo:latest python3 studyo_0541_karsilastir.py
Çıktı: /rapor/rapor_0541.txt (sunucuda /DATA/AppData/dedplay-studyo/rapor/rapor_0541.txt), ekrana kitap başına özet."""
import collections, difflib, json, os, subprocess, sys

SEKIZ = ["ISLAM/Risale-i Nur/Asar-i Bediye.epub", "ISLAM/Risale-i Nur/Sikkeyi tasdik.epub",
         "ISLAM/Risale-i Nur/iman ve küfür muvazeneleri.epub", "Türkçe Kitaplar/Din ve Felsefe/Şemsi Tebrizi - Makalat.epub",
         "Türkçe Kitaplar/Din ve Felsefe/Muhyiddin İbn Arabi - Özün Özü.epub",
         "ISLAM/imam-gazzali-kitapligi/İmam Gazali - Kudsi Hadisler.pdf", "ISLAM/İslam Felsefesi/Farabi - Kitabu'l -Burhan.pdf",
         "ISLAM/İslam Felsefesi/Joseph Schacht - İslam Hukukuna Giriş.pdf"]
EN_COK = 30


def oku(kod, yol):
    """Ayrı süreçte (eski/yeni kod karışmasın): kitabı okur, satır listesi döndürür."""
    betik = r'''
import sys, json, os
sys.path.insert(0, sys.argv[1])
os.environ["DATA_DIR"] = "/tmp/k0541_data"
from kutuphane import kaynak as K
kit = K.cevir(sys.argv[2])
out = ["KUNYE\t" + kit["kunye"]["baslik"]["tr"] + " | " + kit["kunye"]["yazar"]["tr"]]
for b in kit["bloklar"]:
    m = b.get("metin", {}); m = m.get("tr") if isinstance(m, dict) else m
    out.append(b["tur"] + str(b.get("seviye", "")) + "\t" + (m or ""))
for g, n in (kit.get("dipnotlar") or {}).items():
    m = n.get("metin", n) if isinstance(n, dict) else n; m = m.get("tr") if isinstance(m, dict) else m
    out.append("NOT\t" + (m or ""))
print(json.dumps(out, ensure_ascii=False))
'''
    env = dict(os.environ, PYTHONHASHSEED="0", PYTHONPATH=kod)
    r = subprocess.run([sys.executable, "-c", betik, kod, yol], capture_output=True, text=True, env=env, timeout=3600)
    if r.returncode:
        return None, r.stderr.strip().splitlines()[-1:] or ["?"]
    return json.loads(r.stdout.strip().splitlines()[-1]), None


def farklar(a, b):
    deg = collections.Counter()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        wa = " ".join("[" + x.replace("\t", "] ", 1) for x in a[i1:i2]).split()
        wb = " ".join("[" + x.replace("\t", "] ", 1) for x in b[j1:j2]).split()
        for o2, x1, x2, y1, y2 in difflib.SequenceMatcher(None, wa, wb, autojunk=False).get_opcodes():
            if o2 != "equal":
                deg[" ".join(wa[x1:x2])[:150] + "  ->  " + " ".join(wb[y1:y2])[:150]] += 1
    return deg


def kitaplar():
    secilen = [os.path.join("/kaynak", y) for y in SEKIZ if os.path.exists(os.path.join("/kaynak", y))]
    if os.path.exists("/bakara.pdf"):
        secilen.append("/bakara.pdf")
    if os.environ.get("ARSIV") != "1":
        return secilen   # varsayılan: yalnız 8 kitap + Bakara (arşiv taraması uzun sürüyor)
    sys.path.insert(0, "/app")
    from kutuphane import kaynak as K
    for kok, _, adlar in sorted(os.walk("/kaynak")):
        for ad in sorted(adlar):
            yol = os.path.join(kok, ad)
            if len(secilen) >= EN_COK or yol in secilen:
                continue
            if ad.lower().endswith(".epub"):
                secilen.append(yol)
            elif ad.lower().endswith(".pdf"):
                try:
                    if not K.ocr_gerekir(yol) and os.path.getsize(yol) < 40e6:
                        secilen.append(yol)
                except Exception:
                    pass
    return secilen


def main():
    os.makedirs("/rapor", exist_ok=True)
    rapor = open("/rapor/rapor_0541.txt", "w", encoding="utf-8")
    for yol in kitaplar():
        ad = os.path.basename(yol)
        a, hata_a = oku("/app", yol)
        b, hata_b = oku("/k", yol)
        if a is None or b is None:
            satir = f"== {ad}: HATA eski={hata_a} yeni={hata_b}"
            print(satir, flush=True)
            rapor.write(satir + "\n")
            continue
        deg = farklar(a, b)
        satir = f"== {ad}: blok {len(a)} -> {len(b)}, {sum(deg.values())} yer" + ("  AYNI" if not deg else "")
        print(satir, flush=True)
        rapor.write(satir + "\n")
        for k, v in deg.most_common():
            rapor.write(f"  {v:4d} {k}\n")
        rapor.flush()
    rapor.close()
    print("RAPOR: /rapor/rapor_0541.txt")


if __name__ == "__main__":
    main()
