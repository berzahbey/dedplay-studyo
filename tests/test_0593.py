"""0.5.93 (kalite taraması 25 Kasım, 66 kitap): seslendirmede sure/âyet numarası "(40/16)", çapraz atıf "(bk. HAVÂLE)", "bk." ile
kaynak gösteren cümle, tek paragrafa birleşmiş dizin, Arapça sayfanın Latin OCR çöpü okunmaz; yıl "(508/1115)", miras payı "(1/4)",
DİA çeviriyazısı kalır. Türkçe metinde "262 - KİTAP ADI" sayfa başlığı silinir."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app.ses import ses_metni, ocr_copu, dizin_satiri
from kutuphane import sayfa_basi as SB
B = []
def ok(k, m):
    B.append(bool(k)); print(("GECTI " if k else "KALDI ") + m)

ok(ses_metni('– “Ona götürecek vesileyi arayınız.” (5/35) Bunun tefsiri şöyle:') == '– “Ona götürecek vesileyi arayınız.” Bunun tefsiri şöyle:', "(5/35) âyet numarası okunmaz")
ok(ses_metni("açıklanmaktadır (en-Nebe’ 78/23). Şu halde") == "açıklanmaktadır. Şu halde", "(en-Nebe’ 78/23) okunmaz")
ok(ses_metni("dayanırlar (Markos, 10/17-18; 14/28, 17/3). İznik") == "dayanırlar. İznik", "(Markos, 10/17-18; …) okunmaz")
ok("(508/1115)" in ses_metni("esir aldı (508/1115). Bundan sonra") and "(7/628)" in ses_metni("fethi sırasında (7/628) babası"), "hicrî/milâdî yıl kalır")
ok("(1/4)" in ses_metni("eş (1/4) pay alır"), "miras payı (1/4) kalır")
ok(ses_metni("kelâm terimi (bk. İMAN).") == "kelâm terimi." and ses_metni("alınmıştır (aş. bk.). Bezzâr") == "alınmıştır. Bezzâr", "(bk. İMAN), (aş. bk.) okunmaz")
ok(ses_metni("Diğer faaliyetlerin listesi için bk. Syed Abdul Vahid, A Bibliography of Iqbal, Karachi 1965. Sonra şair öldü.") == "Sonra şair öldü.",
   "bk. ile kaynak gösteren cümle okunmaz")
ok(ses_metni("Bu söz (bk. aşağıda) doğrudur.") == "Bu söz doğrudur.", "parantez içi bk. yalnız parantez olarak çıkar, cümle kalır")
idx = "İNDEKS abd Allah 75 abd el-Câmi 70 el-abd el-kâmil 80 abd el-Melik 75 abd er-Rabb 75 abstracta 25 adem 12 ahad 40, 41 ahadiyye 33 akl 90 " \
      "akl el-evvel 91 alem 3 amel 15 ayn 22 ayan 44 batın 60 cem 50 cevher 70 ilm 80 insan 81 kalb 33 kemal 31 nefs 55 nur 66 ruh 77 sırr 88."
ok(dizin_satiri(idx) and ses_metni(idx) == "", "tek paragraf dizin okunmaz")
par = "Bu bölümde 1920 yılında 3 kişi 4 köyden 5 kasabaya gitti ve 6 gün kaldı. Sonra 7 gün daha 8 köyde kaldılar ve 9 ay sonra döndüler. " \
      "Bu yolculuk 10 yıl sürdü, 11 kişi öldü, 12 kişi kaldı. Toplam 13 köy gezildi ve 14 kasaba görüldü."
ok(not dizin_satiri(par), "sayılı anlatı paragrafı dizin sayılmaz")
cop = "• J ı./ J '-.r.:>\" oJoo 0iᡨٿ ƺlk;J\\ aiJ,-.:.ı':J_,A.JI ı) ƻ ᡧŏ._jJ'ÜJ -.:.ı':l_,A.JI"
ok(ocr_copu(cop) and ses_metni(cop) == "", "Arapça sayfanın Latin OCR çöpü okunmaz")
dia = "” bölümü el-Ǿİlelü’ś-śaġīr adıyla anılmıştır. Bezzâr’ın el-Müsnedü’l-kebîrü’l-muǾallel’inde bulunur."
ok(not ocr_copu(dia) and ses_metni(dia) == dia, "DİA çeviriyazısı çöp değil")
kit = {"kunye": {"baslik": {"tr": "Fususu'l-Hikem Anahtarları"}}, "bloklar": [
    {"id": "a", "tur": "p", "metin": {"tr": "Önceki cümle bitti. 262 - FUSUSU'L HİKEM ANAHTARLARI söylüyor: “Nefis durdu” dedi."}},
    {"id": "b", "tur": "p", "metin": {"tr": "1984 - BÜYÜK DOĞU dergisi çıktı."}}]}
SB.temizle(kit)
ok(kit["bloklar"][0]["metin"]["tr"] == "Önceki cümle bitti. söylüyor: “Nefis durdu” dedi." and kit["bloklar"][1]["metin"]["tr"] == "1984 - BÜYÜK DOĞU dergisi çıktı.",
   "'262 - KİTAP ADI' sayfa başlığı silinir, başka büyük harfli söz kalır")
print("SONUC:", "HEPSI GECTI" if all(B) else f"{B.count(False)} TEST KALDI")
sys.exit(0 if all(B) else 1)
