"""0.5.43: seslendirmeye giden metinden yazarın kaynak gösterimleri çıkar (Zahir, 19 Ekim: "yazarın kaynak gösterdiği yerler
seslendirmede okunmamalı"). Yazılı çıktılara (EPUB, PDF, DOCX, TXT, HTML) dokunulmaz; yalnız Kitap Okuma'ya giden seslendirme EPUB'u.
Çıkanlar: âyet yerleri "(Kehf, 110; Fussilet, 6)", "[Enâm, 149]", "-Kehf, 54", "Bakara 2/40"; hadis kaynakları "(Müslim)",
"Tirmizî, Zühd, 25; İbn Mâce, …"; kitap/sayfa atıfları "(M. 54)", "(bkz. s. 12)", "(Ta'rîfât, 130)", "(Mevzûât el-Ulûm, I, 358)";
not işaretleri "(3)", "(٢)", "(Haşiye-1)", "…söylemiştir.55". Kalanlar: yıllar ve tarihler "(1953)", "(19 Kasım 1908)", "(ölm. 456/1065)",
"(H. 505)", açıklama parantezleri "(yani …)", sayı değerleri "(400.000)"."""
import re

SURE = ("Fatiha|Fâtiha|Bakara|Âl-i İmrân|Âl-i İmran|Al-i İmran|Âl-i İmrân|Nisâ|Nisa|Mâide|Maide|En'âm|En‘âm|Enâm|Enam|A'râf|A‘râf|Araf|Enfâl|Enfal|"
        "Tevbe|Yûnus|Yunus|Hûd|Hud|Yusuf|Yûsuf|Ra'd|İbrâhîm|İbrahim|Hicr|Nahl|Nahil|İsrâ|İsra|Kehf|Meryem|Tâhâ|Taha|Enbiyâ|Enbiya|Hac|Mü'minûn|"
        "Mü’minûn|Müminun|Nûr|Nur|Furkan|Furkân|Şuarâ|Şuara|Neml|Kasas|Ankebût|Ankebut|Rum|Rûm|Lokman|Lukmân|Secde|Ahzâb|Ahzab|Sebe'|Sebe|Fâtır|"
        "Fatır|Yâsin|Yasin|Sâffât|Saffat|Sâd|Zümer|Mü'min|Mü’min|Gâfir|Gafir|Fussilet|Şûrâ|Şura|Zuhruf|Duhân|Duhan|Câsiye|Casiye|Ahkâf|Ahkaf|"
        "Muhammed|Fetih|Hucurât|Hucurat|Kâf|Zâriyât|Zariyat|Tûr|Necm|Kamer|Rahmân|Rahman|Vâkıa|Vâkia|Vakıa|Hadîd|Hadid|Mücâdele|Mücadele|Haşr|"
        "Mümtehine|Saff|Cum'a|Cuma|Münâfikûn|Münafikun|Teğâbün|Tegabün|Talâk|Talak|Tahrîm|Tahrim|Mülk|Kalem|Hâkka|Hakka|Meâric|Nûh|Nuh|Cin|"
        "Müzzemmil|Müddessir|Kıyâme|Kıyame|İnsan|Dehr|Mürselât|Nebe'|Nebe|Nâziât|Nâzi‘ât|Naziat|Abese|Tekvîr|Tekvir|İnfitâr|Mutaffifîn|İnşikâk|"
        "Bürûc|Büruc|Târık|A'lâ|A‘lâ|A'la|Ğâşiye|Gaşiye|Fecr|Beled|Şems|Leyl|Duhâ|İnşirâh|Tîn|Alak|Kadr|Beyyine|Zilzâl|Âdiyât|Kâria|Tekâsür|"
        "Tekasür|Asr|Hümeze|Fîl|Kureyş|Mâûn|Maun|Kevser|Kâfirûn|Nasr|Tebbet|İhlâs|Felak|Nâs|Nas")
