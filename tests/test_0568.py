"""0.5.68: Kütüphane rafı = dedplay klasörü. Kitaplar biçim/dil klasörlerinden ve M4B'den adla toplanır; Stüdyo kaydı
çıktı adıyla bağlanır; EPUB bölümleri temizlenmiş HTML olarak okunur (betik/olay/resim yok); yol klasör dışına çıkamaz."""
import os, sys, tempfile, zipfile
kok = tempfile.mkdtemp(prefix="t0568-")
D = os.path.join(kok, "dedplay")
os.environ.update(DATA_DIR=os.path.join(kok, "data"), DEDPLAY_DIR=D, CIKTI_DIR=os.path.join(D, "EPUB"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kutuphane import depo, raf  # noqa: E402
hata = []
for k in ("EPUB/Türkçe", "EPUB/Osmanlıca", "PDF/Türkçe", "M4B", "MP3/Kitap Bir - Yazar"):
    os.makedirs(os.path.join(D, k), exist_ok=True)


def epub_yaz(yol, bolumler, nav=False):
    with zipfile.ZipFile(yol, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", '<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">'
                   '<rootfiles><rootfile full-path="OEBPS/p.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        man = ['<item id="kapak" href="kapak.xhtml" media-type="application/xhtml+xml"/>',
               '<item id="kunye" href="kunye.xhtml" media-type="application/xhtml+xml"/>']
        spine = ['<itemref idref="kapak"/>', '<itemref idref="kunye"/>']
        z.writestr("OEBPS/kapak.xhtml", '<html><body><img src="k.png"/></body></html>')
        z.writestr("OEBPS/kunye.xhtml", '<html><body><p>Kitap Bir</p></body></html>')
        for i, govde in enumerate(bolumler):
            man.append(f'<item id="b{i}" href="metin/b{i}.xhtml" media-type="application/xhtml+xml"/>')
            spine.append(f'<itemref idref="b{i}"/>')
            z.writestr(f"OEBPS/metin/b{i}.xhtml", f'<html xmlns="http://www.w3.org/1999/xhtml"><head><title>x</title><style>p{{}}</style></head><body>{govde}</body></html>')
        z.writestr("OEBPS/p.opf", '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
                   '<dc:title>Kitap Bir</dc:title></metadata><manifest>' + "".join(man) + '</manifest><spine>' + "".join(spine) + '</spine></package>')


ep = os.path.join(D, "EPUB/Türkçe/Kitap Bir - Yazar.epub")
epub_yaz(ep, ['<h1>GİRİŞ</h1><p onclick="x()">Metin <a href="#n1">1</a> &amp; devam.</p><script>alert(1)</script><img src="r.png"/>',
              '<h2 class="b">BİRİNCİ <span>BÖLÜM</span></h2><p>İkinci.</p>'])
epub_yaz(os.path.join(D, "EPUB/Osmanlıca/Kitap Bir - Yazar.epub"), ["<p>متن</p>"])
open(os.path.join(D, "PDF/Türkçe/Kitap Bir - Yazar.pdf"), "wb").write(b"%PDF")
for f in ("Kitap Bir - Yazar - 2.m4b", "Kitap Bir - Yazar - 10.m4b", "Kitap Bir - Yazar - 1.m4b", "Silinmiş Kitap - Biri.m4b", ".gizli.m4b"):
    open(os.path.join(D, "M4B", f), "wb").write(b"0")
depo.durum_yaz("Kitap-Bir-abc123", baslik="Kitap Bir", yazar="Yazar", asama="hazır", cikti=["Türkçe/Kitap Bir - Yazar.epub"],
               epublar=[{"dosya": "a.epub"}], kutuphanede=5)

r = {k["baslik"]: k for k in raf.tara()}
if set(r) != {"Kitap Bir", "Silinmiş Kitap"}: hata.append(f"raf: {sorted(r)}")
k = r.get("Kitap Bir", {})
if [e["dil"] for e in k.get("epub", [])] != ["Türkçe", "Osmanlıca"]: hata.append(f"epub dilleri: {k.get('epub')}")
if k.get("ses") != ["M4B/Kitap Bir - Yazar - 1.m4b", "M4B/Kitap Bir - Yazar - 2.m4b", "M4B/Kitap Bir - Yazar - 10.m4b"]: hata.append(f"ses sırası: {k.get('ses')}")
if k.get("kimlik") != "Kitap-Bir-abc123" or k.get("kutuphanede") != 5: hata.append("Stüdyo kaydı bağlanmadı")
if not k.get("mp3") or k.get("yazar") != "Yazar": hata.append("mp3/yazar")
if r.get("Silinmiş Kitap", {}).get("kimlik") or r.get("Silinmiş Kitap", {}).get("ses") != ["M4B/Silinmiş Kitap - Biri.m4b"]: hata.append("silinmiş kitap")
y = raf.epub_yapi(ep)
if [b["baslik"] for b in y["bolumler"]] != ["Künye", "GİRİŞ", "BİRİNCİ BÖLÜM"]: hata.append(f"bölümler: {[b['baslik'] for b in y['bolumler']]}")
h = raf.epub_bolum(ep, 1)["html"]
for kotu in ("onclick", "<script", "<img", "<a ", "href", "<style"):
    if kotu in h: hata.append(f"temizlenmedi: {kotu} -> {h}")
if "Metin 1 &amp; devam." not in h or "<h1>GİRİŞ</h1>" not in h: hata.append(f"metin bozuk: {h}")
if 'class=' in raf.epub_bolum(ep, 2)["html"]: hata.append("class kaldı")
try:
    raf.epub_bolum(ep, 9); hata.append("olmayan bölüm")
except IndexError:
    pass
for kotu in ("../data/x", "/etc/passwd", "EPUB/../../x", ""):
    g = raf.guvenli(kotu)
    if g and not g.startswith(os.path.realpath(D) + os.sep): hata.append(f"klasör dışı yol kabul edildi: {kotu}")
if not raf.guvenli("EPUB/Türkçe/Kitap Bir - Yazar.epub"): hata.append("geçerli yol reddedildi")
print("\n".join(hata) or "test_0568: hepsi geçti")
sys.exit(1 if hata else 0)
