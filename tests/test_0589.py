"""0.5.89: seslendirmeye yalnız ana metin (Zahir 23 Kasım; İslam Felsefesinde Allah'ın Varlığının Delilleri dinlemesi)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app.ses import ses_metni as S  # noqa: E402
from app.worker import ses_satirlari  # noqa: E402

durum = []
def dene(girdi, beklenen):
    c = S(girdi)
    if c != beklenen:
        durum.append(f"{girdi!r}\n   çıkan {c!r}\n   beklenen {beklenen!r}")

dene("Bu konuda Nazzam (Ölm. H. 231 / M. 845) şöyle söylemiştir:", "Bu konuda Nazzam şöyle söylemiştir:")
dene("Eş'ari (Ölm. H. 33o / M. g4ı ) Allah'ın varlığını isbatlar.", "Eş'ari Allah'ın varlığını isbatlar.")
dene("64 Bak. al - A'râf, ayet: 185.", "")
dene("83 al - En'âm, ayet: 76.", "")
dene("Il Bak. İbn Rüşd, Kitab al - Keşf An Menahic al-Edille, adiyle kamttır. Kur'an'da bunlara benzer âyetler vardır.",
     "Kur'an'da bunlara benzer âyetler vardır.")
dene("Bu da Tanrıdır 12", "Bu da Tanrıdır")
dene('"akıllı insan bilir" 1 . Ebu Huzeyl ise', '"akıllı insan bilir". Ebu Huzeyl ise')
dene("Mehdî Maddi 19 34 sırf sırk 20 17 önce öne 24 21", "")
dene("Mısır: 6, 10, 14, 15, 18, 27.", "")
dene("Hz. Ali 1. Halife oldu.", "Hz. Ali 1. Halife oldu.")
dene("1923 yılında 3 kişi, 25 Mart 1453; sayfa 12 ve 13", "1923 yılında 3 kişi, 25 Mart 1453; sayfa 12 ve 13")
dene("(H. 505) ve (M. 1058) yılında", "(H. 505) ve (M. 1058) yılında")
dene("Sözü geçen 5 nci madde gereğince cisim sonludur.", "Sözü geçen 5 nci madde gereğince cisim sonludur.")
dene("Allah vardır. Bak. Robert Hamand, anılan eser, s. 19 - 23, Paris 1950. Bu böyledir.", "Allah vardır. Bu böyledir.")
s = ses_satirlari("Giriş cümlesi burada.\n29 Karşıtlar ve eşler\n29 Yokluk ve varlık\n31. Kuvvetliler ve zayıflar\n45 BİBLİYOGRAFYA\n"
                  "Son cümle Tanrıdır 12\nYANLIŞ - DOĞRU CETVELİ Sayfa Doğru Satır Yanlış\nTimaios 6 Timaos\n13 25 cisimin cismin\nBitti.")
if s != ["Giriş cümlesi burada.", "Son cümle Tanrıdır", "Bitti."]:
    durum.append(f"ses_satirlari: {s}")
print("\n".join(durum) if durum else "SONUC: HEPSI GECTI")
