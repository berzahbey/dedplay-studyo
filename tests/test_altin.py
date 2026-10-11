"""Altın çıktı (kutuphane/altin.py): döküm, üretme (taklit kaynak ile) ve karşılaştırma."""
import copy, json, os, shutil, sys, tempfile, types

kalan = []


def dene(ad, kosul):
    print(("  TAMAM  " if kosul else "  KALDI  ") + ad)
    if not kosul:
        kalan.append(ad)


from kutuphane import altin as A


def kitap():
    return {"kunye": {"baslik": {"tr": "Dinde  Kırk Prensip"}, "yazar": {"tr": "Gazâlî"}, "asil_dil": "tr"},
            "bloklar": [
                {"id": "b00001", "tur": "baslik", "seviye": 1, "metin": {"tr": "BİRİNCİ PRENSİP"}},
                {"id": "b00002", "tur": "p", "metin": {"tr": "Allah'a iman{{n0001}} esastır.", "osm": "x"},
                 "sayfalar": [{"no": "12", "konum": {"tr": 7}}], "notlar": ["n0001"]},
                {"id": "b00003", "tur": "p", "metin": {"tr": "İkinci paragraf burada{{n0002}} biter."}, "notlar": ["n0002"]},
                {"id": "b00004", "tur": "p", "metin": {"tr": "Silinmiş satır."}, "silindi": True},
            ],
            "dipnotlar": {"n0001": {"metin": {"tr": "Birinci not."}}, "n0002": {"metin": {"tr": "İkinci not."}},
                          "n0009": {"metin": {"tr": "Sahipsiz not."}}}}


d = A.dok(kitap())
print("\n".join("    " + x for x in d))
dene("künye satırları, çift boşluk teke", d[0] == "K| başlık: Dinde Kırk Prensip" and d[1] == "K| yazar: Gazâlî")
dene("başlık seviyesiyle", "B1| BİRİNCİ PRENSİP" in d)
dene("sayfa işareti konumunda, dipnot atfı [*]", "P| Allah'a⟦12⟧ iman[*] esastır." in d)
dene("dipnot paragrafın hemen altında", d[d.index("P| Allah'a⟦12⟧ iman[*] esastır.") + 1] == "N| Birinci not.")
dene("silinmiş blok yazılmaz", not any("Silinmiş" in x for x in d))
dene("sahipsiz dipnot sonda Y", d[-1] == "Y| Sahipsiz not.")
dene("Osmanlıca dökülmez", not any(x.endswith("| x") for x in d))

# dipnot kimlikleri değişse de (araya not eklenince) döküm aynı
k2 = kitap()
k2["bloklar"][1]["metin"]["tr"] = "Allah'a iman{{n0007}} esastır."
k2["bloklar"][1]["notlar"] = ["n0007"]
k2["dipnotlar"]["n0007"] = k2["dipnotlar"].pop("n0001")
dene("dipnot kimliği değişince döküm aynı", A.dok(k2) == d)

# karşılaştırma
e = d
y = list(d)
y[y.index("P| İkinci paragraf burada[*] biter.")] = "P| İkinci paragraf orada[*] biter."
y[y.index("N| İkinci not.")] = "N| İkinci notu."
y[y.index("B1| BİRİNCİ PRENSİP")] = "B2| BİRİNCİ PRENSİP"
say, satir, cift = A.kitap_farki(e, y)
print("\n".join("    " + x for x in satir))
dene("gövde farkı sayıldı", say["gövde"] == 1 and ("gövde", "burada[*]", "orada[*]") in cift)
dene("dipnot farkı sayıldı", say["dipnot"] == 1)
dene("başlık seviyesi farkı", say["başlık seviyesi"] == 1)
dene("sayfa numarası farkta görünür", any("[s.12]" in s for s in satir if "orada" in s))
y2 = [x for x in d if x != "N| Birinci not."]
say, satir, _ = A.kitap_farki(d, y2)
dene("kaybolan dipnot 'dipnot satırı gitti'", say["dipnot satırı gitti"] == 1 and any("- N| Birinci not." in s for s in satir))
y3 = [x.replace("Allah'a⟦12⟧ iman", "Allah'a iman⟦12⟧") for x in d]
say, _, _ = A.kitap_farki(d, y3)
dene("yalnız sayfa işareti kayınca 'sayfa işareti'", say == {"sayfa işareti": 1})
say, satir, _ = A.kitap_farki(d, list(d))
dene("aynı dökümde fark yok", not say and not satir)

