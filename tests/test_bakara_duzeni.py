"""0.5.40 gerileme testi (Bakara meali PDF'i, 17 Ekim denetimi):
1) Asılı girintili numaralı ayetler ("2. Bu, …" sol kenarda, devam satırı numaranın sağında) tek paragraf olur; sıradan paragraf girintisi
   (ilk satır içeride) ve numarasız kitaplar etkilenmez.
2) Ardışık numaralı madde, numaradan sonra boşluk olmasa da yeni paragraf ("10. Amel…" / "11.Gök…"); ardışık olmayan sayı ("1915.") değil.
3) Satır sonu tiresi: Arapça harf-i tarif tireyle kalır (el-hâşi'în, es-selvâ, bi'l-ma'rûf); ara söz çizgisi boşlukla kalır
   (istiyorlardı- bildikleri); hece bölünmesi birleşir (kitap-ların, değer-lendirme).
4) Açılış tırnağından önceki boşluk silinmez (Size 'Göklerin, ve 'Hıtta'); kopuk kesme ekleri yine birleşir (Nasır ’ ın -> Nasır’ın).
Çalıştırma: docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/app:/k -e TR_KELIME=/app/app/data/tr_kelime.txt berzahbey/dedplay-studyo:latest python tests/test_bakara_duzeni.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kutuphane import kaynak as S
from app import textsrc as TS
from app import duzelt as DZ

kalan = []


def dene(ad, kosul):
    print(("GECTI " if kosul else "KALDI ") + ad)
    if not kosul:
        kalan.append(ad)


def satir(t, x0, top, x1=520):
    return {"text": t, "h": 13.0, "top": top, "bot": top + 13, "x0": x0, "x1": x1, "n": 0, "kalin": False, "blok": 0, "ocr": False}


def paragraflar(rows, asili=None):
    return [m for _, m, _ in S._sayfa_paragraflari(rows, 595, 13.0, 0.0, asili=asili)]


# 1) asılı girinti: sayfadaki satırların çoğu numaralı (Bakara 1. sayfası gibi): eskiden devam satırları ayrı paragraftı
bakara = [satir("1. Elif-Lâm-Mîm.", 68, 57, 177), satir("2. Bu, kendisinde hiçbir şüphe bulunmayan Kitap’tır. Sakınanlar (el-muttaqîn)", 68, 84),
          satir("için bir hidayet rehberidir.", 93, 99, 241), satir("3. Onlar ki; gayba inanırlar, namazı kılarlar ve kendilerine verdiğimiz", 68, 126),
          satir("rızıktan harcarlar.", 93, 141, 197), satir("12.Dikkat edin! Onlar bozguncuların ta kendileridir.", 68, 168),
          satir("13.Onlara: \"İnsanların inandığı gibi siz de inanın\" denildiğinde: \"Beyinsizlerin", 68, 195),
          satir("(es-sufehâ) inandığı gibi mi inanalım?\" derler.", 93, 210, 300)]
asili = S._asili_girinti([bakara, bakara], 13.0)
dene("asılı girinti bulunur (68, 93)", asili == (68, 93))
p = paragraflar(bakara, asili)
dene("ayet tek paragraf", p[1] == "2. Bu, kendisinde hiçbir şüphe bulunmayan Kitap’tır. Sakınanlar (el-muttaqîn) için bir hidayet rehberidir.")
dene("her ayet ayrı paragraf (5)", len(p) == 5 and p[3].startswith("12.") and p[4].startswith("13."))
# sıradan kitap: ilk satır girintili paragraflar; asılı girinti bulunmaz, paragraflar eskisi gibi
duz = [satir("Birinci paragrafın ilk satırı burada başlıyor ve uzun", 93, 57), satir("devam ediyor, burada bitiyor.", 68, 72, 300),
       satir("İkinci paragraf yine içeriden başlıyor ve uzun bir", 93, 87), satir("satırla devam edip bitiyor.", 68, 102, 300),
       satir("1. Madde başlıklı bir paragraf içeriden başlıyor ve", 93, 117), satir("sol kenardan devam ediyor.", 68, 132, 300)] * 1
dene("sıradan girintide asılı girinti yok", S._asili_girinti([duz] * 3, 13.0) is None)
dene("sıradan girintide paragraflar aynı", len(paragraflar(duz)) == 3)

# 2) ardışık numaralı madde, boşluksuz
tekvir = [satir("10. Amel defterleri açıldığı zaman,", 68, 57, 250), satir("11.Gök sıyrılıp yüzüldüğü (küşitat) zaman,", 68, 72, 280),
          satir("12.Cehennem kızıştırıldığı zaman,", 68, 87, 250)]
dene("boşluksuz ardışık numara yeni paragraf", len(paragraflar(tekvir)) == 3)
yil = [satir("1. Birinci madde burada başlıyor ve satırın sonuna kadar gidiyor", 68, 57),
       satir("1915.Yılında olanlar da bu maddeye dahildir.", 68, 72, 300)]
dene("ardışık olmayan sayı ayırmaz", len(paragraflar(yil)) == 1)

# 3) satır sonu tiresi
dene("harf-i tarif tireyle kalır", TS.join_lines("duyanlar (el-\nhâşi'în) dışındakilere") == "duyanlar (el-hâşi'în) dışındakilere")
dene("es-selvâ", TS.join_lines("bıldırcın (es-\nselvâ) indirdik") == "bıldırcın (es-selvâ) indirdik")
dene("bi'l-ma'rûf", TS.join_lines("uygun (bi’l-\nma’rûf) tutun") == "uygun (bi’l-ma’rûf) tutun")
dene("ara söz çizgisi boşlukla kalır", TS.join_lines("fetih istiyorlardı-\nbildikleri (hakikat)") == "fetih istiyorlardı- bildikleri (hakikat)")
dene("hece bölünmesi birleşir", TS.join_lines("kitap-\nların hepsi") == "kitapların hepsi")
dene("hece bölünmesi birleşir (değerlendirme)", TS.join_lines("değer-\nlendirme yapıldı") == "değerlendirme yapıldı")
dene("satır içi tarif birleşmez", DZ.satir_ici_tireleri_birlestir("artanı (el-afve). Faiz (er-ribâ)") == "artanı (el-afve). Faiz (er-ribâ)")
dene("satır içi hece tiresi yine birleşir", DZ.satir_ici_tireleri_birlestir("Merini-ler geldi") == "Meriniler geldi")
dene("ara söz çizgisi DZ'de de kalır", DZ.satir_ici_tireleri_birlestir("zalim olanlar müstesna- yüzlerinizi") == "zalim olanlar müstesna- yüzlerinizi")

# 4) açılış tırnağı
d = S._duzelt(['haber verince (Allah): "Size \'Göklerin ve yerin gaybını', "girin ve 'Hıtta' (Bizi bağışla)", "Nasır ’ ın kitabı", "Ahmed 'in sözü"])
dene("açılış tırnağı ayrı kalır", d[0].endswith("\"Size 'Göklerin ve yerin gaybını") and d[1] == "girin ve 'Hıtta' (Bizi bağışla)")
dene("kopuk kesme eki birleşir", d[2] == "Nasır’ın kitabı" and d[3] == "Ahmed'in sözü")

# 5) 0.5.40b (arşiv karşılaştırmasından): büyük harfli özel ad önünde tarif, kısa parça hece bölünmesi, büyük harfli ek
dene("tarif + büyük harfli ad", TS.join_lines("Abdullah el-\nBelhî (ö. 199)") == "Abdullah el-Belhî (ö. 199)")
dene("kısa parça hece bölünmesi birleşir", TS.join_lines("mutlaka alı-\nkordu. Çünkü") == "mutlaka alıkordu. Çünkü")
dene("büyük harfli ek birleşir", S._duzelt(["el-kadîm Û ’İN bir nüktesi"])[0] == "el-kadîm Û’İN bir nüktesi")

# 6) 0.5.40c: açılmış ara sözün kapanış çizgisi, parça kısa olsa da (Kitabü't-Tevhid, Âsâr-ı Bediiyye)
dene("ara söz kapanışı (satır sonu)", TS.join_lines("zaten -dilsizlik değil-\nacz alternatifine") == "zaten -dilsizlik değil- acz alternatifine")
dene("ara söz kapanışı (da-)", TS.join_lines("-hakikatini kavramak mümkün olmasa da-\nâlemin yoktan") == "-hakikatini kavramak mümkün olmasa da- âlemin yoktan")
dene("ara söz kapanışı (EPUB)", DZ.satir_ici_tireleri_birlestir("Fâtıra –tâbir caiz ise- hummalı bir faaliyetle") == "Fâtıra –tâbir caiz ise- hummalı bir faaliyetle")
dene("ara söz yoksa kısa parça birleşir", TS.join_lines("düşmanlığı tercih edip taa-\ntinden yüz") == "düşmanlığı tercih edip taatinden yüz")

# 7) 0.5.40d: ara söz içinde de sağ parça ekse (kelime değilse) hece bölünmesidir
dene("ara söz içinde hece bölünmesi (satır sonu)", TS.join_lines("çoğunun -ki bunlar cismiyetle-\nrinden söz edilmesine") == "çoğunun -ki bunlar cismiyetlerinden söz edilmesine")
dene("ara söz içinde hece bölünmesi (EPUB)", DZ.satir_ici_tireleri_birlestir("çoğunun -ki bunlar cismiyetle- rinden söz") == "çoğunun -ki bunlar cismiyetlerinden söz")
dene("ara söz kapanışı büyük harf", TS.join_lines("-Açıklamalı Tercüme-\nEbû Mansur") == "-Açıklamalı Tercüme- Ebû Mansur")

print("SONUC: HEPSI GECTI" if not kalan else f"SONUC: {len(kalan)} TEST KALDI")
