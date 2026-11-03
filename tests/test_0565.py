"""0.5.65: model "kaynak" dediği "Eser, sayfa" biçimli parantez okunmaz olur ("(Tehafüt et-Tehafüt, 32)",
"(nakleden, Osman, 49)"); açıklama parantezleri ("(filozofların)", "(Kategoriler)") ve tarihler okunur
(Filozofların Tutarsızlığı denetim raporundan; kural bütün kitaplar için)."""
import json, os, re, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kutuphane import denetim as D, rapor as R  # noqa: E402
R._gecerli = lambda w: True

hata = []
EVET = ["Tehafüt et-Tehafüt, 32", "Tehafüt et- Tehafüt 42-52", "nakleden, Osmân, 49", "nakleden. Osman, 84",
        "21 - 26 nolu dipnotlar", "nakleden Sübkî, Tabakât, IV, 104, 110", "Süleyman Dünya Tehâfüt el-felâsife, 77",
        "el-Aydarûs, Ta'rîf, 30, Sübkî, Tabakât, IV, 116 Kâtib Çelebi, Keşf, 1129", "Journ. of Am. Or. Soc. 1899, XX, 71-132",
        "Tehafüt et-Tehâ. füt 249-250", "Tahafüt et Tahafüt, 39", "Tehafüt et-Tehafüt 162", "Buhârî, Savm 5"]
HAYIR = ["11. Analitikler", "I. Analitikler", "Kategoriler", "De Caelo et Mundo", "yaşayabileceğini", "filozofların",
         "Sâvî dedi ki:", "*", "ÖL 1030 - 1621", "19960", "Pages de théologie musulmane", "İbn Rüşdün Tehafütü", "sene 505",
         "Hicri 505", "miladi 1111", "Aralık 1111", "1111", "505 yılı", "öl. 505", "ölümü 1111", "yaklaşık 300",
         "Yaklaşık 300", "toplam 12", "hepsi 3", "12 kişi", "Bakara 255"]
for s in EVET:
    if not D.sayfali_kaynak(s):
        hata.append(f"kaynak sayılmadı: ({s})")
for s in HAYIR:
    if D.sayfali_kaynak(s):
        hata.append(f"yanlışlıkla kaynak: ({s})")


class Model:  # her parantez için "kaynak" der (en kötü durum): kurallar ayırmalı
    ad = "sahte"

    def sor(self, sistem, metin, en_fazla=0):
        out = [{"no": int(m.group(1)), "tur": "kaynak"} for m in re.finditer(r"^(\d+)\. ", metin, re.M)]
        return json.dumps(out), "sahte"


metin = ("Ebu Hâmid'in itirazı onları ilzam etmez. (Tehafüt et-Tehafüt, 175-182) Bu, kavmin (filozofların) bildiği şey değildir. "
         "Katiğoryas (Kategoriler) ve Îsâgûcî. Gazzâlî (Hicri 505) yılında öldü. Siyer (nakleden, Osman, 69), Yâfiî.")
kit = {"bloklar": [{"tur": "p", "metin": {"tr": metin}}], "dipnotlar": {}}
d = D.Denetci(tempfile.mkdtemp(prefix="t0565-"), model=Model(), on_ek="")
d.calistir(kit)
son = kit["bloklar"][0]["metin"]["tr"]
for p in ["(Tehafüt et-Tehafüt, 175-182)", "(nakleden, Osman, 69)"]:
    if D.OK_AC + p not in son:
        hata.append(f"okunmaz olmadı: {p}")
for p in ["(filozofların)", "(Kategoriler)", "(Hicri 505)"]:
    if D.OK_AC + p in son:
        hata.append(f"okunmaz yapıldı: {p}")

print("\n".join(hata) or "test_0565: hepsi geçti")
sys.exit(1 if hata else 0)
