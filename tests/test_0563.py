"""0.5.63: seslendirmede cümle arasına girenler (sayfa üst/alt bilgisi, telif, yayınevi, kaynak dizisi) okunmaz; satır/sayfa
sonunda kopan cümle ve tireyle bölünen kelime birleşir. Kitabın kendi tekrarları ("Peygamberimiz Aleyhisselam:", "Şiir:") kalır."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.worker import ses_satirlari, kisa_satir_sayilari  # noqa: E402

hata = []
parca = "\n".join([
    "Birinci Bölüm",
    "Allah'ın elçisi mescide girdiğinde orada bulunan sahabilere dönüp iyilik ve doğruluğu şiar",
    "edinenlerden hoşnut olur dedi.",
    "116 • TEFSİRİ KEBİR / TE’VİLÂT",
    "Bu münâsebetlerin özel-",
    "191' ligini idrâk etmek beşerin gücü dâhilinde değildir.",
    "Copyright ©2013 islam-tr.net. Ali Rights Reserved.",
    "el muvafakat",
    "Taberî, Tefsîr, c. 27, s. 48, Hâkim, Müstedrek, c. 2, s. 469, Kurtubî, Tefsîr, c. 17, s. 92.",
    "Peygamberimiz Aleyhisselam:",
    "Bu Türkler kâmilen şiîdir. Bun-",
    "larda muvakkat nikâh var.",
    "TÜRKİYE İŞ BANKASI KÜLTÜR YAYINLARI",
    "Şiir:",
    "Ey aşkın, kıyamet meydanının İsrafili!",
    "Uzun bir satır olup büyük harfle başlayan ikinci satıra",
    "Geçer ve birleşmez.",
    "Hadis, Al-Câmi’, c. II, s. 172 rivayetinde geçen bu söz, kişinin emin olması gerektiğini anlatır.",
])
parts = [{"tr": parca}] + [{"tr": "el muvafakat\nPeygamberimiz Aleyhisselam:"}] * 3
cikti = ses_satirlari(parca, "Şâtibî - El-Muvâfakât", kisa_satir_sayilari(parts))
bekle = [
    "Birinci Bölüm",
    "Allah'ın elçisi mescide girdiğinde orada bulunan sahabilere dönüp iyilik ve doğruluğu şiar edinenlerden hoşnut olur dedi.",
    "Bu münâsebetlerin özelligini idrâk etmek beşerin gücü dâhilinde değildir.",
    "Peygamberimiz Aleyhisselam:",
    "Bu Türkler kâmilen şiîdir. Bunlarda muvakkat nikâh var.",
    "Şiir:",
    "Ey aşkın, kıyamet meydanının İsrafili!",
    "Uzun bir satır olup büyük harfle başlayan ikinci satıra",
    "Geçer ve birleşmez.",
    "Hadis, Al-Câmi’, c. II, s. 172 rivayetinde geçen bu söz, kişinin emin olması gerektiğini anlatır.",
]
if cikti != bekle:
    for i, (a, b) in enumerate(zip(cikti + [""] * 9, bekle + [""] * 9)):
        if a != b:
            hata.append(f"{i}: {a!r}\n   beklenen {b!r}")
# kitap adı tek kez (kapak/başlık) geçiyorsa okunur
if ses_satirlari("Şâtibî\nBir cümle.", "Şâtibî - El-Muvâfakât", {}) != ["Şâtibî", "Bir cümle."]:
    hata.append("tek geçen kitap adı atıldı")
print("\n".join(hata) or "test_0563: hepsi geçti")
sys.exit(1 if hata else 0)
