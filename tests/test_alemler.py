"""0.5.18 ("Âlemlerin Sırrı", İmam Gazâlî, taranmış PDF, Surya) bulguları: harf kaybı, "bir çok", izafet "-1",
forma işareti, Yunan harfi, konuşma çizgisi. Örnekler kitabın kendi satırlarından."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import logging
logging.disable(logging.CRITICAL)
from kutuphane import kaynak as S
from app import duzelt as DZ

kalan = 0


def esit(ad, a, b):
    global kalan
    if a == b:
        print("GECTI", ad)
    else:
        kalan += 1
        print("KALDI", ad, "\n   beklenen:", repr(b), "\n   bulunan :", repr(a))


# 1) birleştirme: iki gerçek kelime ayrı kalır, OCR'ın böldüğü kelime birleşir
B = DZ.bolunmus_kelimeleri_birlestir
esit("bir çok ayrı", B("Şurası da bir gerçektir ki, bir çok ilim adamları"), "Şurası da bir gerçektir ki, bir çok ilim adamları")
esit("bir şey ayrı", B("Mutlaka olacak bir şey hakkındaki duan"), "Mutlaka olacak bir şey hakkındaki duan")
esit("pek çok ayrı", B("pek çok kimse"), "pek çok kimse")
esit("oldu ğundan birleşir", B("oldu ğundan sonra"), "olduğundan sonra")
esit("kar şılık birleşir", B("kar şılık verdi"), "karşılık verdi")
esit("Allah ın birleşir", B("Allah ın adı"), "Allahın adı")
esit("birçok (kitabın yazımı) kalır", B("birçok ilim"), "birçok ilim")

# 2) harf kaybı
H = S._harf_kaybi_onar
esit("I -> İ", H("Imamı Gezâlî hayatını, Isa ve Insanlar"), "İmamı Gezâlî hayatını, İsa ve İnsanlar")
esit("Irak, Islandı kalır", H("Irak'a gitti. Islandı, çamurlandı."), "Irak'a gitti. Islandı, çamurlandı.")
esit("ı kaybı", H("Allahin rahmeti. Nasil olur bu, anlatir"), "Allahın rahmeti. Nasıl olur bu, anlatır")
esit("ş kaybı (listede harfsiz yazım)", H("Her sey Allah'tandır. Hayir!"), "Her şey Allah'tandır. Hayır!")
esit("büyük harfli", H("ALEMLERİN SIRRI ve AHIRET ILIMLERINE"), "ALEMLERİN SIRRI ve AHİRET İLİMLERİNE")
esit("izafet -1", H("Cenab-1 Hak. Levh-1 Mahfuz? Kur'an-1 Kerim"), "Cenab-ı Hak. Levh-i Mahfuz? Kur'an-ı Kerim")
korunan = "cevab nakl zikr olup tutup Gezâlî lûtuf Ebû dıye fısk bürhan mu'cize etdi yokdur Hattâ Salih kasd isbat"
esit("eski imlâ, şapka, baskı hatası korunur", H(korunan), korunan)
esit("Arapça kalır", H("قل هو الله احد"), "قل هو الله احد")

# 3) forma işareti
F = S._forma_deseni("Alemlerin Sırrı")
esit("forma: dipnot sonunda", F.sub("", "Dikkatli olmak gerekir..(Mütercim) Alemlerin Sırrı — 14").rstrip(),
     "Dikkatli olmak gerekir..(Mütercim)")
esit("forma: tek başına", F.sub("", "Alemlerin Sırrı - 3").strip(), "")
esit("forma: sayfa işaretli", F.sub("", "son satır. Alemlerin Sırrı — 2 \ue002120\ue003"), "son satır. \ue002120\ue003")
esit("forma: şapkalı ad", S._forma_deseni("Âlemlerin Sırrı").sub("", "x Alemlerin Sırrı — 8"), "x ")
esit("sure atfı kalır", F.sub("", "El-Bakara — 2"), "El-Bakara — 2")
esit("cümledeki ad kalır", F.sub("", "Alemlerin Sırrı ve ahiret ilimleri"), "Alemlerin Sırrı ve ahiret ilimleri")
esit("tek kelimelik ad: desen yok", S._forma_deseni("Mesnevî"), None)

# 4) Yunan harfi
esit("εy -> ey", S._surya_harfleri("yoksun olan εy gafil!"), "yoksun olan ey gafil!")
esit("Yunanca kelime kalır", S._surya_harfleri("λόγος kelimesi"), "λόγος kelimesi")

# 5) konuşma çizgisi
uzun = ["— Evet, dedi."] * 10
esit("kısa çizgi uzun olur", S._konusma_cizgileri(uzun + ["- Hayır!", "«- İşte hediyen!", "\ue00212\ue003- Nasıl?", "3 - Hizmetçin"])[10:],
     ["— Hayır!", "«— İşte hediyen!", "\ue00212\ue003— Nasıl?", "3 - Hizmetçin"])
esit("kısa çizgili kitap değişmez", S._konusma_cizgileri(["- Evet"] * 20 + ["— Hayır"] * 10)[0], "- Evet")
esit("az örnekte değişmez", S._konusma_cizgileri(["— a"] * 3 + ["- b"])[3], "- b")

print("SONUC: HEPSI GECTI" if not kalan else "SONUC: %d TEST KALDI" % kalan)
