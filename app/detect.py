"""Kitaptan kısa bir örnek metin alıp dilini tahmin eder (OCR yapmaz)."""
import os
import re

ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
LETTER = re.compile(r"[^\W\d_]")
WORDS = {
    "tr": {"ve", "bir", "bu", "ile", "için", "olan", "olarak", "da", "de", "ki", "gibi", "daha", "çok", "ise",
           "değil", "kadar", "sonra", "onun", "bütün", "her"},
    "en": {"the", "and", "of", "to", "in", "is", "that", "it", "was", "for", "with", "as", "his", "which", "by"},
    "fr": {"le", "la", "les", "et", "des", "du", "un", "une", "est", "que", "dans", "pour", "qui", "pas", "au"},
}


def sample_text(path, limit=40000):
    ext = os.path.splitext(path)[1].lower()
    text = ""
    try:
        if ext == ".pdf":
            import fitz
            doc = fitz.open(path)
            for i, page in enumerate(doc):
                text += page.get_text() + "\n"
                if len(text) > limit or i > 40:
                    break
        elif ext == ".epub":
            from bs4 import BeautifulSoup
            from ebooklib import ITEM_DOCUMENT, epub
            book = epub.read_epub(path, options={"ignore_ncx": True})
            for item in book.get_items_of_type(ITEM_DOCUMENT):
                text += BeautifulSoup(item.get_content(), "html.parser").get_text(" ") + "\n"
                if len(text) > limit:
                    break
        elif ext == ".docx":
            import docx
            for p in docx.Document(path).paragraphs:
                text += p.text + "\n"
                if len(text) > limit:
                    break
        elif ext == ".txt":
            raw = open(path, "rb").read(limit * 2)
            for enc in ("utf-8", "cp1254", "cp1256", "latin-1"):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
    except Exception:
        return ""
    return text[:limit]


def detect_lang(text):
    """'tr', 'ar', 'en', 'fr' ya da None (metin yok/az)."""
    letters = LETTER.findall(text)
    if len(letters) < 200:
        return None
    if len(ARABIC.findall(text)) / len(letters) > 0.3:
        return "ar"
    words = re.findall(r"[^\W\d_]+", text.lower())
    if not words:
        return None
    scores = {k: sum(1 for w in words if w in v) / len(words) for k, v in WORDS.items()}
    tr_chars = len(re.findall(r"[çğışöü]", text.lower())) / max(1, len(words))
    scores["tr"] += tr_chars * 0.5
    return max(scores, key=scores.get)
