"""0.5.68: Kütüphane rafı: dedplay klasöründeki bitmiş kitaplar (Stüdyo kaydından bağımsız).

Düzen (Stüdyo yazar): EPUB|PDF|DOCX|TXT|HTML/<Dil>/<Ad>.<uzantı>, M4B/<Ad>.m4b (ya da <Ad> - 1.m4b …), MP3/<Ad>/.
Kitap Stüdyo listesinden silinse de dosyaları burada kalır: okunur (EPUB, salt okunur) ve dinlenir (M4B).
Stüdyo kaydı duruyorsa okuma ekranı Stüdyo'nunkidir (düzeltme yapılabilir)."""
import html
import os
import re
import zipfile
import posixpath
from urllib.parse import unquote

from . import depo
from .katalog import sade

KOK = os.environ.get("DEDPLAY_DIR", "/dedplay")
BICIMLER = ["EPUB", "PDF", "DOCX", "TXT", "HTML"]
SIRA_DIL = ["Türkçe", "Osmanlıca", "Türkçe-Osmanlıca", "Arapça", "Arapça-Türkçe", "İngilizce", "İngilizce-Türkçe"]
SAG_SOL = {"Osmanlıca", "Arapça"}


def guvenli(rel):
    """dedplay içinde göreli yol -> tam yol (dışarı çıkılamaz). Geçersizse None."""
    if not rel or "\x00" in rel:
        return None
    kok = os.path.realpath(KOK)
    tam = os.path.realpath(os.path.join(kok, rel.lstrip("/")))
    return tam if tam.startswith(kok + os.sep) else None


def _ad_parcala(ad):
    if " - " in ad:
        b, y = ad.split(" - ", 1)
        return b.strip(), y.strip()
    return ad, ""