HADIS = (r"Buhârî|Buharî|Buhari|Müslim|Tirmizî|Tirmizi|Ebû Dâvûd|Ebu Davud|Ebû Davud|Nesâî|Nesai|Neseî|İbn Mâce|İbn Mace|ibn Mâce|Müsned|"
         r"Dârimî|Darimi|Muvatta|Beyhakî|Taberânî|Ahmed b\. Han-?bel|Ahmed|Hâkim|Dârekutnî|Mâlik")
HADIS_KESIN = (r"Buhârî|Buharî|Buhari|Tirmizî|Tirmizi|Ebû Dâvûd|Ebu Davud|Ebû Davud|Nesâî|Nesai|Neseî|İbn Mâce|İbn Mace|ibn Mâce|Müsned|"
               r"Dârimî|Darimi|Muvatta|Beyhakî|Taberânî|Ahmed b\. Han-?bel|Dârekutnî")   # tek başına adla karışmayanlar
_SURE_RX = re.compile(rf"(?<![\w'’])(?:{SURE})(?:\s+s[ûu]resi)?\s*[,:/]?\s*\d", re.I)
_SURE_NO = re.compile(rf"\d+\s*/\s*(?:el-)?(?:{SURE})", re.I)
_HADIS_YALNIZ = re.compile(rf"(?:{HADIS})(?:\s*(?:,|;|ve)\s*(?:{HADIS}))*\.?")
_KISALTMA = re.compile(r"(?<![\w])(?:s|ss|sh|sf|c|no|nr|vol|bl|bab)\.\s*\d|\b(?:bkz|bk|bak|krş|karş|a\.g\.e|age|a\.g\.m|nşr|neşr|çev|trc|thk|tah|"
                       r"yay|bsk|baskı|hadis no)\b\.?", re.I)
_TARIH_BASI = re.compile(r"(?:ö|öl|ölm|ölümü|vefatı|vefat|v|d|doğ|doğumu|h|m|hicri|miladi|hicrî|milâdî)\b\.?", re.I)
_ESER_NO = re.compile(r"[A-ZÇĞİÖŞÜÂÎÛ'’][^()\[\]\d]{1,60}?[,:]?\s*(?:[IVXLC]+\s*,\s*)?\d{1,4}(?:\s*[-–/]\s*\d{1,4})?(?:\s*vd\.?)?\.?")


def atif_mi(ic):
    """Parantez/köşeli parantez içi bir kaynak gösterimi mi."""
    c = ic.strip()
    if not c:
        return False
    if re.fullmatch(r"[\d٠-٩۰-۹]{1,3}|\*{1,3}|[Hh][âa]şiye(?:\s*-?\s*\d+)?|[Hh][âa]şiyecik", c):
        return True                                             # not işareti
    if _HADIS_YALNIZ.fullmatch(c):
        return True                                             # (Müslim), (Buharî, Müslim)
    if not re.search(r"[\d٠-٩]", c):
        return False
    if _SURE_RX.search(c) or _SURE_NO.search(c):
        return True                                             # (Kehf, 110), (Nahil Sûresi, 97), (20/Taha: 50)
    m = re.match(r"([A-ZÇĞİÖŞÜ]{1,3})\.\s*(\d+)", c)
    if m:                                                       # (M. 54) sayfa; (H. 505) hicrî, (M. 1058) milâdî yıl kalır
        return not (m.group(1) == "H" or (m.group(1) == "M" and len(m.group(2)) == 4))
    if len(c.split()) > 8:
        return False                                            # uzun açıklama ("yukarıda s. 182'de sözü edilen durum …") kalır
    if _KISALTMA.search(c) or re.search(HADIS_KESIN, c):
        return True
    if _ESER_NO.fullmatch(c) and not _TARIH_BASI.match(c):
        return True                                             # (Ta'rîfât, 130), (Mevzûât el-Ulûm, I, 358)
    return False


