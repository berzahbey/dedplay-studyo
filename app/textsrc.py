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


def to_parts(paras, size=PART_CHARS):
    """Paragrafları ~3000 karakterlik parçalara toplar; paragraf sınırları satır sonuyla korunur."""
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
