"""0.5.62: seste "Allâh" -> "Allah" (ses modeli â'dan önceki l'yi ince okuyor). Yalnız llâh; öteki şapkalar değişmez."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.ses import ses_metni  # noqa: E402
VAKA = [("Allâh'ın Resûlü buyurdu.", "Allah'ın Resûlü buyurdu."), ("Allâhü Teâlâ buyurur.", "Allahü Teâlâ buyurur."),
        ("Abdullâh b. Ömer, Resûlullâh ve Bismillâh, inşâallâh.", "Abdullah b. Ömer, Resûlullah ve Bismillah, inşâallah."),
        ("ALLÂH", "ALLAH"), ("Allah'a hamd olsun.", None), ("Bunu bilmek lâzımdır, lâkin İslâm ahlâkı.", None)]
hata = [f"{g!r} -> {ses_metni(g)!r}" for g, b in VAKA if ses_metni(g) != (g if b is None else b)]
print("\n".join(hata) or "test_0562: hepsi geçti")
sys.exit(1 if hata else 0)
