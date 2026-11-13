"""0.5.76: kesik köken cevabından tam nesneler kurtarılır."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kutuphane import koken  # noqa: E402

KELIMELER = ["kalem", "zor", "masa"]


def test_tam_cevap():
    c = '[{"no":1,"koken":"ar","kok":"kalem","yazilis":"قلم"},{"no":2,"koken":"fa","kok":"zor","yazilis":"زور"}]'
    assert [k["kelime"] for k in koken.cevaplari_coz(KELIMELER, c, "m")] == ["kalem", "zor"]


def test_kesik_cevap():
    c = '```json\n[{"no":1,"koken":"ar","kok":"kalem","yazilis":"قلم"},\n{"no":2,"koken":"fa","kok":"zor","yazilis":"زور"},\n{"no":3,"koken":"it","ok'
    assert [k["kelime"] for k in koken.cevaplari_coz(KELIMELER, c, "m")] == ["kalem", "zor"]


def test_bos_cevap():
    assert koken.cevaplari_coz(KELIMELER, "", "m") == []
    assert koken.cevaplari_coz(KELIMELER, "üzgünüm", "m") == []
