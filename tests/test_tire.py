"""0.5.29 gerileme testi (Ey Oğul, Esmaul hüsna, Felsefenin Temel İlkeleri, Filozofların Tutarsızlığı: ABBYY metin katmanı):
1) Satır sonundaki yumuşak tire (U+00AD) heceleme tiresidir: kelime birleşir ("bü-" + "tün" -> "bütün"; eskiden "bü tün").
2) Kopuk paragraf birleşirken önceki satır sonu tiresiyle bitiyorsa kelime birleşir ("gay-" + "ya kuyusu" -> "gayya").
3) Dosya adında yazar varsa onunla hiç kelime paylaşmayan bilgi alanı yazarı (KUTLUG, Emin: tarayan kişi) kullanılmaz.
4) Surya'nın uydurduğu LaTeX komutları ve kendini tekrarlayan İngilizce ("the control of the control of") atılır; gerçek
   İngilizce alıntı ("(The Incoherence of the Philosophers)") kalır.
5) Gövdeden küçük puntolu dipnot satırının numarası ("(1) Necm sûresi/39") kenar numarası sayılıp silinmez; gövde boyundaki
   gerçek kenar numarası ("(18) edilebilen") yine silinir."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kutuphane import kaynak as S
from app import textsrc as TS

kalan = []


def dene(ad, kosul):
    print(("GECTI " if kosul else "KALDI ") + ad)
    if not kosul:
        kalan.append(ad)


# 1) yumuşak tire
dene("satır sonu yumuşak tire tireye döner", TS.norm("anlatılan bü\u00ad") == "anlatılan bü-")
dene("kelime içi yumuşak tire silinir", TS.norm("ke\u00adli\u00adme") == "kelime")
dene("satırlar birleşince kelime birleşir",
     TS.join_lines(TS.norm("anlatılan bü\u00ad") + "\n" + TS.norm("tün meseleler")) == "anlatılan bütün meseleler")
dene("rakamdan sonraki yumuşak tire tire olmaz", TS.norm("1999\u00ad") == "1999")

# 2) kopuk paragraf
dene("kopuk: tireli satır kelimeyi birleştirir", S._kopuk_ekle("Cehennemin gay-", "ya kuyusunu boylayacaklar.")
     == "Cehennemin gayya kuyusunu boylayacaklar.")
dene("kopuk: tiresiz satır boşlukla eklenir", S._kopuk_ekle("bir şey", "daha var.") == "bir şey daha var.")
dene("kopuk: büyük harfle başlayan devamda tire kalır", S._kopuk_ekle("Hasan-", "Basrî dedi").startswith("Hasan-"))
og = [{"tur": "p", "metin": "kendi nefsiyle kaim olan diye yo-"}, {"tur": "p", "metin": "rumlamaları gibi. Onlar"}]
S._kopuk_paragraflari_birlestir(og)
dene("kopuk paragraf birleştirmesi (yo- rumlamaları)", len(og) == 1 and "diye yorumlamaları gibi" in og[0]["metin"])

# 3) künye
for yol, meta, yazar in [("/x/Imam_Gazali_-_Felsefenin_Temel_İlkeleri.pdf", "KUTLUG", "İmam Gazali"),
                         ("/x/imam_Gazali_-_Esmaul_hüsna.pdf", "Emin", "İmam Gazali"),
                         ("/x/Gazali_-_Ihya.pdf", "Ebû Hâmid el-Gazâlî", "Hâmid el-Gazâlî"),
                         ("/x/Kitap_Adı.pdf", "Ahmet Yılmaz", "Ahmet Yılmaz")]:
    ab, ay = S._dosya_adindan(yol)
    sonuc = S._kunye_sec({"yazar": meta}, ab, ay, os.path.basename(yol)[:-4])
    dene(f"künye yazarı {os.path.basename(yol)} + {meta} -> {yazar} (çıkan {sonuc[1]})",
         sonuc[1] == yazar or (yazar.startswith("Hâmid") and sonuc[1].endswith(yazar)))  # Ebû/Ebu: kelime listesine bağlı

# 4) Surya uydurması
for t, beklenen in [(r"ŞÖHRET DÜŞKÜNÜ OLMAMAKTIR\| \bigtriangleup \|\bigtriangleup", "ŞÖHRET DÜŞKÜNÜ OLMAMAKTIR"),
                    ("Nâziât Sûresi, âyet: 1-2 the control of the control of the contract of t", "Nâziât Sûresi, âyet: 1-2"),
                    ("الساعة The contract of the contract of", "الساعة"),
                    ("and the State and the the control of the control of the contract of", ""),
                    ("Tehâfüt el-Felâsife (The Incoherence of the Philosophers) adlı eser",
                     "Tehâfüt el-Felâsife (The Incoherence of the Philosophers) adlı eser"),
                    ("Bu kitapta the sözü geçer.", "Bu kitapta the sözü geçer."),
                    ("Allah teâlâ ve Resûlü", "Allah teâlâ ve Resûlü")]:
    dene(f"uydurma: {t[:40]!r}", S._surya_uydurma(t) == beklenen)


# 5) kenar numarası / dipnot numarası
def satir(t, h, top):
    return {"text": t, "h": h, "top": top, "bot": top + h, "x0": 30, "x1": 300, "n": len(t.split()), "kalin": False}


sayfalar = []
for k in range(1, 11):
    rows = [satir("Bu sayfada uzun bir gövde satırı yer alıyor", 11.0, 50 + 12 * j) for j in range(8)]
    rows.append(satir(f"({k + 17}) edilebilen bir şey daha var burada", 11.0, 160))  # kenar numarası (aslın sayfası)
    rows.append(satir(f"({k}) Necm sûresi/39", 8.5, 280))                          # dipnot
    sayfalar.append(rows)
sonuc = S._kenar_numarasi_dizisi(sayfalar)
dipler = [r["text"] for rows in sonuc for r in rows if r["h"] < 9]
govde = [r["text"] for rows in sonuc for r in rows if "edilebilen" in r["text"]]
dene("dipnot numarası korunur", all(t.startswith("(") for t in dipler) and len(dipler) == 10)
dene("gövdedeki kenar numarası silinir", all(t.startswith("edilebilen") for t in govde))

print("SONUC: HEPSI GECTI" if not kalan else f"SONUC: {len(kalan)} TEST KALDI")
