"""0.5.41 gerileme testi (9 kitap denetimi, 17 Ekim; kaynak_8 arşivi): Türkçe metin düzeltmeleri.
1) EPUB dipnotları: hedefi kendisi de geri bağlantı olan dipnot (Calibre "[10]", Word "(*)" kutusu) bağlanır; başlıktaki "[15]"
   bağlı atıf olur; "{{n}}(*)" / "{{n}}(Haşiye)" çift işaret teke iner; not başındaki "(*):" ve sonundaki "↵" atılır.
2) Tire: "kulları- nın", "bildirilmiş- tir", "te- âlâ", "İs- lâm" birleşir; metin kaynağında yalnız geçerli birleşim ("kadar- minhac-ı"
   kalır) ve kelime içi heceleme ("Mev-lânâ", "ta-mamiyle"; "mânâ-yı", "meyl-üt", "Müşarün-ileyh", "bî-aman" kalır).
3) Noktasız I: Ikincisi, ILGILI, Imparator, TARIHI -> İ; IŞIK, AYNI, ILIK, II, XXI, yabancı ad (Studies in Islamic Law) kalır.
4) Noktalama: cemiyet:içinde, ki,sen -> boşluk; uyma.yı, burha.na -> tek kelime; da.onun -> "da onun"; vb.de, s.a.v. kalır.
5) Başlıklar: etiketsiz EPUB'da (Makâlât) "GiRiŞ" -> "GİRİŞ" başlık; başlık etiketli "S- …" soru satırı paragraf; kısa başlık kalır.
6) Kitap sonu: ISBN satırı, tek başına sayı, taranmış kitapta arka kapak çöpü silinir; temiz son paragraf kalır.
7) Sayfa numarası: "gel-" + "47 miştir" -> "gelmiştir". 8) Künye: "Kitabu'l -Burhan", "SİKKE-İ TASDÎK-İ GAYBÎ", küçük harfli ad.
Çalıştırma: docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/app:/k -e TR_KELIME=/app/app/data/tr_kelime.txt berzahbey/dedplay-studyo:latest python tests/test_0541.py"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kutuphane import kaynak as S
from app import duzelt as DZ

kalan = []


def dene(ad, kosul):
    print(("GECTI " if kosul else "KALDI ") + ad)
    if not kosul:
        kalan.append(ad)


def epub_yap(belgeler, toc=None):
    from ebooklib import epub
    book = epub.EpubBook()
    book.set_identifier("t0541")
    book.set_title("Deneme")
    book.set_language("tr")
    ogeler = []
    for ad, govde in belgeler:
        c = epub.EpubHtml(title=ad, file_name=ad, lang="tr")
        c.content = "<html><body>" + govde + "</body></html>"
        book.add_item(c)
        ogeler.append(c)
    book.toc = toc(ogeler) if toc else ogeler
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ogeler
    yol = os.path.join(tempfile.mkdtemp(), "deneme.epub")
    epub.write_epub(yol, book)
    return yol


uzun = " ".join(["Bu paragraf metnin gövdesidir ve yeterince uzundur, okuyucu burada asıl konuyu bulur."] * 2)

# 1a) Calibre biçimi: atıf "[10]", dipnottaki hedef de geri bağlantı (Özün Özü)
yol = epub_yap([
    ("metin.xhtml", '<h1>Birinci Mertebe</h1><p>Bu makama ebu’l-vakt<sup><a href="not.xhtml#fn10" id="fn10-geri">[10]</a></sup> adı verilir. '
                    + uzun + '</p><h1>İkinci Mertebe: Âlem-i Ceberût <sup><a href="not.xhtml#fn15" id="fn15-geri">[15]</a></sup></h1><p>' + uzun + '</p>'),
    ("not.xhtml", '<h1>Notlar</h1><p><sup>[<a href="metin.xhtml#fn10-geri" id="fn10">10</a>]</sup> Baba anlamına gelen eb kelimesi.</p>'
                  '<p><sup>[<a href="metin.xhtml#fn15-geri" id="fn15">15</a>]</sup> Ceberût: kudret âlemi.</p>')])
og, notlar, _ = S.epub_oku(yol)
metinler = " | ".join(o["metin"] for o in og)
dene("geri bağlantılı dipnot bağlanır", len(notlar) == 2 and "Baba anlamına gelen eb kelimesi." in notlar.values())
dene("metinde [10] kalmaz, atıf olur", "[10]" not in metinler and "ebu’l-vakt{{n" in metinler)
dene("dipnot paragrafı metne girmez", "Baba anlamına" not in metinler)
bas = [o["metin"] for o in og if o["tur"] == "baslik"]
dene("başlıktaki [15] bağlı atıf olur", any(b.startswith("İkinci Mertebe: Âlem-i Ceberût") and "{{n" in b for b in bas)
     and not any("[15]" in b for b in bas))

# 1b) Word biçimi (Âsâr-ı Bedîiyye): "(*)" atıf, dipnot kutusu birkaç paragraf
yol = epub_yap([
    ("metin.xhtml", '<p>Şu bürhanımız <a href="not.xhtml#_ftn3" id="_ftnref3"><span><sup>(*)</sup></span></a> değil yalnız erkânı. ' + uzun + '</p>'),
    ("not.xhtml", '<div id="ftn3"><p><a href="metin.xhtml#_ftnref3" id="_ftn3"><sup>(*)</sup></a> Dikkat, <span>dik</span><span>kat!</span></p>'
                  '<p><span>–Naşir–</span></p></div>')])
og, notlar, _ = S.epub_oku(yol)
dene("(*) atıflı Word dipnotu bağlanır", list(notlar.values()) == ["Dikkat, dikkat! –Naşir–"])
metinler = " | ".join(o["metin"] for o in og)
dene("metinde (*) kalmaz", "(*)" not in metinler and "bürhanımız {{n0001}} değil" in metinler)

# 1c) Risale EPUB'u: numaralı atıftan sonra kaynağın kendi işareti, not başında etiket ve geri oku
yol = epub_yap([
    ("metin.xhtml", '<p>“bir esarettir” diyor. <a href="notlar.xhtml#footnote-0009"><sup>9</sup></a><a id="fnreturn-0009"></a>(*) ' + uzun + '</p>'
                    '<p>Eski Said’in <a href="notlar.xhtml#footnote-0010"><sup>10</sup></a>(Haşiye-2) kuvvesi. ' + uzun + '</p>'),
    ("notlar.xhtml", '<p id="footnote-0009">(*): Mahkemeye karşı bir parça. <a href="metin.xhtml#fnreturn-0009">↵</a></p>'
                     '<p id="footnote-0010">( Haşiye-2): Yani o zaman. <a href="metin.xhtml#fnreturn-0010">↵</a></p>')])
og, notlar, _ = S.epub_oku(yol)
metinler = " | ".join(o["metin"] for o in og)
dene("çift işaret teke iner", "diyor. {{n0001}} " in metinler and "{{n0002}} kuvvesi" in metinler and "(*)" not in metinler and "Haşiye" not in metinler)
dene("not etiketi ve geri oku atılır", sorted(notlar.values()) == ["Mahkemeye karşı bir parça.", "Yani o zaman."])

# 2) tire
for once, sonra in [("kulları- nın", "kullarının"), ("bildirilmiş- tir", "bildirilmiştir"), ("te- âlâ", "teâlâ"), ("İs- lâm", "İslâm"),
                    ("muh- temelen", "muhtemelen"), ("Al-lah", "Allah"), ("istiyorlardı- bildikleri", "istiyorlardı- bildikleri"),
                    ("müstesna- yüzlerinizi", "müstesna- yüzlerinizi")]:
    dene(f"tire: {once}", DZ.satir_ici_tireleri_birlestir(once) == sonra)
dene("tarif kalır: (el-afve)", DZ.satir_ici_tireleri_birlestir("bağışlamayı (el- afve) emret") == "bağışlamayı (el-afve) emret")
dene("metin kaynağı: ara söz kalır", DZ.satir_ici_tireleri_birlestir("bu kadar- minhac-ı Kur'an", yalniz_bosluklu=True, kati=True)
     == "bu kadar- minhac-ı Kur'an")
dene("metin kaynağı: geçerli birleşim", DZ.satir_ici_tireleri_birlestir("kendi- lerine", yalniz_bosluklu=True, kati=True) == "kendilerine")
for once, sonra in [("Mev-lânâ", "Mevlânâ"), ("Mev-lânâ'nın", "Mevlânâ'nın"), ("ta-mamiyle", "tamamiyle"), ("Mu-hammed", "Muhammed"), ("kö-tülükleriyle", "kötülükleriyle"),
                    ("mânâ-yı", "mânâ-yı"), ("meyl-üt", "meyl-üt"), ("Vâcib-ül", "Vâcib-ül"), ("Müşarün-ileyh", "Müşarün-ileyh"),
                    ("bî-aman", "bî-aman"), ("el-ân", "el-ân"), ("bir-iki", "bir-iki"), ("Kur'an-ı", "Kur'an-ı"), ("hüsn-ü", "hüsn-ü")]:
    dene(f"kelime içi tire: {once}", DZ.ic_tireleri_birlestir(once) == sonra)

# 3) noktasız I
dene("noktasız I düzelir", S._noktasiz_I_onar("Ikincisi ILGILI Imparator TARIHI Iyice Islam İSLAM") == "İkincisi İLGİLİ İmparator TARİHİ İyice İslam İSLAM")
dene("geçerli kelime ve Roma rakamı kalır", S._noktasiz_I_onar("IŞIK AYNI ILIK IRAK II XXI ÂISha") == "IŞIK AYNI ILIK IRAK II XXI ÂISha")
dene("yabancı başlık kalır", S._noktasiz_I_onar("Schacht, Studies in Islamic Law, Oxford") == "Schacht, Studies in Islamic Law, Oxford")

# 4) noktalama
dene("noktalama boşluğu", S._noktalama_boslugu("cemiyet:içinde ki,sen da.onun uyma.yı burha.na ile.de") ==
     "cemiyet: içinde ki, sen da onun uymayı burhana ile de")
dene("kısaltma ve harf dizisi kalır", S._noktalama_boslugu("vb.de s.a.v. www.dedplay.nl") == "vb.de s.a.v. www.dedplay.nl")

# 5) başlıklar
dene("GiRiŞ büyük harf", S._buyuk_harf_onar("GiRiŞ") == "GİRİŞ")
og = [{"tur": "p", "metin": t, "boy": 0} for t in
      ["GiRiŞ", uzun, "Şems-i Tebrizî Kimdir?", uzun, "İlk Çağları", uzun, "Onu göz yaşlarınla tertemiz yıkamadıkça!", uzun, "BİRİNCİ BÖLÜM", uzun]]
S._etiketsiz_basliklar(og)
dene("etiketsiz başlıklar", [o["metin"] for o in og if o["tur"] == "baslik"] == ["GİRİŞ", "Şems-i Tebrizî Kimdir?", "İlk Çağları", "BİRİNCİ BÖLÜM"])
og2 = [{"tur": "p", "metin": t, "boy": 0} for t in ["Giriş", uzun, "Sonuç", uzun]]
S._etiketsiz_basliklar(og2)
dene("3'ten az aday: dokunulmaz", all(o["tur"] == "p" for o in og2))
dene("S- soru satırı başlık değil", S._baslik_cumlesi("S- Kimsin? Ölsen yine sen misin?") and S._baslik_cumlesi("VEHİM: Bu cemiyet tefrika verir?"))
dene("başlık biçimli satır başlık kalır", not S._baslik_cumlesi("Hayat-ı İhtilal; Mevt-i Zekat, Hayat-ı Ribadan Çıkmış")
     and not S._baslik_cumlesi("BİRİNCİ MAKAM") and not S._baslik_cumlesi("وَ اِنَّ الْفُجَّارَ لَفِى جَحِيمٍ"))
dene("uzun cümle başlık değil", S._baslik_cumlesi("Evet biz aşağıya iniyoruz, onlar yukarıya çıkıyor. Bunun iki sebebi vardır."))

# 6) kitap sonu
p = lambda t: {"tur": "p", "metin": t, "boy": 0}
govde = [p(uzun), p("Âlemlerin rabbi yüce Allah'a hamdolsun.")]
son = S._kitap_sonu_temizle(govde + [p("ISBN 975-290-632-X"), p("579")], True)
dene("ISBN ve sayı silinir (EPUB)", [o["metin"] for o in son] == [uzun, "Âlemlerin rabbi yüce Allah'a hamdolsun."])
son = S._kitap_sonu_temizle(govde + [p("Rudst agggle mam Sazali"), {"tur": "baslik", "metin": "Sınat. Zfl", "boy": 0}, p("—- em")], False)
dene("taranmış kitapta arka kapak çöpü silinir", [o["metin"] for o in son] == [uzun, "Âlemlerin rabbi yüce Allah'a hamdolsun."])
son = S._kitap_sonu_temizle(govde + [p("151 vd., 158 vd., 169, 197.")], False)
dene("dizin satırı kalır", len(son) == 3)
son = S._kitap_sonu_temizle(govde + [p("Elkuddüsü Elmüheyminü Elazizü"), p("( وإن الى ربك المنتهى ) «Muhakkak ki")], False)
dene("Esmâ ve Arapçalı satır kalır", len(son) == 4)
dene("temiz son kalır (EPUB çöp sayılmaz)", len(S._kitap_sonu_temizle(govde + [p("Rudst agggle mam Sazali")], True)) == 3)

# 7) sayfa numarası
og = [p("bu görev İslamda sürüp gel-"), p("47 miştir. İl pazar kontrol memuru.")]
S._kopuk_paragraflari_birlestir(og)
dene("sayfa numarası atılır, kelime birleşir", len(og) == 1 and "sürüp gelmiştir. İl pazar" in og[0]["metin"])
og = [p("Bu sayfa bitti."), p("12 kişi geldi.")]
S._kopuk_paragraflari_birlestir(og)
dene("cümle sonundan sonra sayı kalır", len(og) == 2 and og[1]["metin"] == "12 kişi geldi.")

# 8) künye
dene("künye: Kitabu'l-Burhan", S._kunye_bicimi("Kitabu'l -Burhan") == "Kitabu'l-Burhan")
dene("künye: büyük harf", S._kunye_bicimi("SİKKE-İ TASDÎK-İ GAYBÎ") == "Sikke-i Tasdîk-i Gaybî")
dene("künye: küçük harf", S._kunye_bicimi("iman ve küfür muvazeneleri") == "İman ve Küfür Muvazeneleri")
dene("künye: düzgün ad kalır", S._kunye_bicimi("Özün Özü") == "Özün Özü" and S._kunye_bicimi("Asar-ı Bediye") == "Asar-ı Bediye")

print("SONUC: HEPSI GECTI" if not kalan else f"SONUC: {len(kalan)} TEST KALDI")
