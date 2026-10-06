"""Tur 2/B: dil denetimi ve tek ekleme yolu. Türkçe olmayan kitap yalnız kendi dilinde EPUB olur (Osmanlıca ve seslendirme yok);
Türkçe kitaptaki âyet ve Arapça ibareler kitabı Arapça yapmaz; Stüdyo'nun eski ekleme adresleri ve ikinci Osmanlıca adımı kapalı.
  docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/app:/k berzahbey/dedplay-studyo:latest python tests/test_dil.py"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
kok = tempfile.mkdtemp()
os.environ["DATA_DIR"] = os.path.join(kok, "k")
os.environ["STUDYO_DATA_DIR"] = os.path.join(kok, "s")
os.makedirs(os.environ["STUDYO_DATA_DIR"], exist_ok=True)
from app import birlesik  # noqa: F401
from app import main as studyo
from fastapi import HTTPException
from kutuphane import depo, kaynak
from kutuphane import kitap as K

B = []


def ok(k, ad):
    B.append(bool(k))
    print(("GECTI " if k else "KALDI ") + ad)


def yaz(ad, metin):
    yol = os.path.join(kok, ad)
    open(yol, "w", encoding="utf-8").write(metin)
    return yol


arapca = ("الحمد لله رب العالمين والصلاة والسلام على سيدنا محمد وعلى آله وصحبه أجمعين. أما بعد فإن العلم نور "
          "يقذفه الله في قلب من يشاء من عباده، وهو أشرف ما يطلبه الطالب. ") * 20
ingilizce = ("The knowledge of God is the highest of all sciences, and it is by this knowledge that the soul finds its "
             "rest. In the following chapters we shall explain the meaning of this claim with care. ") * 20
turkce = ("Bu kitapta Allah'ın isimleri anlatılır ve her biri bir bölümde ele alınır. Kur'an'da şöyle buyrulur: "
          "الحمد لله رب العالمين الرحمن الرحيم مالك يوم الدين. Bu âyetin manası çok derindir ve onun üzerinde durulur. ") * 20

kit = kaynak.cevir(yaz("Arapça Kitap.txt", arapca))
ok(kit["kunye"]["asil_dil"] == "ar" and all("tr" not in b["metin"] for b in kit["bloklar"])
   and any("ar" in b["metin"] for b in kit["bloklar"]), "Arapça metin: asil_dil ar, metin Arapça anahtarında")
ok("ar" in kit["kunye"]["baslik"] and "tr" not in kit["kunye"]["baslik"], "Arapça kitabın adı da kendi dilinde")
ok([e for e, _ in depo.surumler(kit)] == ["arapca"] if depo.surumler(kit) else False,
   f"Arapça kitap yalnız Arapça EPUB {depo.surumler(kit)}")

kit = kaynak.cevir(yaz("English Book.txt", ingilizce))
ok(kit["kunye"]["asil_dil"] == "en" and any("en" in b["metin"] for b in kit["bloklar"]), "İngilizce metin: asil_dil en")

kit = kaynak.cevir(yaz("Türkçe Kitap.txt", turkce))
ok(kit["kunye"]["asil_dil"] == "tr" and any("tr" in b["metin"] for b in kit["bloklar"]),
   "Türkçe kitap, içindeki âyetlerle birlikte Türkçe kalır")
ok(kaynak.metin_dili(["kısa"]) == "tr", "Çok kısa metin Türkçe sayılır")

# depo: Türkçe olmayan kitap için Osmanlıca işi açılmaz
kuyruk = []
depo.is_ekle = lambda is_turu, kid, arg=None, **d: kuyruk.append(is_turu)
depo.epub_uret = lambda kid: None
for ad, metin, beklenen in (("ar.kitap", arapca, []), ("tr.kitap", turkce, ["osmanlica"])):
    kuyruk.clear()
    os.makedirs(depo.klasor(ad), exist_ok=True)
    depo._isle("dosya", ad, yaz(ad + ".txt", metin))
    ok(kuyruk == beklenen, f"{ad}: sonraki iş {kuyruk} (beklenen {beklenen})")

# Stüdyo'nun eski ekleme yolları ve ikinci Osmanlıca adımı kapalı
for ad, f, arg in (("from-text", studyo.job_from_text, studyo.PastedText(title="x", text="y")),
                   ("redo-osm", studyo.redo_osm, 1)):
    try:
        f(arg)
        ok(False, f"{ad} kapalı")
    except HTTPException as e:
        ok(e.status_code == 410, f"{ad} kapalı (410)")
ok(studyo.job_from_kutuphane is not None, "Kütüphane'den gelen yol (from-kutuphane) açık")

print("SONUC:", "HEPSI GECTI" if all(B) else f"{B.count(False)} TEST KALDI")
sys.exit(0 if all(B) else 1)
