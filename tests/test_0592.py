"""0.5.92: EPUB'da XML'de yasak denetim karakteri temizlenir; başlıkla başlayan sayfada numara sonraki paragraftan silinir."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

hata = 0
def ok(k, m):
    global hata
    print(("GECTI " if k else "HATA  ") + m)
    hata += 0 if k else 1

# 5) EPUB: XML'de yasak denetim karakteri temizlenir (Harfler Kitabı: 0x8, 0x1c; dipnotta 0x15)
from kutuphane import epub as E
ok(E.XM("a\x08b\x1cc\x0bd") == "abc d" and E.X("<x\x00>") == "&lt;x&gt;", "denetim karakterleri silinir, \\x0b boşluk olur")

# 6) sayfa başlıkla başlıyorsa numarası sonraki paragraftan silinir (İdeal Devlet "26 oldukça ona…")
from kutuphane import sayfa_basi as SB
kit = {"kunye": {"baslik": {"tr": "X"}}, "bloklar": [
    {"id": "a", "tur": "p", "metin": {"tr": "önceki paragraf bitti."}},
    {"id": "b", "tur": "baslik", "metin": {"tr": "Yüce Tanrı hakkında"}, "sayfalar": [{"no": "26", "konum": {"tr": 0}}]},
    {"id": "c", "tur": "p", "metin": {"tr": "26 oldukça ona daha çok yaklaşırız."}},
    {"id": "d", "tur": "baslik", "metin": {"tr": "Başka"}, "sayfalar": [{"no": "30", "konum": {"tr": 0}}]},
    {"id": "e", "tur": "p", "metin": {"tr": "1917 yılında oldu."}}]}
SB.temizle(kit)
ok([b["metin"]["tr"] for b in kit["bloklar"]][2] == "oldukça ona daha çok yaklaşırız." and kit["bloklar"][4]["metin"]["tr"] == "1917 yılında oldu.",
   "başlıktan sonraki sayfa numarası silinir, başka sayı kalır")
print("SONUC:", "HEPSI GECTI" if not hata else f"{hata} HATA")
sys.exit(1 if hata else 0)
