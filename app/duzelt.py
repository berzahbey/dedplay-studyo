"""Biçimden bağımsız metin düzeltme (EPUB, PDF, DOCX, TXT, OCR): satır içine girmiş sayfa üst bilgileri,
sayfa sonunda bölünen kelimeler, çöp işaretler, sayfa atıfları ve dipnot işaretleri."""
import collections
import os
import re

KELIME_DOSYASI = os.environ.get("TR_KELIME", os.path.join(os.path.dirname(__file__), "data", "tr_kelime.txt"))
_TR_ISKELET = str.maketrans("ıiİIşŞğĞçÇöÖüÜâÂîÎûÛ", "iiiissggccoouuaaiiuu")
_kelimeler, _iskelet = None, None


def _sozluk():
    """Türkçe kelime listesi (sıklığa göre) ve Türkçe harfsiz 'iskelet' -> en sık kelime eşlemesi."""
    global _kelimeler, _iskelet
    if _kelimeler is None:
        _kelimeler, _iskelet = {}, {}
        try:
            for sira, ln in enumerate(open(KELIME_DOSYASI, encoding="utf-8")):
                w = ln.split()[0].lower() if ln.strip() else ""
                if w and w.isalpha():
                    _kelimeler.setdefault(w, sira)
                    _iskelet.setdefault(w.translate(_TR_ISKELET), w)
        except OSError:
            pass
    return _kelimeler, _iskelet


_SAPKA = str.maketrans("âîûÂÎÛ", "aiuAIU")
_BAGLAC = {"ve", "de", "da", "ki", "mi", "mı", "mu", "mü", "bir", "bu", "şu", "o", "ya", "ile"}


def _kelime_mi(w):
    k = _sozluk()[0]
    w = w.lower()
    return w in k or w.translate(_SAPKA) in k


def _birlesik(sol, sag):
    """Sayfa geçişinde bölünen kelime: sol+sağ gerçek bir kelimeyse (Türkçe harf farkları dahil) onu döndürür."""
    kelimeler, iskelet = _sozluk()
    aday = (sol + sag).lower()
    # aynı kelimenin en sık (Türkçe harfli) yazılışı tercih edilir: artik -> artık
    duz = iskelet.get(aday.translate(_TR_ISKELET))
    if duz:
        return (duz[0].upper() + duz[1:]) if sol[:1].isupper() else duz
    if aday in kelimeler:
        return sol + sag
    # listede olmayan uzun ekli kelimeler: parçalardan biri tek başına kelime değilse birleştir (çekiş+melerini)
    if not _kelime_mi(sol) or (not _kelime_mi(sag) and len(sag) <= 8):
        return sol + sag
    return None


_COP = re.compile(r"\s*[|¦■□▪▫◆◇●○¤§]{2,}\s*")
_BUYUK = "A-ZÇĞİÖŞÜÂÎÛ"
# Satır içi üst bilgi: "16 GİRİŞ", "17 İBN HALDUN" ya da "GİRİŞ 16"
_UST_BILGI = re.compile(rf"(?<![\w])(\d{{1,4}})\s+([{_BUYUK}][{_BUYUK}'’\- ]{{2,40}}?[{_BUYUK}])(?=\s|$)|"
                        rf"(?<![\w])([{_BUYUK}][{_BUYUK}'’\- ]{{2,40}}?[{_BUYUK}])\s+(\d{{1,4}})(?![\w/.])")


def satir_ici_ust_bilgileri_bul(paras):
    """Kitap boyunca farklı sayfa numaralarıyla tekrar eden büyük harfli ifadeler (sayfa üst bilgileri)."""
    sayac = collections.defaultdict(set)
    for p in paras:
        for m in _UST_BILGI.finditer(p):
            no, baslik = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
            sayac[baslik.strip()].add(no)
    return {b for b, nolar in sayac.items() if len(nolar) >= 3}


def satir_ici_ust_bilgileri_sil(p, basliklar):
    if not basliklar:
        return p
    def degis(m):
        baslik = (m.group(2) or m.group(3) or "").strip()
        return "\u0000" if baslik in basliklar else m.group(0)
    p = _UST_BILGI.sub(degis, p)
    # silinen yerde bölünmüş kelime kaldıysa birleştir: "ar \0 tik" -> "artık"
    def onar(m):
        sol, sag = m.group(1), m.group(2)
        b = _birlesik(sol, sag)
        return b if b else f"{sol} {sag}"
    p = re.sub(r"([^\W\d_]+)\s*\u0000\s*([a-zçğıöşüâîû]+)", onar, p)
    return re.sub(r"\s*\u0000\s*", " ", p)


