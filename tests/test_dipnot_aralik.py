"""0.5.35 gerileme testi: Surya sayfasında dipnot ayrımı satır aralığıyla (tests/dipnot_sayfalari.json: 10 kitaptan 39 gerçek
sayfa, önbellekteki ham satırlar ve her sayfanın doğru cevabı, 11 Ekim 2026 sunucu taramasından).
Dinde Kırk Prensip: uzun dipnot devamı sayfanın çoğunu kaplar (s.69-70), dipnot yazısı gövdeye yakın ölçülür (s.137, 231, 303),
ara başlık ve gövde satırları küçük ölçülür ama dipnot değildir (s.302). Diğerleri: başlıktan sonraki gövde (El-Afâk, Arayanlar
s.68, Ahiret), âyet meali (Ahiret s.74, 116), işaretli kısa notlar (Devlet s.5 '2 Habib', s.9 '5 Fatih', s.41 '* Cahiliye'),
numaralı not listeleri (Hidayet Rehberi, Helaller), şema (Hidayet s.32), kapak sayfası (Arayanlar s.10).
0.5.34 bu sayfaların 9'unu doğru ayırıyordu; bilinen yanlışlar (0.5.34'te de yanlış): Arayanlar s.4 (kapak), El-İktisad s.179 ve
s.277 (Arapça sayfa)."""
import json, os, sys, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kutuphane import kaynak as S

kalan = []
BILINEN = {("Arayanlar", "4"), ("iktisad", "179"), ("iktisad", "277")}


def dene(ad, kosul):
    print(("GECTI " if kosul else "KALDI ") + ad)
    if not kosul:
        kalan.append(ad)


V = json.load(open(os.path.join(os.path.dirname(__file__), "dipnot_sayfalari.json"), encoding="utf-8"))


def ayir(kitap, p, govde=None):
    k = V[kitap]
    rows = S._surya_satirlari([types.SimpleNamespace(text=t, bbox=b) for t, b in k["sayfalar"][p]["satirlar"]], 72 / 200, None)
    rows = S._sayfa_no_ve_kenar(rows, k["h"])[1]
    return S._dipnot_ayir(rows, k["h"], govde or k["govde"])


dogru_sayi = toplam = 0
for kitap, k in V.items():
    for p, s in k["sayfalar"].items():
        if (kitap, p) in BILINEN:
            continue
        ana, dip = ayir(kitap, p)
        ilk = dip[0]["text"].replace("\ue000", "").replace("\ue001", "") if dip else None
        bek = s["dogru"]
        ok = (bek is None and not dip) or (bek is not None and ilk is not None and ilk.startswith(bek))
        toplam += 1
        dogru_sayi += ok
        dene(f"{kitap} s.{p}: " + ("dipnot yok" if bek is None else f"dipnot '{bek}' ile başlar") +
             ("" if ok else f" (çıkan: {ilk[:30] if ilk else None!r})"), ok)
print(f"  {dogru_sayi}/{toplam} sayfa doğru")

# Dinde Kırk: gövde boyu kitap genelinden gelir ve sayfanınkinden farklı olabilir
for g in (18.5, 21.5):
    for p, bek in (("69", "Biz de deriz"), ("70", "ci ve olmazsa"), ("137", "ve onunla"), ("231", "ise, o anda"), ("303", "hu bu iş")):
        ana, dip = ayir("Kirk", p, g)
        dene(f"Kirk s.{p} (gövde {g}): dipnot '{bek}'", dip and dip[0]["text"].startswith(bek))
    ana, dip = ayir("Kirk", "302", g)
    dene(f"Kirk s.302 (gövde {g}): ara başlık gövdede", any(r["text"] == "Kötü ve Güzel Ahlâk" for r in ana))

# yardımcılar
r = lambda top, h=20, n=8, t="kelime kelime kelime": {"top": top, "h": h, "n": n, "text": t}
dene("Satır aralığı: paragraf boşluğu ortancayı bozmaz", S._satir_araligi([r(0), r(26), r(52), r(90), r(116)], 20) == 26)
dene("Satır aralığı: büyük harfli başlık sayılmaz", S._satir_araligi([r(0, t="YOL GİDENLERİN"), r(50, t="ARAYANLARIN")], 20) is None)
dene("İşaretli not: '2 Habib' / 'olunur2'", S._isaretli_not("2 Habib-üs-Siyer 11/4", "rivayet olunur2 Teşvik"))
dene("İşaretli not: '* Cahiliye' / 'giymezse *'", S._isaretli_not("* Cahiliye devrinde", "elbise giymezse * ve Allah"))
dene("İşaretli not değil: liste maddesi ('vardır: 1.')", not S._isaretli_not("1. Rûhânî ve", "dört türlü hidâyet vardır: 1. Allah"))

print("SONUC: HEPSI GECTI" if not kalan else f"SONUC: {len(kalan)} TEST KALDI")
sys.exit(1 if kalan else 0)
