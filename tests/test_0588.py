"""0.5.88: sayfa başındaki sütun başlığı ve sayfa numarası silinir; sayfada bölünen paragraf birleşir."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kutuphane import sayfa_basi as S  # noqa: E402

def p(i, t, sayfa=None):
    b = {"id": i, "tur": "p", "metin": {"tr": t}}
    if sayfa:
        b["sayfalar"] = [{"no": str(sayfa), "konum": {"tr": 0}}]
    return b

kit = {"kunye": {"baslik": {"tr": "İdeal Devlet (El Medinetü'l Fazıla)"}, "asil_dil": "tr"}, "bloklar": [
    {"id": "b1", "tur": "baslik", "metin": {"tr": "Önsöz"}},
    p("b2", "Farabî bütün ilimleri"), p("b3", "ÖNSÖZ okumuş ve yazmıştı.", 9),
    p("b4", "Bu konu büyük"), p("b5", "ÖNSÖZ önem taşır.", 10), p("b6", "ÖNSÖZ", 11), p("b7", "Yeni paragraf başlıyor.", None),
    p("b8", "Öyle olunca"), p("b9", "16 da kendisini teşkil eden.", 16),
    p("b10", "Şehir halkı"), p("b11", "EL-MEDtNETÜ’L FÂZILA bazan yönelirler.", 48),
    p("b12", "Cümle bitti."), p("b13", "ANKARA Üniversitesi yayını.", 50)]}
o = S.temizle(kit)
t = [b["metin"]["tr"] for b in kit["bloklar"]]
assert "Farabî bütün ilimleri okumuş ve yazmıştı." in t, t
assert "Bu konu büyük önem taşır." in t, t
assert "Öyle olunca da kendisini teşkil eden." in t, t
assert "Şehir halkı bazan yönelirler." in t, t
assert "ANKARA Üniversitesi yayını." in t, t           # tek geçen büyük harfli kelime başlık sayılmaz
assert "ÖNSÖZ" not in " ".join(t), t
print("SONUC: HEPSI GECTI", o)
