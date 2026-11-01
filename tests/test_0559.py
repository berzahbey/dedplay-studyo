"""0.5.59: bütün cevaplar saklıyken (istek gitmeden) biten denetimin raporu, günlük sınır doluyken de yazılır."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kutuphane import denetim as D, yz  # noqa: E402

hata = []


class Dolu:          # yz.Gemini gibi: hiç istek yok, .ad sınır dolu diye hata atar
    sayac = {"cagri": 0}
    kullanilan = {}

    @property
    def ad(self):
        raise yz.GunlukSinir("dolu")


class Kullanildi(Dolu):
    sayac = {"cagri": 3}
    kullanilan = {"gemini-x-lite": 3}


for model, bekle in ((Dolu(), "saklı cevaplar"), (Kullanildi(), "model: -"), (None, "model: -")):
    dn = D.Denetci(tempfile.mkdtemp(), model=model)
    try:
        r = dn.rapor_metni("Kitap")
        if bekle not in r:
            hata.append(f"{type(model).__name__}: '{bekle}' yok: {r.splitlines()[1]}")
    except Exception as e:
        hata.append(f"{type(model).__name__}: rapor hata verdi: {type(e).__name__}")
print("\n".join(hata) or "test_0559: hepsi geçti")
sys.exit(1 if hata else 0)