def tara():
    """Raf: [{anahtar, ad, baslik, yazar, epub:[{dil, yol}], dosyalar:[{bicim, dil, yol, boyut}], ses:[yol], mp3, kimlik, kutuphanede}]"""
    kitaplar = {}

    def kitap(ad):
        k = sade(ad)
        if k not in kitaplar:
            b, y = _ad_parcala(ad)
            kitaplar[k] = {"anahtar": k.strip(), "ad": ad, "baslik": b, "yazar": y, "epub": [], "dosyalar": [], "ses": [],
                           "mp3": False, "kimlik": None, "kutuphanede": None, "studyo": None, "tarih": 0}
        return kitaplar[k]

    if not os.path.isdir(KOK):
        return []
    for bicim in BICIMLER:
        bk = os.path.join(KOK, bicim)
        if not os.path.isdir(bk):
            continue
        for dil in sorted(os.listdir(bk)):
            dk = os.path.join(bk, dil)
            if dil.startswith(".") or not os.path.isdir(dk):
                continue
            for f in sorted(os.listdir(dk)):
                kok_ad, uz = os.path.splitext(f)
                if f.startswith(".") or uz.lower() != "." + bicim.lower():
                    continue
                k = kitap(kok_ad)
                p = os.path.join(dk, f)
                st = os.stat(p)
                k["tarih"] = max(k["tarih"], int(st.st_mtime))
                giris = {"bicim": bicim, "dil": dil, "yol": f"{bicim}/{dil}/{f}", "boyut": st.st_size}
                k["dosyalar"].append(giris)
                if bicim == "EPUB":
                    k["epub"].append({"dil": dil, "yol": giris["yol"]})
    md = os.path.join(KOK, "M4B")
    if os.path.isdir(md):
        for f in sorted(os.listdir(md), key=lambda x: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", x)]):
            if f.lower().endswith(".m4b") and not f.startswith("."):
                kitap(re.sub(r" - \d+$", "", f[:-4]))["ses"].append(f"M4B/{f}")
    mp = os.path.join(KOK, "MP3")
    if os.path.isdir(mp):
        for f in os.listdir(mp):
            if os.path.isdir(os.path.join(mp, f)) and sade(f) in kitaplar:
                kitaplar[sade(f)]["mp3"] = True
    # Stüdyo kaydı: kitabın EPUB çıktı adı (durum "cikti": "Türkçe/Ad.epub") ya da "Başlık - Yazar"
    for s in depo.liste():
        adaylar = {sade(os.path.splitext(os.path.basename(c))[0]) for c in (s.get("cikti") or [])}
        if s.get("baslik"):
            adaylar.add(sade(f"{s['baslik']} - {s['yazar']}" if s.get("yazar") and s["yazar"] != s["baslik"] else s["baslik"]))
        for a in adaylar:
            if a in kitaplar and not kitaplar[a]["kimlik"]:
                kitaplar[a].update(kimlik=s["kimlik"], kutuphanede=s.get("kutuphanede"), studyo=s.get("studyo"))
                break
    out = [k for k in kitaplar.values() if k["epub"] or k["ses"] or k["dosyalar"]]
    for k in out:
        k["epub"].sort(key=lambda e: SIRA_DIL.index(e["dil"]) if e["dil"] in SIRA_DIL else 99)
    return sorted(out, key=lambda k: k["anahtar"])


# ---------------- EPUB okuma (salt okunur) ----------------
def _xml(z, ad):
    from lxml import etree
    return etree.fromstring(z.read(ad), etree.XMLParser(recover=True, resolve_entities=False, no_network=True))


_onbellek = {}


def epub_yapi(tam):
    """Önbellekli (yol + değişme zamanı)."""
    a = (tam, os.path.getmtime(tam))
    if a not in _onbellek:
        if len(_onbellek) > 50:
            _onbellek.clear()
        _onbellek[a] = _epub_yapi(tam)
    return _onbellek[a]


def _epub_yapi(tam):
    """{baslik, bolumler: [{no, baslik, dosya}]}: omurga (spine) sırası; başlık içindekilerden (nav/ncx), yoksa dosyadan."""
    with zipfile.ZipFile(tam) as z:
        kap = _xml(z, "META-INF/container.xml")
        opf_ad = kap.xpath("//*[local-name()='rootfile']/@full-path")[0]
        opf = _xml(z, opf_ad)
        taban = posixpath.dirname(opf_ad)
        tam_ad = lambda h: posixpath.normpath(posixpath.join(taban, unquote(h.split("#")[0])))
        ogeler = {i.get("id"): i for i in opf.xpath("//*[local-name()='manifest']/*[local-name()='item']")}
        baslik = (opf.xpath("string(//*[local-name()='title'])") or "").strip()
        adlar = {}
        nav = [i for i in ogeler.values() if "nav" in (i.get("properties") or "").split()]
        try:
            if nav:
                n = _xml(z, tam_ad(nav[0].get("href")))
                ntaban = posixpath.dirname(tam_ad(nav[0].get("href")))
                for a in n.xpath("//*[local-name()='nav'][1]//*[local-name()='a'][@href]"):
                    d = posixpath.normpath(posixpath.join(ntaban, unquote(a.get("href").split("#")[0])))
                    adlar.setdefault(d, " ".join("".join(a.itertext()).split()))
            else:
                ncx = [i for i in ogeler.values() if i.get("media-type") == "application/x-dtbncx+xml"]
                if ncx:
                    n = _xml(z, tam_ad(ncx[0].get("href")))
                    ntaban = posixpath.dirname(tam_ad(ncx[0].get("href")))
                    for p in n.xpath("//*[local-name()='navPoint']"):
                        src = p.xpath("string(*[local-name()='content']/@src)")
                        d = posixpath.normpath(posixpath.join(ntaban, unquote(src.split("#")[0])))
                        adlar.setdefault(d, " ".join(p.xpath("string(*[local-name()='navLabel'])").split()))
        except Exception:
            pass
        bolumler = []
        for ref in opf.xpath("//*[local-name()='spine']/*[local-name()='itemref']"):
            i = ogeler.get(ref.get("idref"))
            if i is None or "html" not in (i.get("media-type") or ""):
                continue
            d = tam_ad(i.get("href"))
            try:
                ham = z.read(d).decode("utf-8", "replace")
            except KeyError:
                continue
            govde = re.sub(r"(?s)<head.*?</head>|<script.*?</script>|<style.*?</style>", " ", ham)
            if not re.sub(r"<[^>]+>|&[a-z#0-9]+;|\s", "", govde):
                continue                                   # kapak resmi gibi yazısız sayfa
            ad = adlar.get(d) if len(adlar) > 1 else ""   # Stüdyo EPUB'unda içindekiler tek bağlantıdır
            if not ad and "kunye" in (i.get("id") or "").lower():
                ad = "Künye"
            if not ad and "nav" in (i.get("properties") or "").split():
                ad = "İçindekiler"
            if not ad:
                m = re.search(r"(?s)<h[1-3][^>]*>(.*?)</h[1-3]>", govde)
                ad = " ".join(re.sub(r"<[^>]+>", " ", html.unescape(m.group(1))).split())[:90] if m else ""
            bolumler.append({"no": len(bolumler), "baslik": ad or "", "dosya": d})
    for b in bolumler:
        b["baslik"] = b["baslik"] or f"Bölüm {b['no'] + 1}"
    return {"baslik": baslik, "bolumler": bolumler}


_YASAK_ETIKET = {"script", "style", "link", "meta", "iframe", "object", "embed", "form", "input", "button", "svg", "img",
                 "image", "video", "audio", "source", "head", "title", "base"}


def epub_bolum(tam, no):
    """Bölümün gövdesi, temizlenmiş HTML olarak (betik, stil, resim, olay öznitelikleri yok; bağlantılar metin olur)."""
    from lxml import html as lh
    yapi = epub_yapi(tam)
    if not 0 <= no < len(yapi["bolumler"]):
        raise IndexError(no)
    with zipfile.ZipFile(tam) as z:
        ham = z.read(yapi["bolumler"][no]["dosya"])
    metin = re.sub(r"^\s*<\?xml[^>]*\?>", "", ham.decode("utf-8-sig", "replace"))   # EPUB UTF-8'dir; bildirim lxml'e verilmez
    kok = lh.document_fromstring(metin)
    govde = kok.find("body") if kok.find("body") is not None else kok
    for el in list(govde.iter()):
        if not isinstance(el.tag, str):          # yorum, işlem talimatı
            el.drop_tree() if el.getparent() is not None else None
            continue
        etiket = el.tag.split("}")[-1].lower()
        if etiket in _YASAK_ETIKET and el is not govde:
            el.drop_tree()
            continue
        if etiket == "a":
            el.drop_tag()
            continue
        for oz in list(el.attrib):
            if oz.lower() not in ("dir", "lang", "colspan", "rowspan") and not oz.endswith("}lang"):
                del el.attrib[oz]
    ic = html.escape(govde.text or "") + "".join(lh.tostring(c, encoding="unicode") for c in govde)
    return {"no": no, "baslik": yapi["bolumler"][no]["baslik"], "toplam": len(yapi["bolumler"]), "html": ic}
