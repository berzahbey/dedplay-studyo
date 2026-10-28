"""0.5.52: (1) Dedplay Hazırlık'ın okunmaz işareti (<span class="okunmaz" data-ses="yok">) EPUB'dan okunur, metinde kalır, yalnız
seslendirmede atlanır; (2) dipnotun içindeki numaralı liste ("Bunlar: 1- … 12-" ve sonraki sayfada "13- …") yeni dipnot sayılmaz
(Tahrif 1 s.17-18: 18 sahte dipnot paragraf sonuna diziliyordu); (3) tırnaktan sonra gelen 3 haneli dipnot numarası bağlanır
('olmuştur. "214', 'nüsha). ''335').   python tests/test_0552.py"""
import os
import re
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kutuphane import kaynak as KY, kitap as K, cikti  # noqa: E402
from app.ses import ses_metni  # noqa: E402
from app import export  # noqa: E402

hata = 0


def kontrol(ad, kosul):
    global hata
    print(("TAMAM " if kosul else "HATA  ") + ad)
    hata += not kosul


# --- (1) okunmaz işareti
m = "Kimine göre Şiî'dir (B. Lewis, The Middle East), kimine göre {{n0012}} Ali (Şeyh Abduh) Hintli."
t, liste = K.ses_yok_ayir(m)
kontrol("işaretler metinden çıkar, metin aynen kalır", t == "Kimine göre Şiî'dir (B. Lewis, The Middle East), kimine göre {{n0012}} Ali (Şeyh Abduh) Hintli.")
kontrol("iki parça (bitişik işaretler tek parça)", [x["metin"] for x in liste] == ["(B. Lewis, The Middle East)", "(Şeyh Abduh)"])
sade = re.sub(r"\s+", " ", K.NOT_ISARETI.sub("", t)).strip()
isaretli = K.ses_yok_isaretle(sade, liste)
kontrol("Stüdyo parçasında işaretlenir", isaretli.count("") == 2)
kontrol("seslendirmede okunmaz", ses_metni(isaretli) == "Kimine göre Şiî'dir, kimine göre Ali Hintli.")
kontrol("bulunamayan parça atlanır", K.ses_yok_isaretle("başka metin", liste) == "başka metin")
kontrol("biçimlerde (PDF/DOCX/TXT/HTML) işaret yok",
        export._blocks([{"tr": isaretli, "osm": ""}], "tr") == [[("tr", sade)]])

# uçtan uca: küçük EPUB -> kitap -> Stüdyo parçası -> ses
d = tempfile.mkdtemp()
yol = os.path.join(d, "deneme.epub")
govde = ('<p>Birinci paragraf uzunca bir cümledir ve kitabın ana metnidir, okunur. <span class="okunmaz" data-ses="yok">'
         '(Bkz. Nutuk, sh: 434)</span> Sonra devam eder.</p>'
         '<p><span class="okunmaz" data-ses="yok">433 Besim Atalay- a.g.e., sh: 93.</span></p>'
         '<p>Üçüncü paragraf da ana metindir ve olduğu gibi okunur, hiçbir işareti yoktur.</p>')
