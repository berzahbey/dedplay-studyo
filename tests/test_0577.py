"""0.5.77: EPUB fihristinde alt kısım tek Link olsa da (ebooklib) kitap durmaz."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ebooklib import epub  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402
from kutuphane import kaynak  # noqa: E402


def _kitap(toc):
    b = epub.EpubBook()
    b.toc = toc
    return b


def test_link_alt():
    a, c = epub.Link("a.xhtml", "Birinci", "a"), epub.Link("b.xhtml", "İkinci", "b")
    belgeler = [("a.xhtml", BeautifulSoup("<body><h1>Birinci</h1><p>x</p></body>", "html.parser")),
                ("b.xhtml", BeautifulSoup("<body><h1>İkinci</h1><p>y</p></body>", "html.parser"))]
    for toc in ([(a, c)], [(epub.Section("Bölüm"), c), a], (a, [c]), [a, c]):
        kaynak._epub_fihristi(_kitap(toc), belgeler)      # hata vermemeli
