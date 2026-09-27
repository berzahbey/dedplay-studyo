"""Kitabın ilk (orijinal) metnini çıkarır.

Kitap Okuma'nın metni seslendirme için değiştirilmiş olur (sayılar yazıya çevrilir,
şapkalar/kesmeler kaldırılır, okunuşa göre yazılır). Osmanlıca çeviri ve Türkçe kitap
dosyaları için kitabın kendi metni gerekir; bu modül onu çıkarır.

Sadece sayfa numarası, tekrar eden üst/alt bilgi ve satır sonu tirelerini temizler;
kelimelere dokunmaz. Taranmış PDF sayfalarını bütün çekirdeklerle OCR yapar.
"""
import collections
import io
import os
import re
import unicodedata
from concurrent.futures import ProcessPoolExecutor

OCR_LANG = os.environ.get("OCR_LANG", "tur")
PART_CHARS = 3000

PAGE_NUM = re.compile(r"^[\s\-–—\[\(]*(\d{1,4}|[ivxlcdm]{1,7}|[٠-٩]{1,4})[\s\-–—\]\)]*$", re.I)
END_PUNCT = tuple('.!?:;"”»)]…')


def norm(t):
    t = unicodedata.normalize("NFC", t)  # NFKC değil: Türkçe/Arapça harflere dokunma
    t = t.replace("\u00ad", "").replace("\ufeff", "")
    t = re.sub(r"[ \t\u00a0]+", " ", t)
    return t.strip()


def join_lines(raw):
    raw = re.sub(r"(\w)[-‐]\n(\w)", r"\1\2", raw)
    return norm(raw.replace("\n", " "))


def merge_paragraphs(paras):
    """Sayfa ya da satır geçişinde bölünmüş paragrafları birleştirir."""
    out = []
    for t in paras:
        if out and not out[-1].endswith(END_PUNCT) and len(out[-1]) > 40 and t[:1].islower():
            out[-1] = out[-1] + " " + t
        else:
            out.append(t)
    return out


# ---------------- OCR ----------------
def _ocr_page(args):
    os.environ["OMP_THREAD_LIMIT"] = "1"
    import fitz
    import pytesseract
    from PIL import Image
    path, i = args
    pix = fitz.open(path)[i].get_pixmap(dpi=250)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    try:
        text = pytesseract.image_to_string(img, lang=OCR_LANG)
    except Exception:
        text = pytesseract.image_to_string(img)
    paras = [join_lines(p) for p in re.split(r"\n\s*\n", text)]
    return i, [(p, False) for p in paras if p and not PAGE_NUM.match(p)]


# ---------------- biçimler ----------------
def from_pdf(path):
    import fitz
    doc = fitz.open(path)
    pages, need = [], []
    for n, page in enumerate(doc):
        h = page.rect.height
        items = []
        for b in page.get_text("blocks", sort=True):
            if b[6] != 0:
                continue
            t = join_lines(b[4])
            if t:
                items.append((t, b[3] < h * 0.09 or b[1] > h * 0.91))
        if sum(len(t) for t, _ in items) < 40:
            need.append(n)
        pages.append(items)
    if need:
        workers = max(1, os.cpu_count() or 1)
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for i, items in ex.map(_ocr_page, [(path, i) for i in need], chunksize=2):
                pages[i] = items

    def key(t):
        return re.sub(r"\d+", "", t).strip().lower()

    counts = collections.Counter(key(t) for items in pages for t, edge in items if edge)
    limit = max(3, int(len(pages) * 0.3))
    repeated = {k for k, c in counts.items() if c >= limit and k}
    paras = []
    for items in pages:
        for t, edge in items:
            if PAGE_NUM.match(t) or (edge and (key(t) in repeated or len(t) < 4)):
                continue
            paras.append(t)
    return merge_paragraphs(paras)


