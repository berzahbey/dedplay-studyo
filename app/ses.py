"""0.5.43: seslendirmeye giden metinden yazarın kaynak gösterimleri çıkar (Zahir, 19 Ekim: "yazarın kaynak gösterdiği yerler
seslendirmede okunmamalı"). Yazılı çıktılara (EPUB, PDF, DOCX, TXT, HTML) dokunulmaz; yalnız Kitap Okuma'ya giden seslendirme EPUB'u.
Çıkanlar: âyet yerleri "(Kehf, 110; Fussilet, 6)", "[Enâm, 149]", "-Kehf, 54", "Bakara 2/40"; hadis kaynakları "(Müslim)",
"Tirmizî, Zühd, 25; İbn Mâce, …"; kitap/sayfa atıfları "(M. 54)", "(bkz. s. 12)", "(Ta'rîfât, 130)", "(Mevzûât el-Ulûm, I, 358)";
not işaretleri "(3)", "(٢)", "(Haşiye-1)", "…söylemiştir.55". Kalanlar: yıllar ve tarihler "(1953)", "(19 Kasım 1908)", "(ölm. 456/1065)",
"(H. 505)", açıklama parantezleri "(yani …)", sayı değerleri "(400.000)"."""
import collections
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
_KISALTMA = re.compile(r"(?<![\w])(?:s|ss|sh|sf|c|no|nr|vol|bl|bab)\.\s*\d|(?<![\w])(?:s|ss|sh|sf|c)\s?:\s*(?:\d|[IVX]+\b)|\b(?:bkz|bk|bak|krş|karş|a\.g\.e|age|a\.g\.m|nşr|neşr|çev|trc|thk|tah|"
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
    if re.match(r"(?:bkz|bk|krş|karş)\b\.?|bak\s?[.:]", c, re.I):
        return True                                             # 0.5.48: "(Bkz: Necmi Uyanık, … Doktora Tezi, … sh: 12)" uzun da olsa
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


# ---------- 0.5.48: Latin harfli Arapça ibareler (Zahir, 27 Ekim) ----------
# Tırnak içindeki Arapça ibare ("«ve lekad yessernâ'l-Kur'âne li'z-zikri…»") Türkçe sesle okununca anlaşılmıyor. Arkasından meali geliyorsa
# ("… yani 'Hüküm ancak Allah'ındır'", "(Hüküm, yalnız Allah'a âittir.)") ibare okunmaz, meal okunur; meali yoksa yerine "Arapça ibare" okunur
# (cümle bozulmasın: "«Semiallâhu limen hamideh» ve «Rabbenâ lekel hamd» demeksizin"). Ad ve eser adları (çoğu kelimesi büyük harfle başlayan,
# arkasından "isimli/adlı…" gelen), Osmanlıca tamlamalar ("Emr-i bi'l-ma'rûf") ve ikiden az kelimeli ibareler okunur.
_AR_ISLEV = set("fe fî fi min mine alâ ala ilâ ila bi li lâ la innâ inne innemâ innehu kad lekad hüve huve hiye ente ene nahnu mâ ma men "
                "entüm hum hüm kânû kâne leyse illâ ellezî ellezîne allâhu allâh allâhi rabbi rabbenâ rabbinâ kul emme ammâ seyyidinâ aleyhi "
                "aleyke aleyküm ve'l ev lev izâ izen sümme hattâ".split())
_AR_EK = re.compile(r"(?:hu|hû|hum|hüm|kum|küm|ke|kü|nâ|în|ûn|âni|tü|tu|hâ|ehu|uhu)$")
_AR_TARIF = re.compile(r"\w['’]?(?:l|r|s|n|z|t|d|ş)-\w|['’](?:l|r|s|n|t|d|z)-?\w|\b(?:el|er|es|en|et|ed|ez|eş)-\w", re.I)
_AR_SONRA = re.compile(r"^\W{0,3}\s*(?:isimli|adlı|adındaki|adında|nâmındaki|namındaki|nam|isminde|ismindeki|başlıklı|unvanlı|ünvanlı|eser|kitab|"
                       r"risâle|risale|dergi|gazete|mecmua|partisi|cemiyeti|derneği|tarikat)", re.I)
_AR_TIRNAK = re.compile(r"«([^«»\n]{3,400})»|“([^“”\n]{3,400})”|\"([^\"\n]{3,400})\"")
_AR_MEAL = re.compile(r"^[\s,:;]*(?:yani|yâni|ya'ni|yânî)\b[\s,:]*|^\s*(?=\((?![^()]*\d)[^()]{8,}\))", re.I)


def _ar_nr(w):
    return re.sub(r"[^a-zçğıöşüâîû'’-]", "", w.replace("İ", "i").replace("I", "ı").lower())


def _ar_kelime(w):
    k = _ar_nr(w).strip("-'’")
    if not k:
        return None
    if k in _AR_ISLEV or _AR_TARIF.search(k):
        return True
    if re.search(r"-[ıiuü]$", k):
        return False                                          # Osmanlıca izafet: Emr-i, Sazmân-ı
    try:
        from app import duzelt as DZ
        if DZ._gecerli_kelime(re.sub(r"[^a-zçğıöşü]", "", k.replace("â", "a").replace("î", "i").replace("û", "u"))):
            return False
    except Exception:
        return False
    return bool(re.search(r"[âîû]", k) or _AR_EK.search(k) or "'" in k or "’" in k or w.lstrip("-«\"“'(")[:1].islower())


def arapca_ibare_mi(ic, sonra=""):
    """Tırnak içi yazı Latin harfli Arapça ibare mi (0.5.48)."""
    ws = [w for w in ic.split() if _ar_nr(w).strip("-'’")]
    if len(ws) < 3 or _AR_SONRA.match(sonra):
        return False
    if sum(1 for w in ws if w.lstrip("-«\"“'(")[:1].isupper()) >= 0.6 * len(ws):
        return False                                          # ad / eser adı: İhvanü's-Safâ ve Hullenü'l-Vefâ
    if any(re.search(r"-[ıiuü]$", _ar_nr(w)) for w in ws):
        return False
    b = [_ar_kelime(w) for w in ws if _ar_nr(w).strip("-'’") != "ve"]   # "ve" iki dilde de var
    if not b:
        return False
    oran = sum(1 for x in b if x) / len(b)
    islev = sum(1 for w in ws if _ar_nr(w).strip("-'’") in _AR_ISLEV)
    isaret = islev or re.search(r"[âîû]|['’][lrsntdz]-|allâh|ullâh", ic)
    return bool(isaret) and (oran >= 0.75 or (oran >= 0.5 and islev >= 1))


def _arapca_ibareler(t, S):
    """Arapça ibare: meali arkasından geliyorsa çıkar (S), gelmiyorsa "Arapça ibare". Değişiklik yoksa t aynen döner."""
    if not re.search(r"[«“\"]", t):
        return t
    parca, son = [], 0
    for m in _AR_TIRNAK.finditer(t):
        ic = next(g for g in m.groups() if g is not None)
        sonra = t[m.end():]
        if not arapca_ibare_mi(ic, sonra[:40]):
            continue
        parca.append(t[son:m.start()])
        meal = _AR_MEAL.match(sonra)
        if meal:
            parca.append(S)
            son = m.end() + meal.end()
        else:
            parca.append("Arapça ibare")
            son = m.end()
    if not parca:
        return t
    parca.append(t[son:])
    return "".join(parca)


# ---------- 0.5.48: OCR'ın uydurduğu tekrarlar ve bozuk Arap harfli satırlar (Zahir, 27 Ekim) ----------
# Surya taramada okuyamadığı satırda bir kelimeyi döngüye girip 10-20 kez yazabiliyor ("المراد المراد المراد …", "Maria Maria …"): art arda
# 4 ve daha çok aynı kelime tek kelimeye iner. Arap harfli parça Arapça sesle (FastPitch) okunur; Urduca harfli (OCR çöpü: "ڊو رڈ"),
# Farsça/Osmanlıca harfli (پ چ ژ گ ڭ: Arapça ses okuyamaz), çoğu tek-iki harfli parçalardan oluşan ya da döngülü parça okunmaz.
_TEKRAR = re.compile(r"(?<!\S)(\S{1,30})(?:[\s،,.]+\1(?!\S)){3,}")
_ARAP_PARCA = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿][؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿\sً-ٰٟ"
                         r"،؛؟.:!?()\-0-9٠-٩۰-۹«»\"]*")
