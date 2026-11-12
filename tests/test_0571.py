"""0.5.71: yapay zekâ köken adımı (kutuphane/koken.py): cevap çözme, kapalıyken atlama, çevirici eski sürümse atlama."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kutuphane import koken, yz  # noqa: E402


def test_cevap_cozme():
    kel = ["mahmuzuyla", "kargaşa", "Charakter"]
    cevap = json.dumps([{"no": 1, "koken": "ar", "kok": "mahmuz", "yazilis": "مهمیز", "anlam": "çivili demir"},
                        {"no": 2, "koken": "tr", "kok": "kargaşa"},
                        {"no": 3, "koken": "de", "kok": "Charakter", "okunus": "Karakter"},
                        {"no": 9, "koken": "tr"}, {"no": 2, "koken": "?"}], ensure_ascii=False)
    k = koken.cevaplari_coz(kel, "```json\n" + cevap + "\n```", "m")
    assert [x["kelime"] for x in k] == kel
    assert k[0]["yazilis"] == "مهمیز" and k[2]["okunus"] == "Karakter" and k[0]["model"] == "m"


def test_kapaliyken_atlanir(monkeypatch):
    monkeypatch.setattr(yz, "acik", lambda: False)
    assert koken.kokenleri_sor(["bir metin"])["durum"] == "atlandi"


def test_eski_cevirici_atlanir(monkeypatch):
    monkeypatch.setattr(yz, "acik", lambda: True)
    monkeypatch.setattr(koken, "_bilinmeyenler", lambda m: None)
    assert koken.kokenleri_sor(["bir metin"])["durum"] == "atlandi"


def test_sahte_akis(monkeypatch):
    monkeypatch.setenv("STUDYO_YZ_SAHTE", "1")
    monkeypatch.setattr(yz, "acik", lambda: True)
    monkeypatch.setattr(koken, "_bilinmeyenler", lambda m: ["kargaşa", "egemen"])
    yazilan = []
    monkeypatch.setattr(koken, "_kaydet", lambda k: (yazilan.extend(k), {"onayli": len(k), "kontrol": 0})[1])
    o = koken.kokenleri_sor(["kargaşa egemen"])
    assert o["durum"] == "tamam" and o["onayli"] == 2 and [x["kelime"] for x in yazilan] == ["kargaşa", "egemen"]
