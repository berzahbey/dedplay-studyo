"""0.5.86: OCR onarımı (aym -> aynı, soma -> sonra, onlann -> onların, Fiakkında -> Hakkında); doğru ve Arapça kelimeye dokunulmaz."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kutuphane import ocr_onarim as O  # noqa: E402

metin = ("Fiakkında söylenen her şey aym idi. Soma onlann yalmz insamn aklına geldi. Bunu yapacağım ve azm ettim. "
         "Bu kitabın aynı sayfasında sonra okudum; onların sözü doğru idi. Kelile ve Dimne okundu.")
kit = {"kunye": {"asil_dil": "tr"}, "bloklar": [{"metin": {"tr": metin}}], "dipnotlar": {"n0001": {"metin": {"tr": "Soma geldi."}}}}
s = O.kitabi_onar(kit)
t = kit["bloklar"][0]["metin"]["tr"]
for beklenen in ("Hakkında söylenen", "aynı idi", "Sonra onların yalnız insanın", "yapacağım ve azm ettim", "Dimne"):
    assert beklenen in t, (beklenen, t)
assert kit["dipnotlar"]["n0001"]["metin"]["tr"] == "Sonra geldi.", kit["dipnotlar"]
kit2 = {"kunye": {"asil_dil": "en"}, "bloklar": [{"metin": {"tr": "aym"}}]}
assert O.kitabi_onar(kit2) == {}
print("SONUC: HEPSI GECTI", s)
