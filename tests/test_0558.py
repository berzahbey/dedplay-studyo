"""0.5.58: denetim kuralları (rapor incelemesinden, bütün kitaplar için):
  1) tireyle bitişik kelime ("olabildigi-ni") düzeltilmez: "olabildiğini-ni" tekrarı olmasın;
  2) eski ek yazımı yazarın imlâsıdır: bekliyerek/başlıyacak/bilmiyen/çalmağa modernleştirilmez ("kayamet"->"kıyamet" kalır);
  3) ölçü içindeki sayı ("16x19 cm") dipnot işareti sayılmaz."""
import os, re, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kutuphane import denetim as D, rapor as R  # noqa: E402
# sözlük (zeyrek) bu testte yok: küçük bir sözlükle
SOZLUK = set("""bu kitap ile arasında bir fark görmez onları doğru değildir beden nasıl bilmiyoruz yardım gittiler ve değil
çalıştılar mektup cm ebadında idi bunu söyledi sonra gitti olmaz de ısrar karıştırmak bekleyerek çalmaya kaçmağa""".split())
R._gecerli = lambda w: w in SOZLUK

hata = []

# --- 2) imlâ kuralı (birim)
for w, d, bekle in [("bekliyerek", "bekleyerek", True), ("başlıyacak", "başlayacak", True), ("Bilmiyen", "Bilmeyen", True),
                    ("çalmağa", "çalmaya", True), ("gelmeğe", "gelmeye", True), ("kalb", "kalp", True),
                    ("kayamet", "kıyamet", False), ("kanştırmak", "karıştırmak", False), ("Hişatm", "Hişam", False),
                    ("öğütieyiniz", "öğütleyiniz", False), ("kesiierek", "kesilerek", False)]:
    if D._eski_yazim(w, d) != bekle:
        hata.append(f"imlâ {w}->{d}: {not bekle} bekleniyordu {bekle}")

# --- 1) ve 3): uçtan uca, sahte modelle
DUZ = {"bekliyerek": "bekleyerek", "olabildigi": "olabildiğini", "kanştırmak": "karıştırmak", "çalmağa": "çalmaya"}


class Model:
    ad = "sahte"
    sorulan = []

    def sor(self, sistem, metin, en_fazla=0):
        out = []
        for satir in metin.split("\n"):
            m = re.match(r"(\d+)\. (.*)", satir)
            if not m:
                continue
            no, govde = int(m.group(1)), m.group(2)
            if metin.startswith("SAYI"):
                out.append({"no": no, "dipnot_isareti": True})
                Model.sorulan.append(("sayi", govde))
            elif "«" in govde and govde.split("»")[0].strip("«") in DUZ:
                w = govde.split("»")[0].strip("«")
                Model.sorulan.append(("kelime", w))
                out.append({"no": no, "hata": True, "dogru": DUZ[w]})
        import json
        return json.dumps(out), "sahte"


metin = ("Bu kitap karıştırmak ile karıştırmak arasında bir fark görmez; onları kanştırmak doğru değildir. "
         "Beden nasıl olabildigi-ni bilmiyoruz. Yardım bekliyerek gittiler ve kaçmağa değil çalmağa çalıştılar. "
         "Mektup; 16x19 cm. ebadında idi. Bunu söyledi.12 Sonra gitti.")
kit = {"bloklar": [{"tur": "p", "metin": {"tr": metin}}], "dipnotlar": {}}
d = D.Denetci(tempfile.mkdtemp(prefix="t0558-"), model=Model(), on_ek="")
d.calistir(kit)
son = kit["bloklar"][0]["metin"]["tr"]
if "-ni-ni" in son or "olabildiğini-ni" in son:
    hata.append("tireli kelime düzeltildi")
if ("kelime", "olabildigi") in Model.sorulan:
    hata.append("tireli kelime modele soruldu")
if "bekliyerek" not in son or "çalmağa" not in son:
    hata.append("eski yazım değişti")
if "karıştırmak doğru" not in son:
    hata.append(f"gerçek OCR düzeltmesi kayboldu: {son}")
if any("«19»" in g for t, g in Model.sorulan if t == "sayi") or D.OK_AC + "19" in son:
    hata.append("16x19 dipnot sayıldı")
if D.OK_AC + "12" not in son:
    hata.append("gerçek dipnot işareti (söyledi.12) okunmaz olmadı")

# --- tireli yer başka yerde de aynı kelime çıplak geçiyorsa: çıplak olan düzelir, tireli kalır
D2 = D.Denetci(tempfile.mkdtemp(), model=Model(), on_ek="")
rx_kit = {"bloklar": [{"tur": "p", "metin": {"tr": "Onları kanştırmak olmaz. Bir de kanştırmak-ta ısrar. karıştırmak karıştırmak"}}],
          "dipnotlar": {}}
D2.calistir(rx_kit)
t2 = rx_kit["bloklar"][0]["metin"]["tr"]
if "Onları karıştırmak olmaz" not in t2 or "kanştırmak-ta" not in t2:
    hata.append(f"tire sınırı: {t2}")

print("\n".join(hata) or "test_0558: hepsi geçti")
sys.exit(1 if hata else 0)