def from_epub(path):
    from bs4 import BeautifulSoup
    from ebooklib import ITEM_DOCUMENT, epub
    book = epub.read_epub(path, options={"ignore_ncx": True})
    tags = ["h1", "h2", "h3", "h4", "p", "li", "blockquote"]
    paras = []
    for idref, _ in book.spine:
        item = book.get_item_with_id(idref)
        if not item or item.get_type() != ITEM_DOCUMENT:
            continue
        soup = BeautifulSoup(item.get_content(), "html.parser")
        for s in soup(["script", "style"]):
            s.decompose()
        found = False
        for tag in soup.find_all(tags):
            if tag.find(tags):
                continue
            t = norm(tag.get_text(" "))
            if t and not PAGE_NUM.match(t):
                paras.append(t)
                found = True
        if not found and soup.body:
            paras += [norm(x) for x in soup.body.get_text("\n").split("\n") if norm(x)]
    return paras


def from_docx(path):
    import docx
    return [norm(p.text) for p in docx.Document(path).paragraphs if norm(p.text) and not PAGE_NUM.match(norm(p.text))]


def from_txt_bytes(raw, skip_title=False):
    text = None
    for enc in ("utf-8-sig", "cp1254", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    blocks = re.split(r"\n\s*\n", (text or "").replace("\r\n", "\n"))
    paras = [join_lines(b) for b in blocks]
    paras = [p for p in paras if p and not PAGE_NUM.match(p)]
    return paras[1:] if skip_title and paras else paras


def extract(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return from_pdf(path)
    if ext == ".epub":
        return from_epub(path)
    if ext == ".docx":
        return from_docx(path)
    if ext == ".txt":
        return from_txt_bytes(open(path, "rb").read())
    return []


def make_title(text: str) -> str:
    """Metnin ilk cümlesinin ilk kelimelerinden dosya adına uygun bir başlık."""
    first = re.split(r"[.!?:\n]", (text or "").strip())[0]
    title = " ".join(first.split()[:8]).strip(" .,;:!?-" + chr(8211) + chr(8212) + chr(34) + chr(39))
    title = re.sub("[" + re.escape(chr(92) + "/:*?" + chr(34) + "<>|") + "]+", " ", title)
    return re.sub(r"\s+", " ", title).strip(" .")[:80]


def to_parts(paras, size=PART_CHARS):
    """Paragrafları ~3000 karakterlik parçalara toplar; paragraf sınırları satır sonuyla korunur."""
    paras = [p for p in paras if any(ch.isalnum() for ch in p)]  # "-----", "*****" gibi süs satırları atlanır
    parts, cur = [], []
    length = 0
    for p in paras:
        if cur and length + len(p) > size:
            parts.append("\n".join(cur))
            cur, length = [], 0
        cur.append(p)
        length += len(p) + 1
    if cur:
        parts.append("\n".join(cur))
    return [(f"Parca_{i:03d}.txt", t) for i, t in enumerate(parts, 1)]


# ================= Temiz metin: ön sayfalar, içindekiler, dipnotlar (Stüdyo tek kaynak) =================
import statistics as _st

ICERIK_BASLIK = re.compile(
    r"^(çevirenin|mütercimin|müellifin|yazarın|naşirin|editörün|yayıncının)?\s*(önsözü|ön sözü)[.:]?$|"
    r"^(önsöz|ön söz|giriş|mukaddime|takdim|sunuş|başlarken|takriz|introduction|preface|foreword)[.:]?$|"
    r"^(birinci|1\.?)\s*(bölüm|kısım|fasıl|kitap)[.:]?$|^(bölüm|kısım)\s*(1|i|bir)[.:]?$", re.I)
KUNYE = re.compile(r"isbn|sertifika|basımevi|matbaa|baskı\b|\bbasım\b|yayın(ları|evi)|hakları saklı|©|copyright|"
                   r"tel\s*[:.]|faks|fax|www\.|e-?posta|kapak tasarım|dizgi|editör|yayın yönetmen|genel yayın|"
                   r"printed in|kütüphane.*katalog", re.I)
ICINDEKILER = re.compile(r"içindekiler|fihrist|contents", re.I)
NOKTALI = re.compile(r"(\.{4,}|…{2,}|(\. ){4,})|\s\d{1,3}\s*$")


def _harf(s):
    return sum(1 for c in s if c.isalpha())


def _sayfa_turu(satirlar):
    """'toc' (içindekiler), 'kunye' (yayıncı/künye), 'bos' (kapak/boş/çöp) ya da 'metin'."""
    metin = "\n".join(satirlar)
    dolu = [s for s in satirlar if s.strip()]
    noktali = sum(1 for s in dolu if NOKTALI.search(s))
    if ICINDEKILER.search(metin[:300]) or (dolu and noktali >= max(3, 0.3 * len(dolu))):
        return "toc"
    if _harf(metin) < 250:
        return "bos"
    if len(KUNYE.findall(metin)) >= 2 and _harf(metin) < 1500:
        return "kunye"
    return "metin"


def on_ve_son_sayfalari_at(sayfalar):
    """sayfalar: [[paragraf, ...], ...]. Baştaki kapak/künye/içindekiler sayfalarını ve sondaki
    içindekiler/künye sayfalarını atar. Asıl metin, ilk sayfalardaki tek başına duran bir içerik
    başlığından (Önsöz, Giriş, Birinci Bölüm...) başlar; bulunamazsa baştaki künye-benzeri sayfalar atlanır."""
    n = len(sayfalar)
    if n < 4:
        return sayfalar
    pencere = min(n - 1, max(8, min(40, n // 5)))
    turler = [_sayfa_turu(s) for s in sayfalar]
    bas = None
    for i in range(pencere):
        if turler[i] == "toc":
            continue
        ilkler = [p.strip() for p in sayfalar[i] if p.strip()][:3]
        if any(ICERIK_BASLIK.match(re.sub(r"\s+", " ", p)) and len(p) < 60 for p in ilkler):
            bas = i
            break
    if bas is None:
        bas = 0
        while bas < pencere and turler[bas] in ("toc", "kunye", "bos"):
            bas += 1
    son = n
    # sonda sadece içindekiler/künye sayfaları (ve onların arasındaki boş sayfalar) atılır; kısa metin sayfaları kalır
    while son > bas + 1 and son > n - 15 and turler[son - 1] in ("toc", "kunye", "bos"):
        if turler[son - 1] == "bos" and not any(t in ("toc", "kunye") for t in turler[max(bas, son - 3):son - 1]):
            break
        son -= 1
    return sayfalar[bas:son]


def _dipnot_ayir(rows, page_h):
    """rows (okuma sırasıyla, {'h','top','n',...}): (ana_satirlar, dipnot_satirlari)."""
    govde = [r["h"] for r in rows if r["n"] >= 4 and r["h"] > 0]
    if len(govde) < 3:
        return rows, []
    ana = _st.median(govde)
    for idx, r in enumerate(rows):
        if r["top"] > page_h * 0.45 and 0 < r["h"] < ana * 0.82:
            kalan = [x for x in rows[idx:] if x["h"] > 0]
            if kalan and sum(1 for x in kalan if x["h"] < ana * 0.86) >= 0.7 * len(kalan):
                return rows[:idx], rows[idx:]
    return rows, []


def _paragraflar(satir_gruplari):
    """[(paragraf_anahtarı, satır), ...] -> paragraflar (satır sonu tireleri birleşir)."""
    out, cur, onceki = [], [], object()
    for key, s in satir_gruplari:
        if key != onceki and cur:
            out.append(join_lines("\n".join(cur)))
            cur = []
        cur.append(s)
        onceki = key
    if cur:
        out.append(join_lines("\n".join(cur)))
    return [p for p in out if p]


_YAPISIK_RAKAM = re.compile(r"(?<=[a-zçğıöşüâîû])\d{1,2}(?=[\s.,;:!?”\"')]|$)")


def _ocr_sayfa_temiz(args):
    """Taranmış sayfa: (sayfa_no, ana_paragraflar, dipnot_paragraflar). 300 DPI, dipnotlar ayrılır."""
    os.environ["OMP_THREAD_LIMIT"] = "1"
    import fitz
    import pytesseract
    from PIL import Image, ImageOps
    path, i = args
    pix = fitz.open(path)[i].get_pixmap(dpi=300)
    img = ImageOps.autocontrast(Image.open(io.BytesIO(pix.tobytes("png"))).convert("L"))
    try:
        d = pytesseract.image_to_data(img, lang=OCR_LANG, output_type=pytesseract.Output.DICT)
    except Exception:
        d = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    satirlar, sira = {}, []
    for k in range(len(d["text"])):
        t = (d["text"][k] or "").strip()
        if not t:
            continue
        key = (d["block_num"][k], d["par_num"][k], d["line_num"][k])
        if key not in satirlar:
            satirlar[key] = []
            sira.append(key)
        satirlar[key].append((d["left"][k], t, d["height"][k], d["top"][k]))
    rows = []
    for key in sira:
        ws = sorted(satirlar[key])
        hs = [h for _, t, h, _ in ws if any(c.isalpha() for c in t)]
        lh = _st.median(hs) if hs else 0
        metin = " ".join(t for _, t, h, _ in ws if not (lh and h < lh * 0.6 and re.fullmatch(r"[\d\W]+", t)))
        rows.append({"key": key[:2], "text": metin, "h": lh, "top": min(w[3] for w in ws), "n": len(ws)})
    ana, dip = _dipnot_ayir(rows, img.size[1])
    temiz = lambda rs: [(r["key"], r["text"]) for r in rs if not PAGE_NUM.match(r["text"].strip())]
    return i, _paragraflar(temiz(ana)), _paragraflar(temiz(dip))


def _katman_sayfa_temiz(page):
    """Metin katmanlı sayfa: (ana_paragraflar, dipnot_paragraflar); dipnot numaraları ayıklanır."""
    rows = []
    for b in page.get_text("dict").get("blocks", []):
        for ln in b.get("lines", []):
            spans = [s for s in ln.get("spans", []) if s.get("text", "").strip()]
            if not spans:
                continue
            boy = [s["size"] for s in spans if any(c.isalpha() for c in s["text"])]
            h = _st.median(boy) if boy else 0
            metin = "".join(s["text"] for s in spans
                            if not ((s.get("flags", 0) & 1 or (h and s["size"] < h * 0.75))
                                    and re.fullmatch(r"[\d\s\W]+", s["text"])))
            rows.append({"key": id(b), "text": metin, "h": h, "top": ln["bbox"][1], "n": len(metin.split())})
    ana, dip = _dipnot_ayir(rows, page.rect.height)
    temiz = lambda rs: [(r["key"], r["text"]) for r in rs if not re.fullmatch(r"[\d\s\W]{0,4}", r["text"])]
    return _paragraflar(temiz(ana)), _paragraflar(temiz(dip))


def _tekrarlayan_basliklari_at(sayfalar):
    """Sayfaların ilk/son paragrafı olarak tekrar eden üst/alt bilgileri (kitap adı, bölüm adı) atar."""
    anahtar = lambda t: re.sub(r"\d+", "", t).strip().lower()
    sayac = collections.Counter()
    for s in sayfalar:
        for p in (s[:1] + s[-1:]):
            if len(p) < 80:
                sayac[anahtar(p)] += 1
    esik = max(3, int(len(sayfalar) * 0.3))
    tekrar = {k for k, c in sayac.items() if c >= esik and k}
    out = []
    for s in sayfalar:
        s = [p for j, p in enumerate(s) if not ((j == 0 or j == len(s) - 1) and anahtar(p) in tekrar)]
        if s:  # üst bilgi ilk paragrafın başına yapışık gelmişse onu da kes
            for t in tekrar:
                if len(t) > 5 and anahtar(s[0]).startswith(t) and len(s[0]) > len(t) + 5:
                    # kesme noktası eşleşmeyle bulunur (İ küçülünce iki karaktere dönüşür)
                    k = next((k for k in range(1, len(s[0]) + 1) if anahtar(s[0][:k]) == t), None)
                    if k:
                        s[0] = s[0][k:].lstrip(" .:-")
                    break
        out.append(s)
    return out


def _birlestir(paras):
    """Sayfa geçişinde bölünen paragrafları birleştirir; sayfa sonu tiresini (olduk- / larını) kapatır."""
    out = []
    for t in paras:
        if out and out[-1].endswith(("-", "‐")) and t[:1].islower():
            out[-1] = out[-1][:-1] + t
        elif out and not out[-1].endswith(END_PUNCT) and len(out[-1]) > 40 and t[:1].islower():
            out[-1] = out[-1] + " " + t
        else:
            out.append(t)
    return out


def _dipnotlari_duzenle(paras):
    """Dipnot parçalarını numaralı notlara böler: '7 Bak: ...' yeni not; devam satırları öncekine eklenir."""
    out = []
    for p in paras:
        for parca in re.split(r"\s(?=\d{1,3}\s+[A-ZÇĞİÖŞÜ])", p):
            parca = parca.strip()
            if not parca:
                continue
            if out and not re.match(r"^\d{1,3}\s", parca):
                out[-1] += " " + parca
            else:
                out.append(parca)
    return out


def pdf_temiz(path):
    """PDF -> (ana_paragraflar, dipnotlar): ön/son sayfalar, içindekiler, üst bilgiler ve dipnotlar ayrılır."""
    import fitz
    doc = fitz.open(path)
    sayfalar, notlar, ocr = [None] * len(doc), [None] * len(doc), []
    for i, page in enumerate(doc):
        try:
            ana, dip = _katman_sayfa_temiz(page)
        except Exception:
            ana, dip = [page.get_text()], []
        if sum(_harf(p) for p in ana) < 40:
            ocr.append(i)
        else:
            sayfalar[i], notlar[i] = ana, dip
    if ocr:
        workers = max(1, os.cpu_count() or 1)
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for i, ana, dip in ex.map(_ocr_sayfa_temiz, [(path, i) for i in ocr], chunksize=2):
                sayfalar[i], notlar[i] = ana, dip
    # ön/son sayfalar sayfa düzeyinde atılır; dipnotları da aynı sayfalarla birlikte gider
    idx = list(range(len(doc)))
    tut = on_ve_son_sayfalari_at([[str(i)] + (sayfalar[i] or []) for i in idx])
    kalan = [int(s[0]) for s in tut]
    sayfalar = _tekrarlayan_basliklari_at([sayfalar[i] or [] for i in kalan])
    ana = _birlestir([_YAPISIK_RAKAM.sub("", p) for s in sayfalar for p in s if not PAGE_NUM.match(p)])
    dip = _dipnotlari_duzenle([p for i in kalan for p in (notlar[i] or [])])
    return ana, dip


def paragraflari_bastan_temizle(paras):
    """EPUB/DOCX/TXT: ilk bölümde içindekiler/künye varsa, tek başına duran ilk içerik başlığından başlatır."""
    if len(paras) < 20:
        return paras
    pencere = min(len(paras) // 4, 400)
    on = paras[:pencere]
    sinyal = sum(1 for p in on if NOKTALI.search(p) or KUNYE.search(p) or ICINDEKILER.search(p))
    if sinyal < 3:
        return paras
    for i, p in enumerate(on):
        if len(p) < 60 and ICERIK_BASLIK.match(re.sub(r"\s+", " ", p.strip())):
            # içindekilerin içindeki başlık değil: ardından gerçek bir metin paragrafı gelmeli
            if i + 1 < len(paras) and len(paras[i + 1]) > 150:
                return paras[i:]
    return paras


def extract_full(path):
    """(ana_paragraflar, dipnotlar)."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return pdf_temiz(path)
    return paragraflari_bastan_temizle(extract(path)), []


def parts_with_notes(paras, notes, size=PART_CHARS):
    """Ana metin Parca_###, dipnotlar kitabın sonunda 'DİPNOTLAR' başlığıyla Dipnot_### parçaları."""
    parts = to_parts(paras, size)
    if notes:
        parts += [(n.replace("Parca_", "Dipnot_"), t) for n, t in to_parts(["DİPNOTLAR"] + notes, size)]
    return parts
