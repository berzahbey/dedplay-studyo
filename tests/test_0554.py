"""0.5.54: harekesiz Arap harfli satır seslendirmede okunmaz; harekeli âyet, Türkçe mealli satır ve Türkçe satır değişmez."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.ses import ses_metni, harekesiz_arap_satiri

OKUNMAZ = ["بسم الله الرحمن الرحيم والصلاة", "المراد من هذا الكلام (Kehf, 110)", "دولت عليه عثمانيه نك اداره سى",
           "(Kehf, 110) قال الشيخ رحمه الله تعالى"]
OKUNUR = ["بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ", "قال رسول الله صلى الله عليه وسلم: Allah Resulü buyurdu ki namaz dinin direğidir",
          "Bugün hava güzel.", "Bu satırda tek Arapça kelime var: الله", "الله أكبر"]

def test():
    for t in OKUNMAZ:
        assert harekesiz_arap_satiri(t.replace("", "").replace("", "")), t
        assert ses_metni(t) == "", t
    for t in OKUNUR:
        assert not harekesiz_arap_satiri(t), t
        assert ses_metni(t).strip(), t
    assert ses_metni("Bugün hava güzel.") == "Bugün hava güzel."

if __name__ == "__main__":
    test(); print("test_0554 tamam")
