"""PDF kitapların sayfa dökümü (19 Ekim, ana metin planı adım 4).

kaydet: Stüdyo'daki her PDF kitabı o anki kodla (kaynak.cevir) okur ve PDF'e dokunan iki yerin sonucunu kaydeder:
  pdf_sayfalari (satırlar + konumları, OCR önbelleğinden) ve _ocr_icindekiler (taranmış içindekiler). Kitabın çıktısı (kit)
  da kaydedilir. Hiçbir şey yazmaz (yalnız çıktı klasörüne <kimlik>.pkl.gz); /data salt okunur bağlanabilir.
  docker run ... python /k/araclar/sayfa_dokum.py kaydet /data/kitaplar /rapor/dokum
oynat: kayıttan PDF'siz aynı kitabı üretir (Claude'un ortamında sayfa düzeni denemeleri için); kaydedilen kit ile karşılaştırır.
  python araclar/sayfa_dokum.py oynat <klasör ya da .pkl.gz>
yaz: kayıttan o anki kodla kitap.json üretir (<çıktı>/<kimlik>/kitap.json) ve md5'ini yazar: sunucu ile Claude'un ortamı aynı kodla
  aynı çıktıyı veriyor mu (md5'ler birebir aynı olmalı); çıktı klasörü karisma_olcu.py olc ile de ölçülebilir.
  python araclar/sayfa_dokum.py yaz <klasör> <çıktı>
"""
import glob
import gzip
import json
import os
import pickle
import sys
import time

sys.path.insert(0, os.environ.get("OLCU_KOD", "/app"))
from kutuphane import kaynak as K  # noqa: E402


def _kitap_pdfleri(kitaplar):
    for j in sorted(glob.glob(os.path.join(kitaplar, "*", "kitap.json"))):
        ku = json.load(open(j, encoding="utf-8")).get("kunye") or {}
        yol = (ku.get("kaynak") or {}).get("yol") or ""
        if yol.lower().endswith(".pdf"):
            yield os.path.basename(os.path.dirname(j)), yol


def kaydet(kitaplar, cikti):
    os.makedirs(cikti, exist_ok=True)
    asil_sayfa, asil_toc = K.pdf_sayfalari, K._ocr_icindekiler
    for kid, yol in _kitap_pdfleri(kitaplar):
        if not os.path.exists(yol):
            print(f"{kid}: kaynak yok ({yol})", flush=True)
            continue
        kayit = {"kimlik": kid, "yol": yol, "toc": {}}

        def sayfa(y, ilerleme=None):
            s, b = asil_sayfa(y, ilerleme)
            b = dict(b)
            b.pop("kapak_resmi", None)
            kayit["sayfalar"], kayit["bilgi"] = s, b
            return s, dict(b, kapak_resmi=None)

        def toc(y, i, dil):
            r = asil_toc(y, i, dil)
            kayit["toc"][(i, dil)] = r
            return r

        K.pdf_sayfalari, K._ocr_icindekiler = sayfa, toc
        t0 = time.time()
        try:
            kayit["kit"] = K.cevir(yol)
        except Exception as e:
            print(f"{kid}: HATA {type(e).__name__}: {e}", flush=True)
            continue
        finally:
            K.pdf_sayfalari, K._ocr_icindekiler = asil_sayfa, asil_toc
        hedef = os.path.join(cikti, kid + ".pkl.gz")
        with gzip.open(hedef, "wb") as f:
            pickle.dump(kayit, f, protocol=4)
        n = len(kayit.get("sayfalar") or [])
        print(f"{kid}: {n} sayfa, {time.time() - t0:.0f} sn, {os.path.getsize(hedef) // 1024} KB", flush=True)


def yukle(yol):
    with gzip.open(yol, "rb") as f:
        return pickle.load(f)


def oynat_bir(kayit):
    """Kayıttaki sayfalarla kitabı yeniden üretir (o anki kodla)."""
    asil_sayfa, asil_toc = K.pdf_sayfalari, K._ocr_icindekiler
    K.pdf_sayfalari = lambda y, ilerleme=None: (kayit["sayfalar"], dict(kayit["bilgi"], kapak_resmi=None))
    K._ocr_icindekiler = lambda y, i, dil: kayit["toc"][(i, dil)]
    try:
        return K.cevir(kayit["yol"])
    finally:
        K.pdf_sayfalari, K._ocr_icindekiler = asil_sayfa, asil_toc


def _ozet(kit):
    return [(b.get("tur"), (b.get("metin") or {}).get("tr")) for b in kit.get("bloklar") or []]


def oynat(hedef):
    dosyalar = sorted(glob.glob(os.path.join(hedef, "*.pkl.gz"))) if os.path.isdir(hedef) else [hedef]
    for d in dosyalar:
        kayit = yukle(d)
        kit = oynat_bir(kayit)
        a, b = _ozet(kayit["kit"]), _ozet(kit)
        ayni = a == b and kayit["kit"].get("dipnotlar") == kit.get("dipnotlar")
        print(f"{kayit['kimlik']}: {'AYNI' if ayni else 'FARKLI'} ({len(a)} -> {len(b)} blok)")


def yaz(hedef, cikti):
    import hashlib
    for d in sorted(glob.glob(os.path.join(hedef, "*.pkl.gz"))):
        kayit = yukle(d)
        kit = oynat_bir(kayit)
        klasor = os.path.join(cikti, kayit["kimlik"])
        os.makedirs(klasor, exist_ok=True)
        veri = json.dumps(kit, ensure_ascii=False).encode("utf-8")
        with open(os.path.join(klasor, "kitap.json"), "wb") as f:
            f.write(veri)
        print(f"{hashlib.md5(veri).hexdigest()}  {kayit['kimlik']}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "kaydet":
        kaydet(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 4 and sys.argv[1] == "yaz":
        yaz(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 3 and sys.argv[1] == "oynat":
        oynat(sys.argv[2])
    else:
        print(__doc__)