_URDU = re.compile(r"[ٹڈڑںھےۓڊڻ۽ڙڳڱ]")
_FARSCA = re.compile(r"[پچژگڭ]")
_OSMANLI = re.compile(r"[\u06A9\u06CC\u06D5\u06C0]")   # ک ی ە ۀ


def _arap_bozuk(p):
    harfli = re.findall(r"[ء-يٱ-ۓ]+", re.sub(r"[ً-ٰٟ]", "", p))
    if not harfli:
        return False
    if _URDU.search(p) or _FARSCA.search(p) or _TEKRAR.search(p):
        return True
    hareke = len(re.findall(r"[\u064B-\u0652]", p))
    if hareke < 0.05 * sum(len(w) for w in harfli) and _OSMANLI.search(p):
        return True                                   # harekesiz Farsça/Osmanlıca yazı (ک ی ە): belge, gazete resmi
    say = collections.Counter(harfli)
    if len(harfli) >= 6 and say.most_common(1)[0][1] >= max(4, 0.25 * len(harfli)):
        return True                                   # bitişik yazılmış döngü: "المعارض المعارالمعارض المعارض …"
    kisa = sum(1 for w in harfli if len(w) <= 2)
    return len(harfli) >= 3 and kisa > 0.5 * len(harfli)


def _ocr_artiklari(t, S):
    y = _TEKRAR.sub(lambda m: m.group(1), t)
    return _ARAP_PARCA.sub(lambda m: S if _arap_bozuk(m.group(0)) else m.group(0), y)


def ses_metni(t):
    """Seslendirmeye giden bir satırdan kaynak gösterimlerini çıkarır. Kaynak gösterimi olmayan satır olduğu gibi kalır."""
    if not t:
        return t
    S = "\u0000"   # çıkan yerin işareti: yalnız orada boşluk/noktalama toplanır (öteki satırlar değişmez, sesi yeniden üretilmez)
    y = _arapca_ibareler(_ocr_artiklari(_ocr_artiklari(t, S), S), S)   # 0.5.48 (iki kez: tekrar silinince Arapça parça yeniden ölçülür)
    ar = y != t
    y = _PARANTEZ.sub(lambda m: _parantez(m, S), y)
    y = _ZINCIR.sub(lambda m: S if _zincir_mi(m.group(0)) else m.group(0), y)
    y = _SURE_KIRIK.sub(S, y)
    y = _SURE_DISARI.sub(S, y)
    y = _YAPISIK_NO.sub(S, y)
    if S not in y:
        return y if ar else t
    y = re.sub(r"\s*\u0000[\s\u0000]*(?=[.,;:!?»”’)]|$)", "", y)
    y = re.sub(r"\s*\u0000[\s\u0000]*", " ", y)
    y = re.sub(r"([,;])\s*(?=[,;.])", "", y)
    return y.strip()