def cop_isaretleri_sil(p):
    """'ar |||| ' gibi çöp işaretler; arkasında bölünmüş kelime varsa onarılır."""
    def onar(m):
        sol, sag = m.group(1), m.group(2)
        b = _birlesik(sol, sag)
        return b if b else f"{sol} {sag}"
    p = re.sub(r"([^\W\d_]+)" + _COP.pattern + r"([a-zçğıöşüâîû]+)", onar, p)
    return _COP.sub(" ", p)


_SAYFA_ATIF = re.compile(
    r"\s*[\(\[]\s*(?:bkz\.?|bak\.?|bakınız|krş\.?|karş\.?)?\s*(?:c\.\s*[IVXLC\d]+,?\s*)?(?:s|sh|sf|syf|sayfa|p|pp)\.?\s*"
    r"\d{1,4}(?:\s*[-–]\s*\d{1,4})?\s*[\)\]]", re.I)
_BKZ_SAYFA = re.compile(r"\s*\(?\b(?:bkz\.?|bakınız)\s+(?:s|sh|sf|sayfa)\.?\s*\d{1,4}(?:\s*[-–]\s*\d{1,4})?\)?", re.I)
_DIPNOT_ISARET = re.compile(r"(?<=[^\W\d_\.,;:!?”\"'’)])\s?(?:\[\d{1,3}\]|\(\d{1,3}\)|[¹²³⁴⁵⁶⁷⁸⁹⁰]+|\*{1,3})(?=[\s.,;:!?”\"')]|$)")


_TIRE_BOSLUK = re.compile(r"(?<![\w-])([^\W\d_]{2,})[-‐]\s+([a-zçğıöşüâîû]{2,})")
_SATIR_ICI_TIRE = re.compile(r"(?<![\w-])([^\W\d_]{2,})-([a-zçğıöşüâîû]{2,})(?![\w-])")


def satir_ici_tireleri_birlestir(p):
    """EPUB'da satır içinde kalmış heceleme tiresi: Merini-ler -> Meriniler (sağ parça tek başına kelime değilse).
    İzafet (Kur'an-ı) ve gerçek birleşik yazımlara (Âl-i) dokunulmaz."""
    kelimeler, iskelet = _sozluk()

    def listede(sol, sag):
        aday = (sol + sag).lower()
        return aday in kelimeler or aday.translate(_TR_ISKELET) in iskelet

    def degis(m):  # tiresiz: sağ parça kısa ek gibiyse ya da birleşik hâl listedeyse (ilim-irfan kalır)
        sol, sag = m.group(1), m.group(2)
        if len(sag) <= 4 and sag.lower() not in _BAGLAC:
            return _birlesik(sol, sag) or (sol + sag)
        if _kelime_mi(sag) or not listede(sol, sag):
            return m.group(0)
        return _birlesik(sol, sag) or m.group(0)

    def degis_bosluklu(m):  # "kitap- ların": tireden sonra boşluk, bölünme neredeyse kesin
        sol, sag = m.group(1), m.group(2)
        if _kelime_mi(sag) and not listede(sol, sag):
            return m.group(0)
        return _birlesik(sol, sag) or m.group(0)
    p = _TIRE_BOSLUK.sub(degis_bosluklu, p)
    return _SATIR_ICI_TIRE.sub(degis, p)


def sayfa_atiflarini_sil(p):
    """(s. 45), [s. 34], (bkz. s. 12), (sh. 23), (c. II, s. 45), bkz. sayfa 12"""
    p = _SAYFA_ATIF.sub("", p)
    return _BKZ_SAYFA.sub("", p)


def dipnot_isaretlerini_sil(p):
    """kelime[1], kelime(1), kelime¹, kelime* gibi dipnot işaretleri."""
    return _DIPNOT_ISARET.sub("", p)


def duzelt(paras):
    """Paragraf listesini düzeltir (kitap düzeyinde üst bilgi analizi dahil)."""
    basliklar = satir_ici_ust_bilgileri_bul(paras)
    out = []
    for p in paras:
        p = satir_ici_ust_bilgileri_sil(p, basliklar)
        p = cop_isaretleri_sil(p)
        p = satir_ici_tireleri_birlestir(p)
        p = sayfa_atiflarini_sil(p)
        p = dipnot_isaretlerini_sil(p)
        p = re.sub(r"\s{2,}", " ", p).replace(" ,", ",").replace(" .", ".").strip()
        p = re.sub(r"\s*[;,:]+\s*(?=[.!?])", "", p)          # atıf silinince kalan ";." -> "."
        p = re.sub(r"([,;:])(\s*\1)+", r"\1", p)               # ", ," -> ","
        p = re.sub(r"\(\s*\)|\[\s*\]", "", p).strip()        # boş parantez
        if p and not re.fullmatch(r"[\d\s\W]{1,6}", p):  # tek başına sayfa numarası / işaret
            out.append(p)
    return out
