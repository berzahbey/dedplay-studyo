"""0.5.38 gerileme testi (toplu rapor, 13 Ekim): harf onarımı Arapça/eski imlâ kelimeyi ve ünlüyle başlayan ekten önceki
yumuşamayı bozmaz (uruc, Sebe', harc-ı, bahs, korkuncudur, göğüse, saatlık); OCR'ın düşürdüğü harf yine düzelir (mahser -> mahşer,
eger -> eğer, sey -> şey, Isa -> İsa). Büyük harfli başlık: ILIM -> İLİM (Roma rakamı sanılmaz), INSAN -> İNSAN (İNŞAN değil),
IRAK / ILIK / IRMAK kalır."""
import os, sys
# Türkçe kelime listesi git'te yok, yalnız imajda: kod klasöründen çalışınca imajdakini kullan
_LISTE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "data", "tr_kelime.txt")
if not os.environ.get("TR_KELIME") and not os.path.exists(_LISTE) and os.path.exists("/app/app/data/tr_kelime.txt"):
    os.environ["TR_KELIME"] = "/app/app/data/tr_kelime.txt"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from kutuphane import kaynak as S

kalan = []


def dene(girdi, beklenen, f=S._harf_onar_korumali):
    c = f(girdi)
    print(("GECTI " if c == beklenen else "KALDI ") + girdi + " -> " + c + ("" if c == beklenen else "  (beklenen " + beklenen + ")"))
    if c != beklenen:
        kalan.append(girdi)


S._kitap_baglami_sil()
# korunur
for w in ["uruc", "ferc", "harc-ı", "Sebe'", "bahs", "korkuncudur", "göğüse", "saatlık"]:
    dene(w, w)
# düzelir
for w, d in [("mahser", "mahşer"), ("eger", "eğer"), ("meshur", "meşhur"), ("sahit", "şahit"), ("sey", "şey"), ("Isa", "İsa"),
             ("Allahin", "Allahın"), ("nasil", "nasıl"), ("oruc", "oruç")]:
    dene(w, d)
# kitapta "şerh" sık geçiyorsa Serh -> Şerh
S._kitap_baglami_kur(["şerh şerh şerh bu kitabın şerhi"])
dene("Serh", "Şerh")
S._kitap_baglami_sil()
# büyük harf
for w, d in [("BİRİNCİ BÖLÜM: ILIM", "BİRİNCİ BÖLÜM: İLİM"), ("INSAN", "İNSAN"), ("ILK", "İLK"), ("DIL", "DİL"), ("IRAK", "IRAK"),
             ("ILIK", "ILIK"), ("IRMAK", "IRMAK"), ("III. BÖLÜM", "III. BÖLÜM"), ("XXI", "XXI"), ("IV", "IV")]:
    dene(w, d)
# kitap ı'yı kaybetmiş ("ayni" çok) ama AYNI kalır
S._kitap_baglami_kur(["AYNI ZAMANDA ayni ayni ayni"])
dene("ve AYNI ZAMANDA", "ve AYNI ZAMANDA")
S._kitap_baglami_sil()
dene("ILIM", "İLİM", S.turkce_onar)
dene("IRAK", "IRAK", S.turkce_onar)

print("SONUC: HEPSI GECTI" if not kalan else f"SONUC: {len(kalan)} TEST KALDI")
sys.exit(1 if kalan else 0)