with zipfile.ZipFile(yol, "w") as z:
    z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
    z.writestr("META-INF/container.xml", '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
               '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    z.writestr("OEBPS/content.opf", '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
               '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">x</dc:identifier><dc:title>Deneme Kitabı</dc:title>'
               '<dc:language>tr</dc:language></metadata><manifest><item id="b" href="b.xhtml" media-type="application/xhtml+xml"/>'
               '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest><spine><itemref idref="b"/></spine></package>')
    z.writestr("OEBPS/nav.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body>'
               '<nav epub:type="toc"><ol><li><a href="b.xhtml">Bölüm</a></li></ol></nav></body></html>')
    z.writestr("OEBPS/b.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>Bölüm</h1>' + govde + '</body></html>')
kit = KY.cevir(yol)
bl = [b for b in kit["bloklar"] if b["tur"] == "p"]
kontrol("EPUB'dan okunur: metin aynen", any("(Bkz. Nutuk, sh: 434) Sonra devam eder." in b["metin"]["tr"] for b in bl))
kontrol("blokta ses_yok saklanır", sum(len((b.get("ses_yok") or {}).get("tr", [])) for b in bl) == 2)
kontrol("kitap metninde işaret karakteri yok", not any(re.search("[]", b["metin"]["tr"]) for b in kit["bloklar"]))
parca = "\n".join(p["tr"] for p in cikti.studyo_parcalari(kit) if p["name"].startswith("Parca_"))
ses = "\n".join(ses_metni(x) for x in parca.split("\n"))
kontrol("seste kaynak yok", "Nutuk" not in ses and "Besim" not in ses)
kontrol("seste ana metin var", "Sonra devam eder." in ses and "Üçüncü paragraf" in ses)

# --- (2) dipnot içindeki numaralı liste (Tahrif 1, sayfa 17-18 satırları)
s16 = ["7 İmam-ı Kastalânî'nin muhalled (klâsik) eseri \"Mevâhibü'l-", "Ledünniye\"de, bunların yirmi beşi şöyle sıralanmış ve haklarında kısa",
       "kısa bilgiler verilmiştir. Bunlar:"] + [f"{i}- Hz. Kişi {i} (r.a.)" for i in range(1, 13)]
a = KY._notlari_bol(s16, "")
kontrol("liste maddeleri notun içinde kalır (tek not: 7)", [n for n, _ in a] == [7] and "12- Hz. Kişi 12" in a[0][1])
s17 = [f"{i}- Hz. Kişi {i} (r.a.)" for i in range(13, 26)] + ["8 Mü'minûn Sûresi, âyet 14.", "Yaratanların en güzelidir!.."]
b = KY._notlari_bol(s17, a[-1][1])
kontrol("sonraki sayfadaki liste devamı önceki nota eklenir, gerçek not 8 ayrı", [n for n, _ in b] == [None, 8] and b[0][1].startswith("13-"))
kontrol("ardışık gerçek notlar bozulmaz", [n for n, _ in KY._notlari_bol(["5- Birinci not.", "6- İkinci not.", "7- Üçüncü not."], "")] == [5, 6, 7])
kontrol("notun kendi içindeki liste (1-, 2-) ve ardından gerçek not", [n for n, _ in KY._notlari_bol(
    ["4 Üç görüş vardır: 1- Birinci görüş.", "2- İkinci görüş.", "3- Üçüncü görüş.", "5 Başka bir not."], "")] == [4, 5])

# --- (3) tırnaktan sonra 3 haneli dipnot numarası
notlar = {214: "n0214", 335: "n0335"}
bag = set()


def bagla(mm):
    g = notlar.get(int(mm.group(1)))
    if g and g not in bag:
        bag.add(g)
        return "{{" + g + "}}"
    return ""


m1 = 'merkezler olmuştur. "214 Sonra'
r1 = KY.TIRNAK_NO.sub(lambda mm: KY._tirnak_no_bagla(mm, m1, notlar, bag, bagla), m1)
kontrol("artık tırnak silinir, not bağlanır", r1 == "merkezler olmuştur.{{n0214}} Sonra")
m2 = '"Bu böyledir" dedi ve "kabul ettik."335'
r2 = KY.TIRNAK_NO.sub(lambda mm: KY._tirnak_no_bagla(mm, m2, notlar, bag, bagla), m2)
kontrol("kapanış tırnağı kalır", r2 == '"Bu böyledir" dedi ve "kabul ettik."{{n0335}}')
m3 = 'sayfada "999 numara'
kontrol("sayfada olmayan numaraya dokunulmaz", KY.TIRNAK_NO.sub(lambda mm: KY._tirnak_no_bagla(mm, m3, notlar, bag, bagla), m3) == m3)

print("SONUC:", "HEPSI GECTI" if not hata else f"{hata} HATA")
sys.exit(1 if hata else 0)
