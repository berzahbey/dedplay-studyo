"""0.5.22 gerileme testi (Kudsi Hadisler, İmam Gazâlî, 48 s. metin katmanlı PDF):
1) Tek sayfanın katmanı harf değil sembolse ('!"#$%&'(#)*&(') yalnız o sayfa yeniden okunur; bütün kitap OCR'a gitmez.
2) Her bölümün yeni sayfada başladığı kitapta sayfa başında tekrar eden bölüm başlığı ("1. KUDSİ HADİS") ve açılış cümlesi
   ("Yüce Allah (c.c) şöyle buyurmaktadır:") üst bilgi sayılıp silinmez; gerçek üst bilgi (kitap adı) yine silinir."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kutuphane import kaynak as S

kalan = []


def dene(ad, kosul):
    print(("GECTI " if kosul else "KALDI ") + ad)
    if not kosul:
        kalan.append(ad)


def satir(t, h=12.0):
    return {"text": t, "h": h, "top": 0, "bot": h, "n": len(t.split()), "kalin": False}


# 1) sembol katmanı
cop = [satir('!"#$%&\'(#)*&(\''), satir('!"#$%&&\'($)"*"+$,-.&#$/0.012\'34\'5617'), satir("89.$:5#2;<&0=$>'?'$(@A2#4$#4B$/#?$/'?'$(@A2#4$#5#?@$C#D#1$D#$30&&'1626$;?0?$(@A2#4@?#")]
turkce = [satir("Yüce Allah (c.c) şöyle buyurmaktadır: Ey âdemoğlu! Öleceğini kesinlikle bilen bir kimsenin, nasıl sevindiğine şaşarım!"),
          satir("Yine, hesaba çekileceğine kesin olarak inanan bir kimsenin nasıl mal topladığına şaşarım! (s.a.v) 2/313, 438")]
dene("Sembol katmanı çöp sayılır", S._katman_cop(cop))
dene("Türkçe katman (noktalama, rakam, parantez dahil) çöp sayılmaz", not S._katman_cop(turkce))
dene("Kısa sayfa (100 karakterden az) çöp sayılmaz", not S._katman_cop([satir("12 - 13 ...")]))

# 2) bölüm açılışları: 40 bölüm, her biri yeni sayfada; üç bölüm iki sayfaya taşıyor (devam sayfasında açılış yok)
sayfalar = []
for n in range(1, 41):
    sayfalar.append([satir(f"{n}. KUDSİ HADİS" + (":" if n in (2, 36) else ""), 14),
                     satir("Yüce Allah (c.c) şöyle buyurmaktadır:" if n not in (2, 36) else "Yüce Allah c.c. şöyle buyurmaktadır:"),
                     satir('"Ey âdemoğlu!'), satir("Öleceğini kesinlikle bilen bir kimsenin, nasıl sevindiğine")]
                    + ([] if n in (12, 28, 37) else [satir('şaşarım!"')]))
    if n in (12, 28, 37):
        sayfalar.append([satir("devam eden metin burada sürer ve"), satir('bölüm burada biter."')])
sonuc = S._tekrar_edenleri_at(sayfalar)
metin = [r["text"] for rows in sonuc for r in rows]
dene("40 bölüm başlığı korunur", sum(1 for t in metin if "KUDSİ HADİS" in t) == 40)
dene("40 açılış cümlesi korunur", sum(1 for t in metin if "şöyle buyurmaktadır" in t) == 40)

# gerçek üst bilgi: kitap adı her sayfanın başında, önceki sayfa çoğu zaman cümle ortasında biter (dipnot noktayla bitse de)
sayfalar = []
for n in range(30):
    son = "ve bu yüzden insan her zaman" if n % 3 else "bu böyledir."
    sayfalar.append([satir("Alemlerin Sırrı", 10), satir("Gövde metni " + "abcçdefgğhıijklmnoöprsştuüvyz"[n % 29] * 3 + " ile başlar ve sürer"), satir(son),
                     satir(f"{n + 1}. Buhârî, Tevhîd, 35.", 8)])
sonuc = S._tekrar_edenleri_at(sayfalar)
metin = [r["text"] for rows in sonuc for r in rows]
dene("Gerçek üst bilgi (kitap adı) yine silinir", not any(t == "Alemlerin Sırrı" for t in metin))
dene("Gövde satırları kalır", sum(1 for t in metin if t.startswith("Gövde metni")) == 30)

# sayfa numaralı üst bilgi ("Alemlerin Sırrı - 14") de silinir
sayfalar = [[satir(f"Alemlerin Sırrı - {n + 3}", 10), satir("Gövde metni burada"), satir("sürer ve")] for n in range(20)]
sonuc = S._tekrar_edenleri_at(sayfalar)
dene("Numaralı üst bilgi silinir", not any("Alemlerin Sırrı -" in r["text"] for rows in sonuc for r in rows))

print("SONUC: HEPSI GECTI" if not kalan else f"SONUC: {len(kalan)} TEST KALDI")