_PARANTEZ = re.compile(r"\s?\(([^()\n]{1,200})\)|\s?\[([^\[\]\n]{1,200})\]")
_Z = r"(?:[^.()\n]|(?<=\b[bB])\.)"   # "Ahmed b. Hanbel" içindeki nokta cümle sonu değil
_ZINCIR = re.compile(rf"(?:(?<=\s)\d{{1,3}}\s+|\(\*+\)\s*)?(?:Bk\.?\s*|Bkz\.?\s*)?(?:{HADIS})\s*,\s*{_Z}*?\d{_Z}*(?:\.|(?=\n)|$)")
_SURE_DISARI = re.compile(rf"(?:(?<=^)|(?<=[\s\"”»’.!?]))[-–—]?\s*(?:{SURE})(?:\s+s[ûu]resi)?\s*(?:[,:]\s*\d{{1,3}}(?:\s*[-–,]\s*\d{{1,3}})*|"
                          rf"\d{{1,3}}\s*/\s*\d{{1,3}})\.?(?=\s|$)", re.M)
# kaynakta parantezi bozuk âyet atfı: "[Bakara, 284.", "(Meryem, 57]", "Mâide, 118]", "[Bakara, 179)"
_SURE_KIRIK = re.compile(rf"\s?[\(\[]\s*(?:{SURE})(?:\s+s[ûu]resi)?\s*[,:]\s*\d{{1,3}}(?:\s*[-–]\s*\d{{1,3}})?\s*[\)\]]?"
                         rf"|\s?(?<![\w'’])(?:{SURE})\s*,\s*\d{{1,3}}(?:\s*[-–]\s*\d{{1,3}})?\s*[\)\]]")
_YAPISIK_NO = re.compile(r"(?<=[^\W\d][.!?:;\"”»’)])(?<!No:)(?<!Sayı:)\d{1,3}(?=\s|$)")


def _zincir_mi(s):
    """Hadis kaynağı dizisi mi: sayı yoğun ("Tirmizî, Zühd, 25; İbn Mâce, Zühd, 39"), anlatı cümlesi değil."""
    sayi = len(re.findall(r"\d+|\b[IVXLC]{1,4}\b", s))
    return (sayi >= 2 or ";" in s) and len(s.split()) <= 6 + 4 * sayi


def _parantez(m, S):
    """Parantez bütünüyle kaynak gösterimiyse çıkar; ';' ile ayrılmış parçalarından yalnız bazıları kaynaksa yalnız onlar çıkar
    ("(esirlik anlamı içerisinde; bak., s. 127)" -> "(esirlik anlamı içerisinde)")."""
    ic = m.group(1) if m.group(1) is not None else m.group(2)
    if atif_mi(ic):
        return S
    parca = [p for p in re.split(r"\s*;\s*", ic)]
    if len(parca) > 1:
        kalan = [p for p in parca if not atif_mi(p)]
        if len(kalan) < len(parca):
            ac, kapa = ("(", ")") if m.group(1) is not None else ("[", "]")
            bas = m.group(0)[:len(m.group(0)) - len(m.group(0).lstrip())]
            return bas + ac + "; ".join(kalan) + kapa + S if kalan else S
    return m.group(0)


def ses_metni(t):
    """Seslendirmeye giden bir satırdan kaynak gösterimlerini çıkarır. Kaynak gösterimi olmayan satır olduğu gibi kalır."""
    if not t:
        return t
    S = "\u0000"   # çıkan yerin işareti: yalnız orada boşluk/noktalama toplanır (öteki satırlar değişmez, sesi yeniden üretilmez)
    y = _PARANTEZ.sub(lambda m: _parantez(m, S), t)
    y = _ZINCIR.sub(lambda m: S if _zincir_mi(m.group(0)) else m.group(0), y)
    y = _SURE_KIRIK.sub(S, y)
    y = _SURE_DISARI.sub(S, y)
    y = _YAPISIK_NO.sub(S, y)
    if S not in y:
        return t
    y = re.sub(r"\s*\u0000[\s\u0000]*(?=[.,;:!?»”’)]|$)", "", y)
    y = re.sub(r"\s*\u0000[\s\u0000]*", " ", y)
    y = re.sub(r"([,;])\s*(?=[,;.])", "", y)
    return y.strip()
