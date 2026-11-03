"""0.5.66: daha önce işlenip Stüdyo'dan kaldırılmış kitap yeniden verilince uyarı (arsiv.bul / arsiv.mesaj).
İzler: islenmis.json kaydı ve dedplay klasöründeki EPUB/M4B çıktıları (bu sürümden önce silinenler için)."""
import os, sys, tempfile
kok = tempfile.mkdtemp(prefix="t0566-")
os.environ["DATA_DIR"] = os.path.join(kok, "data")
os.environ["DEDPLAY_DIR"] = os.path.join(kok, "dedplay")
os.environ["CIKTI_DIR"] = os.path.join(kok, "dedplay", "EPUB")
for k in ("data", "dedplay/EPUB/Türkçe", "dedplay/EPUB/Osmanlıca", "dedplay/M4B"):
    os.makedirs(os.path.join(kok, k), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kutuphane import arsiv as A  # noqa: E402

def dokun(rel):
    open(os.path.join(kok, "dedplay", rel), "w").close()

# önceden silinmiş (kayıt yok) kitapların çıktıları
dokun("EPUB/Türkçe/Filozofların Tutarsızlığı - Gazzâlî.epub")
dokun("EPUB/Osmanlıca/Filozofların Tutarsızlığı - Gazzâlî.epub")
dokun("M4B/Filozofların Tutarsızlığı - Gazzâlî - 1.m4b")
dokun("M4B/Filozofların Tutarsızlığı - Gazzâlî - 2.m4b")
dokun("M4B/Varlık ve Zaman - Heidegger.m4b")

hata = []
def bekle(ad, epub, ses, kayit=False):
    iz = A.bul(ad)
    if bool(epub or ses or kayit) != (iz is not None):
        hata.append(f"{ad}: bulunma {iz is not None}, beklenen {not not (epub or ses or kayit)}"); return
    if iz and (len(iz["epub"]), len(iz["ses"]), iz["kayit"] is not None) != (epub, ses, kayit):
        hata.append(f"{ad}: {len(iz['epub'])} epub, {len(iz['ses'])} ses, kayıt {iz['kayit'] is not None}")

bekle("Gazzali - Filozoflarin Tutarsizligi.pdf", 2, 2)       # "Yazar - Başlık", Türkçe harfsiz
bekle("Filozofların Tutarsızlığı.epub", 2, 2)
bekle("filozoflarin tutarsizligi - gazzali.pdf", 2, 2)        # çıktı adıyla aynı biçim
bekle("Heidegger - Varlık ve Zaman.pdf", 0, 1)
bekle("Varlık.pdf", 0, 0)                                    # yalnız başlığın bir parçası: uyarı yok
bekle("Kitab-ı Yeni.pdf", 0, 0)
bekle("ab.pdf", 0, 0)                                        # çok kısa ad

# işlenmiş kitap silinince kaydı kalır (çıktıları silinmiş olsa da)
d = {"baslik": "Şâtibî El-Muvâfakât", "yazar": "Şâtibî", "kaynak_kimlik": "/kaynak/Kitaplar/Muvafakat Cilt 1.pdf",
     "eklendi": 1730000000, "epublar": [{"dosya": "x.epub"}], "studyo": {"is": 12}}
if not A.kaydet("Muvafakat-Cilt-1-abc123", d, dosyalar_silindi=True):
    hata.append("kayıt yazılmadı")
if A.kaydet("bos-abc123", {"baslik": "Yarım Kalan", "asama": "sırada"}):
    hata.append("işlenmemiş kitap kaydedildi")
bekle("Muvafakat Cilt 1.pdf", 0, 0, kayit=True)               # kaynak dosya adıyla
bekle("Şatibi El-Muvafakat.epub", 0, 0, kayit=True)           # kitabın adıyla
bekle("Yarım Kalan.pdf", 0, 0)
m = A.mesaj("Muvafakat Cilt 1.pdf", A.bul("Muvafakat Cilt 1.pdf"))
for parca in ("arşivde mevcut", "seslendirmeye gönderilmişti", "dosyaları da silindi", "Yeniden işlensin mi?"):
    if parca not in m:
        hata.append(f"mesajda yok: {parca}")
m2 = A.mesaj("Filozofların Tutarsızlığı.epub", A.bul("Filozofların Tutarsızlığı.epub"))
if "Sesli kitap:" not in m2 or "EPUB:" not in m2:
    hata.append("mesajda çıktılar yok: " + m2)

print("\n".join(hata) or "test_0566: hepsi geçti")
sys.exit(1 if hata else 0)
