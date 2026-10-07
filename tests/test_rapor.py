"""0.5.23 gerileme testi: kitap raporu. Rapor metni DEĞİŞTİRMEZ, yalnız kaydeder; hata verse bile kitap işlenir.
Değişiklik, silinen, yapı denetimi (numaralı başlık eksikleri, sayfa atlaması, dipnot eşleşmesi), şüpheli kelime/paragraf."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
GECICI = tempfile.mkdtemp()
os.environ.setdefault("DATA_DIR", GECICI)
from kutuphane import kaynak as S, rapor as R

kalan = []


def dene(ad, kosul):
    print(("GECTI " if kosul else "KALDI ") + ad)
    if not kosul:
        kalan.append(ad)


# 1) kayıt: fark ve silindi
R.basla()
R.fark("Bu \ue00212\ue003 sey cok güzel bir kitap.", "Bu \ue00212\ue003 şey çok güzel bir kitap.")
R.fark("Hiç değişmeyen paragraf.", "Hiç değişmeyen paragraf.")
R.fark("Nasır ’ ın evi", "Nasır’ın evi")   # yalnız boşluk/noktalama
R.silindi("üst/alt bilgi satırı", "Alemlerin Sırrı")
R.silindi("üst/alt bilgi satırı", "Alemlerin Sırrı")
kit = {"kunye": {"baslik": {"tr": "Deneme"}, "yazar": {"tr": "Yazar"}, "asil_dil": "tr", "kaynak": {"ad": "d.pdf"},
                 "cikarma": {"onarim": {"harf": True}}},
       "bloklar": [{"tur": "baslik", "seviye": 1, "metin": {"tr": "GİRİŞ"}, "sayfalar": [{"no": "5"}]}]
       + [{"tur": "baslik", "seviye": 2, "metin": {"tr": f"{n}. KUDSİ HADİS"}} for n in (1, 2, 3, 5, 6)]
       + [{"tur": "p", "metin": {"tr": "Yüce Allah şöyle buyurmaktadır {{n0001}}"}, "sayfalar": [{"no": "6"}, {"no": "7"}]},
          {"tur": "p", "metin": {"tr": "Kalbi temiz olmayana şaşarım {{n0002}}"}, "sayfalar": [{"no": "9"}]},
          {"tur": "p", "metin": {"tr": "Rudst agggle mam Sazali"}},
          {"tur": "p", "metin": {"tr": "12 Buhârî, Tevhîd, 35; Müslim, İmân, 312."}}],
       "dipnotlar": {"n0001": {"metin": {"tr": "Bk. Buhârî, Tevhîd, 35."}}}}
r = R.bitir(kit, {"sayfa": 10, "ocr": 2}, ".pdf")
dg = {(d["once"], d["sonra"]): d for d in r["degisiklik"]}
dene("Kelime değişikliği kaydedilir (sey -> şey, cok -> çok)", ("sey cok", "şey çok") in dg)
dene("Değişikliğin sayfası bilinir", dg.get(("sey cok", "şey çok"), {}).get("sayfa") == "12")
dene("Yalnız boşluk/noktalama ayrı sayılır", r["degisiklik_toplam"]["noktalama_bosluk"] == 1 and len(dg) == 1)
dene("Silinen üst bilgi sayılır", r["silinen"]["üst/alt bilgi satırı"][0]["adet"] == 2)
s = r["yapi"]["numarali_baslik_sorunlari"]
dene("Numaralı başlıkta eksik bulunur (4)", s and s[0]["eksik"] == [4])
dene("Sayfa atlaması bulunur (7 -> 9)", [7, 9] in r["yapi"]["sayfa"]["atlama"])
dene("Metni olmayan dipnot işareti bulunur", r["yapi"]["dipnot"]["metni_olmayan_isaret"] == 1)
dene("Dipnota benzeyen gövde paragrafı bulunur", any("Buhârî" in t for t in r["yapi"]["dipnota_benzeyen_paragraf"]))
dene("Çöp satır şüpheli paragraf", any("Rudst" in p["metin"] for p in r["supheli_paragraf"]))
dene("Şüpheli kelime listesinde 'agggle'", any(d["kelime"] == "agggle" for d in r["supheli_kelime"]))
dene("Doğru kelime şüpheli sayılmaz ('kalbi', 'temiz')", not any(d["kelime"] in ("kalbi", "temiz") for d in r["supheli_kelime"]))
kl = os.path.join(GECICI, "kitaplar", "deneme-abc123")
R.kaydet(kl, r)
dene("rapor.json ve rapor.txt yazılır", os.path.exists(os.path.join(kl, "rapor.json")) and "NUMARALI BAŞLIK" in open(os.path.join(kl, "rapor.txt"), encoding="utf-8").read())
t = R.toplu(os.path.join(GECICI, "kitaplar"))
dene("Toplu rapor kitabı içerir", "[deneme-abc123]" in t and "DEDPLAY TOPLU RAPOR — 1 kitap" in t)

# 2) gerçek akış: metin dosyası -> kitap; rapor oluşur, metin aynı kalır
yol = os.path.join(GECICI, "Deneme Kitabı - Yazar.txt")
with open(yol, "w", encoding="utf-8") as f:
    f.write("BİRİNCİ BÖLÜM\n\nBu kitap tamamen doğru yazılmış bir metindir. Her kelimesi yerindedir.\n\n"
            "İkinci paragraf da hatasızdır; müttaki kimseler, bahs edilen konular ve âhiret korunmalıdır.\n")
kit2 = S.cevir(yol, None, {"yol": yol})
r2 = R.al()
dene("Metin kaynağında rapor oluşur", r2 and r2.get("kitap", {}).get("tur") == "txt")
dene("Hatasız metinde değişiklik yok", r2 and r2["degisiklik_toplam"]["farkli"] == 0)
metin = " ".join(b["metin"]["tr"] for b in kit2["bloklar"])
dene("Metin korunur (müttaki, bahs, âhiret)", all(k in metin for k in ("müttaki", "bahs", "âhiret")))

# 3) rapor hata verse de kitap işlenir
eski = R.olustur
R.olustur = lambda *a, **k: 1 / 0
kit3 = S.cevir(yol, None, {"yol": yol})
r3 = R.al()
R.olustur = eski
dene("Rapor hatası kitabı durdurmaz", kit3 and r3 and "ZeroDivisionError" in r3.get("hata", ""))
dene("Rapor hatası metni değiştirmez", " ".join(b["metin"]["tr"] for b in kit3["bloklar"]) == metin)

print("SONUC: HEPSI GECTI" if not kalan else f"SONUC: {len(kalan)} TEST KALDI")
