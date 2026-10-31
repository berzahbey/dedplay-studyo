"""0.5.55: resim olarak konmuş gazete kupürü (Tahrif 3 son sayfası, sayfa düzeni kutuları sunucudan) metinden çıkar; yanındaki yazar
metni, resimsiz sayfa, dipnot ve resimler arasındaki gövde paragrafı kalır."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kutuphane.kaynak import _resim_satirlari, _govde_satir_boyu


def satirlar(x0, x1, y0, y1, adet, n, ad):
    adim = (y1 - y0) / adet
    return [{"x0": x0, "x1": x1, "top": y0 + k * adim, "bot": y0 + k * adim + adim * 0.8, "n": n, "text": f"{ad}{k}"} for k in range(adet)]


BOL = [("Picture", 25, 46, 345, 294, .999), ("Picture", 31, 296, 242, 348, .974), ("Text", 80, 350, 139, 355, .97),
       ("SectionHeader", 32, 362, 247, 411, .999), ("Text", 32, 415, 105, 451, 1.0), ("SectionHeader", 46, 455, 86, 462, 1.0),
       ("Text", 33, 464, 107, 521, 1.0), ("Text", 33, 520, 108, 559, 1.0), ("Picture", 114, 417, 246, 562, 1.0),
       ("Text", 254, 316, 350, 541, 1.0)]
ROWS = (satirlar(60, 300, 60, 120, 3, 3, "kapak") + satirlar(82, 137, 350.5, 355, 1, 3, "tarih")
        + satirlar(34, 245, 363, 411, 2, 4, "baslik") + satirlar(33, 104, 416, 451, 9, 6, "haber")
        + satirlar(47, 85, 456, 462, 1, 3, "muhabir") + satirlar(34, 106, 465, 520, 14, 6, "haber")
        + satirlar(34, 106, 521, 558, 10, 6, "haber") + satirlar(256, 349, 317, 541, 16, 3, "yazar"))
GOVDE = 11.0
sil = _resim_satirlari(ROWS, BOL, 386, GOVDE)
cik = {ROWS[k]["text"].rstrip("0123456789") for k in sil}
kalan = {r["text"].rstrip("0123456789") for k, r in enumerate(ROWS) if k not in sil}
hata = []
for ad in ("kapak", "tarih", "baslik", "haber", "muhabir"):
    if ad not in cik or ad in kalan:
        hata.append(f"çıkmalıydı: {ad}")
if "yazar" in cik:
    hata.append("yazar metni çıktı")
# eski davranış: govde_boy yoksa yalnız resim içi
eski = {ROWS[k]["text"].rstrip("0123456789") for k in _resim_satirlari(ROWS, BOL, 386)}
if eski != {"kapak"}:
    hata.append(f"govde_boy'suz davranış değişti: {eski}")
# resimler arasında gövde paragrafı (3+ satır, gövde boyu) ve altta dipnot kalır
BOL2 = [("Picture", 30, 40, 350, 200, 1), ("Text", 30, 205, 350, 260, 1), ("Picture", 30, 265, 350, 400, 1),
        ("Footnote", 30, 520, 200, 560, 1)]
ROWS2 = satirlar(30, 350, 206, 260, 4, 10, "paragraf") + satirlar(30, 200, 521, 560, 6, 8, "dipnot")
for r in ROWS2:
    if r["text"].startswith("dipnot"):
        r["bot"] = r["top"] + 5
if _resim_satirlari(ROWS2, BOL2, 386, GOVDE):
    hata.append("gövde paragrafı ya da dipnot çıktı")
# resimler arasında bölüm başlığı (küçük yazı yok) kalır (Tahrif 3 s.289)
BOL3 = [("Picture", 30, 40, 350, 200, 1), ("SectionHeader", 60, 205, 320, 240, 1), ("Picture", 30, 245, 350, 400, 1)]
ROWS3 = satirlar(60, 320, 206, 222, 1, 2, "bolum") + satirlar(60, 320, 223, 240, 1, 4, "baslik")
if _resim_satirlari(ROWS3, BOL3, 386, GOVDE):
    hata.append("resimler arasındaki bölüm başlığı çıktı")
# resimsiz sayfa değişmez
if _resim_satirlari(ROWS2, [("Text", 30, 205, 350, 260, 1)], 386, GOVDE):
    hata.append("resimsiz sayfada çıkarma")
# gövde boyu ölçüsü
s = [(satirlar(30, 350, 0, 600, 60, 8, "g"), 386, 597, True)]
gb = _govde_satir_boyu(s)
if not gb or abs(gb - 8) > 0.5:
    hata.append(f"gövde boyu {gb}")
print("test_0555:", "HEPSI GECTI" if not hata else "KALDI: " + "; ".join(hata))
sys.exit(1 if hata else 0)
