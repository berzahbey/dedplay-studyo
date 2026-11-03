"""0.5.69: dinleme hızı 0,1 adımla − / + düğmeleriyle (0,5–2,0); okuma ekranında ve listedeki çalarlarda, aynı ayar.
(Davranış Playwright ile denendi; bu test arayüzde düğmelerin ve sınırların varlığına bakar.)"""
import os, re, sys
kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
hata = []
raf = open(os.path.join(kok, "kutuphane/static/raf.html"), encoding="utf-8").read()
ana = open(os.path.join(kok, "kutuphane/static/index.html"), encoding="utf-8").read()
for ad, s in (("raf.html", raf), ("index.html", ana)):
    for p in ('"ses:hiz"', "Yavaşlat (0,1)", "Hızlandır (0,1)", "Math.min(2, Math.max(0.5,", "* 10) / 10", "preservesPitch"):
        if p not in s: hata.append(f"{ad}: yok {p}")
if 'id="hiz"' in raf: hata.append("eski hız seçimi duruyor")
if len(re.findall(r"(?<!function )hizCubugu\(kutu\)", ana)) != 2: hata.append("iki çalarda da hız çubuğu olmalı")
print("\n".join(hata) or "test_0569: hepsi geçti")
sys.exit(1 if hata else 0)