# üretme ve karşılaştırma klasörlerle (taklit kaynak / kitap / rapor)
kok = tempfile.mkdtemp()
os.environ["DATA_DIR"] = kok
for kid, ky in (("kitap-a", "a.pdf"), ("kitap-b", "b.epub"), ("kitap-c", None), ("kitap-d", "d.pdf")):
    os.makedirs(os.path.join(kok, "kitaplar", kid))
    yol = os.path.join(kok, ky) if ky else None
    if yol:
        open(yol, "w").write("x")
    json.dump({"kunye": {"kaynak": {"yol": yol}}, "bloklar": []},
              open(os.path.join(kok, "kitaplar", kid, "kitap.json"), "w"))
cagri = []
taklit_kaynak = types.SimpleNamespace(
    __file__=os.path.join(os.path.dirname(A.__file__), "kaynak.py"),
    ocr_gerekir=lambda yol: yol.endswith("d.pdf"),
    cevir=lambda yol, il, kb: cagri.append(yol) or (kitap() if yol.endswith("a.pdf") else (_ for _ in ()).throw(ValueError("bozuk"))))
taklit_kitap = types.SimpleNamespace(yukle=lambda p: json.load(open(p)))
taklit_rapor = types.SimpleNamespace(_kitaplar_klasoru=lambda: os.path.join(kok, "kitaplar"))
paket = sys.modules["kutuphane"]
eski = {n: getattr(paket, n, None) for n in ("kaynak", "kitap", "rapor")}
eski_mod = {n: sys.modules.get("kutuphane." + n) for n in ("kaynak", "kitap", "rapor")}
for n, m in (("kaynak", taklit_kaynak), ("kitap", taklit_kitap), ("rapor", taklit_rapor)):
    setattr(paket, n, m)
    sys.modules["kutuphane." + n] = m
try:
    oz = A.uret(os.path.join(kok, "altin"))
finally:
    for n in eski:
        if eski[n] is None:
            delattr(paket, n)
        else:
            setattr(paket, n, eski[n])
        if eski_mod[n] is None:
            sys.modules.pop("kutuphane." + n, None)
        else:
            sys.modules["kutuphane." + n] = eski_mod[n]
print("    " + oz.replace("\n", "\n    "))
dene("üretilen kitap yazıldı", open(os.path.join(kok, "altin", "kitap-a.txt")).read().split("\n")[:-1] == d)
dene("sürüm dosyadan okundu", "sürüm 0." in oz)
dene("kaynaksız kitap atlandı", "[kitap-c] ATLANDI: kaynak dosya yok" in oz)
dene("OCR'ı önbellekte olmayan atlandı, cevir çağrılmadı", "[kitap-d] ATLANDI: OCR" in oz and not any(c.endswith("d.pdf") for c in cagri))
dene("hata veren kitap HATA satırı, diğerlerini durdurmaz", "[kitap-b] HATA: ValueError: bozuk" in oz)
dene("yarım dosya kalmadı", not any(f.endswith(".yaziliyor") for f in os.listdir(os.path.join(kok, "altin"))))

shutil.copytree(os.path.join(kok, "altin"), os.path.join(kok, "yeni"))
oz = A.karsilastir(os.path.join(kok, "altin"), os.path.join(kok, "yeni"), os.path.join(kok, "fark"))
dene("aynı kod: bütün kitaplar aynı", "aynı 1 kitap, değişen 0 kitap" in oz)
with open(os.path.join(kok, "yeni", "kitap-a.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(y) + "\n")
open(os.path.join(kok, "yeni", "kitap-z.txt"), "w").write("K| başlık: Z\n")
oz = A.karsilastir(os.path.join(kok, "altin"), os.path.join(kok, "yeni"), os.path.join(kok, "fark"))
print("    " + oz.replace("\n", "\n    "))
dene("değişen kitap özette türleriyle", "[kitap-a] başlık seviyesi 1, dipnot 1, gövde 1" in oz and "değişen 1 kitap" in oz)
dene("kitabın fark dosyası yazıldı", "orada" in open(os.path.join(kok, "fark", "kitap-a.txt"), encoding="utf-8").read())
dene("yeni kitap ayrıca belirtilir", "[kitap-z] ALTINDA YOK" in oz)

os.remove(os.path.join(kok, "yeni", "_ozet.txt"))
oz = A.karsilastir(os.path.join(kok, "altin"), os.path.join(kok, "yeni"), os.path.join(kok, "fark"))
dene("_ozet.txt'siz (bitmemiş) klasör karşılaştırılmaz", oz.startswith("HATA:") and "bitmemiş" in oz)

shutil.rmtree(kok, ignore_errors=True)
print("SONUC: " + ("HEPSI GECTI" if not kalan else "KALAN: " + ", ".join(kalan)))
