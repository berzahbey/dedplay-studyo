"""0.5.53: Yapay zekâ denetimi (Dedplay Hazırlık 0.5.3'ten Stüdyo'ya taşındı; Hazırlık da bu modülü kullanır: kod tek yerde).

Görevler (hepsi bütün kitaplara aynı kuralla; kitaba özel elle düzeltme yok):
  parantez : cümle içindeki parantez "kaynak gösterimi" mi (B. Lewis, The Middle East…) "açıklama" mı? Kaynak metinde kalır,
             yalnız "okunmaz" işaretlenir (seslendirme okumaz).
  sayi     : kelimeye/tırnağa yapışık kalmış, bağlanamamış dipnot numaraları -> okunmaz.
  satir    : ana metne karışmış dipnot/kaynak satırları ("433 Besim Atalay- a.g.e., sh: 93.") -> okunmaz (kaynağa yapışık ana
             metin okunur).
  resim    : ana metne girmiş fotoğraf/gazete kupürü/belge yazısı -> okunmaz (kupür kümesi kuralı).
  kelime   : sözlükte olmayan kelimeler: OCR hatası mı, doğrusu ne? Yalnız ölçü kurallarından geçen düzeltme uygulanır.
Modelin her kararı ölçü kuralından geçer; kabul edilmeyen öneriler de raporda görünür. Ana metinden hiçbir şey silinmez.
Model cevapları kitap klasöründe (denetim_kararlar.json): yarıda kalan denetim kaldığı yerden sürer; cevabı veren model "_m"."""
import collections
import hashlib
import json
import os
import re
import time
from pathlib import Path

OK_AC, OK_KAPA = "", ""          # okunmaz işareti (kitap.json metninde); EPUB'da <span class="okunmaz">
NOT = re.compile(r"\{\{n\d{4,}\}\}")
KELIME = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)?")
SAYGI = re.compile(r"^\s*(?:r\.?\s?a\.?|r\.?\s?anh|s\.?\s?a\.?\s?v\.?|a\.?\s?s\.?|c\.?\s?c\.?|k\.?\s?s\.?|ra|sav|as|cc)\s*$", re.I)
TARIH = re.compile(r"^\s*(?:[mhvöd]\.\s*)?\d{1,4}(?:\s*[-–/]\s*\d{1,4})?\s*(?:[mh]\.?)?\s*$", re.I)
SEHIR = (r"İstanbul|Ankara|İzmir|Konya|Bursa|Beyrut|Kahire|Bağdat|Bağdad|Şam|Dımaşk|Tahran|Paris|London|Londra|Leiden|Berlin|"
         r"Oxford|Cambridge|New York|Bulak|Bûlâk|Kum|Necef|Mısır|Haydarabad|Lahor|Leipzig|Wien|Viyana")
# Kaynak işareti (modelin "kaynak" kararı ancak bunlardan biri varsa ya da parantez bir alıntının hemen ardındaysa kabul):
# kaynak kelimeleri, "Şehir, yıl" ya da "Yazar, Eser" biçimi. Yalnız tarih/yıl kaynak işareti DEĞİLDİR (tarih okunur).
GUCLU_KAYNAK = re.compile(
    rf"\bsh\s*[:.]|\bs\.\s*[0-9]|\bc\s*[:.]\s*[0-9IVX]|\bcilt\b|nüsha|[Mm]ecmua|[Dd]ergi(?:si)?\b|[Gg]azete(?:si)?\b|tarihli|"
    rf"\bYay\b|\bYay\.|\bYayın|\ba\.\s?g\.\s?[em]\b|\b[Bb]kz\b|\bBk\.|\bvd\.|\bbaskı|"
    rf"\b(?:{SEHIR})\s*,?\s*[0-9]{{4}}|"
    rf"^\s*(?:[A-ZÇĞİÖŞÜÂ][\w'’.]*\s+){{0,3}}[A-ZÇĞİÖŞÜÂ][\w'’.]*\s*[,–-]\s*\S")
KAYNAK_SATIRI = re.compile(rf"\ba\.\s?g\.\s?[em]\b|\bsh\s*[:.]\s*\d|\bs\.\s*\d|\bc\s*[:.]\s*[\dIVX]|\bYay(?:ınları|\.)|\bBkz|\bbkz|"
                           rf"(?:{SEHIR}),?\s*(?:1[5-9]\d\d|20[0-2]\d)")
KAPANIS = "\"”»'’"


def _kucuk(w):
    return w.replace("I", "ı").replace("İ", "i").lower()


_IMSIZ = str.maketrans("ıişçğöüâîûíáéÍÁÉ", "iiscgouaiuiaeiae")
# 0.4.4: yabancı dilde alıntı/künye (bu kelimeler 2+ kez geçiyorsa kelime düzeltmesi sorulmaz: "Die Welt des Islams")
YABANCI = re.compile(r"\b(?:the|of|and|for|in|with|des|die|das|und|von|journal|review|studies)\b", re.I)


# 0.5.0: eski yazım farkı (kalb/kalp, münâfıkdır/münafıktır, cild/cilt, şapka): OCR hatası değil, yazarın imlâsı -> düzeltilmez
_IMLA = str.maketrans("bpdtgkâîû", "ppttkkaiu")   # 0.5.1: c/ç ve g/ğ OCR farkıdır (imlâ değil)


def _imla(w):
    return _kucuk(w).translate(_IMLA)


# 0.5.0: olumsuzluk eki eklenip çıkarılmaz ("liliyorlar" -> "bilmiyorlar" anlamı tersine çevirir)
OLUMSUZ = re.compile(r"m[ıiuü]yor|m[ae]z|m[ae]d[ıi]|m[ae]m[ıi]ş|m[ae]y[ae]c[ae]k|m[ae]s[ıi]n")
KAYNAK_SON = re.compile(r"\b(?:sh|s)\s*[.:]?\s*\d+(?:\s*[-–,]+\s*\d+)*(?:\s*vd\.?)?|\bnüsha\.?"
                        r"|\b(?:1[5-9]\d\d|20[0-2]\d)\b(?:\s*vd\.)?(?:\s*t[âa]rihli)?(?:\s+\S+\s+(?:gazete|dergi|mecmua)\w*)?")
KIRIL = re.compile(r"[\u0400-\u04ff]")


def _imsiz(w):
    """Harf işaretleri atılmış küçük biçim (OCR'ın düşürdüğü nokta/çengel uzaklığa sayılmaz)."""
    return _kucuk(w).translate(_IMSIZ)


def _anahtar(*p):
    return hashlib.sha1("\x1f".join(p).encode("utf-8")).hexdigest()[:16]


def _uzaklik(a, b):
    """Uzaklık (0.5.1: yer değiştirmiş iki komşu harf bir sayılır: "Cenent" -> "Cennet", "evvlece" -> "evvelce")."""
    if a == b:
        return 0
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[-1][-1]


# 0.5.1: OCR'ın düşürdüğü nokta/çengel geri konuyor ("varilmaz" -> "varılmaz", "Ittihadçı" -> "İttihadçı"): yalnız düz harf ->
# Türkçe harf yönünde, başka değişiklik yok. Sözlük böyle çekimli kelimeyi tanımasa da kabul edilir.
_NOKTA = {("i", "ı"), ("I", "İ"), ("s", "ş"), ("S", "Ş"), ("c", "ç"), ("C", "Ç"), ("g", "ğ"), ("o", "ö"), ("O", "Ö"),
          ("u", "ü"), ("U", "Ü")}


def _nokta_geri(w, d):
    return len(w) == len(d) and w != d and all(a == b or (a, b) in _NOKTA for a, b in zip(w, d))


def _baglam(metin, bas, son, gen=130):
    s = NOT.sub("", metin[max(0, bas - gen):bas]).replace(OK_AC, "").replace(OK_KAPA, "")
    e = NOT.sub("", metin[son:son + gen]).replace(OK_AC, "").replace(OK_KAPA, "")
    return ("…" if bas > gen else "") + s, e + ("…" if son + gen < len(metin) else "")


def _okunmaz_icinde(metin, i):
    return metin.rfind(OK_AC, 0, i) > metin.rfind(OK_KAPA, 0, i)


# ---------------------------------------------------------------- istemler
SISTEM = ("Sen Türkçe basılı kitapların OCR ile okunmuş metnini denetleyen dikkatli bir editörsün. Kitaplar çoğunlukla "
          "Osmanlıca kökenli kelimeler, şapkalı yazım (â, î, û) ve Arapça/Farsça özel isimler içerir; bunlar doğrudur. "
          "Yalnız istenen soruya cevap ver; cevabın yalnız JSON olsun, açıklama yazma.")

ISTEM_PARANTEZ = """PARANTEZ GÖREVİ. Aşağıdaki her maddede bir cümle ve içinde «( )» ile gösterilen bir parantez var.
Her parantez için türü seç:
- "kaynak": bir alıntının ya da bilginin NEREDEN alındığını gösterir: yazar adı, eser/dergi/gazete adı, cilt, sayfa, sayı,
  basım yeri ya da yılı. Örnekler: (B. Lewis, The Middle East and the West) · (Türk Yurdu Mecmuası, c: I) · (İslâm Mecmuası)
  · (Cerrahoğlu, Mehmed Âkif) · (Bkz. Humeynî, İslâm Fıkhı'nda Devlet, sh. 12) · bir alıntının hemen arkasındaki (Şeyh Abduh)
- "aciklama": cümlenin anlamına ait açıklama, eş anlam, çeviri, kişi ya da yer açıklaması, tarih bilgisi. Örnekler:
  (zındıklar) · (uyku ile uyanıklık arası) · (v. 833) · (İbn Ziyad) bir kişinin kim olduğunu açıklıyorsa · (CHP prensipleri)
Emin değilsen "aciklama" seç.
Cevap biçimi: [{{"no": 1, "tur": "kaynak"}}, ...]

{maddeler}"""

ISTEM_SAYI = """SAYI GÖREVİ. Aşağıdaki maddelerde «» içindeki sayı bir kelimeye, noktaya ya da tırnağa bitişik duruyor.
Bu sayı basılı kitaptaki bir DİPNOT İŞARETİ mi (yazının parçası değil, üst simge numarası), yoksa metnin parçası mı
(yıl, adet, sayfa, âyet numarası, sıra numarası)? Emin değilsen dipnot_isareti: false.
Cevap biçimi: [{{"no": 1, "dipnot_isareti": true}}, ...]

{maddeler}"""

ISTEM_SATIR = """SATIR GÖREVİ. Aşağıdaki her madde kitabın ana metninde ayrı bir paragraf olarak duruyor. Bu paragraf
ana metnin parçası mı ("ana_metin"), yoksa sayfa altındaki bir dipnot ya da kaynak gösterimi mi ("kaynak")? Kaynak
satırları genellikle numarayla başlar ve yazar adı, eser adı, a.g.e., sh:, cilt, yıl içerir. Emin değilsen "ana_metin".
Cevap biçimi: [{{"no": 1, "tur": "ana_metin"}}, ...]

{maddeler}"""

ISTEM_RESIM = """RESİM GÖREVİ. Aşağıdaki paragraflar taranmış bir kitabın ana metninde duruyor ama çoğu kelimesi sözlükte yok.
Her paragraf için: kitabın kendi Türkçe metni mi ("ana_metin": yazarın cümleleri, eski kelimeler ve özel isimler çok olsa
da anlamlı akan metin), yoksa kitaba konmuş bir FOTOĞRAFIN, GAZETE KUPÜRÜNÜN, belgenin ya da resmin içindeki yazının OCR ile
okunmuş hâli mi ("resim": bozuk, anlamsız kelime dizileri, yarım satırlar, başka dilde (Fince, İngilizce, Rusça…) yazı)?
Emin değilsen "ana_metin".
Cevap biçimi: [{{"no": 1, "tur": "ana_metin"}}, ...]

{maddeler}"""

ISTEM_KELIME = """KELİME GÖREVİ. Aşağıdaki kelimeler taranmış bir kitaptan OCR ile okundu ve sözlükte bulunamadı.
Her kelime için: OCR'ın yanlış okuduğu bir kelime mi? Öyleyse doğrusu ne?
- Eski/Osmanlıca kelimeler (ehl, âid, ictihad, tenkid), şapkalı yazımlar, özel isimler (Efgânî, Mollabaşı), Arapça
  ibareler ve yabancı kelimeler DOĞRUDUR: hata: false.
- Yalnız OCR'ın harf karıştırması düzeltilir: ı/i/l/I/1, rn/m, ş/s, ğ/g, c/e, ü/ö, eksik ya da fazla bir harf,
  bitişik yazılmış iki kelime ("AliŞah" -> "Ali Şah"). Kelimenin eki ve anlamı değişmez.
- Emin değilsen hata: false. "dogru" alanına yalnız düzeltilmiş tek kelimeyi (ya da ayrılmış iki kelimeyi) yaz.
Cevap biçimi: [{{"no": 1, "hata": false, "dogru": "kelime"}}, ...]

{maddeler}"""


# Gemini grup büyüklükleri (madde/istek). Tahrif 1: parantez ~700 -> 5, sayı ~140 -> 1, satır ~16 -> 1, kelime ~3.600 -> 10 istek
GEMINI_GRUP = {"parantez": 150, "sayi": 150, "satir": 100, "kelime": 400, "resim": 60}
# Flash-Lite: günde 500 istek (28 Ekim): daha küçük gruplar (her maddeye daha çok dikkat), kitap başına ~50 istek
GEMINI_LITE_GRUP = {"parantez": 50, "sayi": 60, "satir": 40, "kelime": 120, "resim": 25}

class Denetci:
    """klasor: kitabın klasörü (denetim_kararlar.json burada). model: .sor(sistem, kullanici, en_fazla) -> metin ya da
    (metin, model adı) ve .ad veren nesne (Stüdyo: yz.Gemini; Hazırlık: yerel MLX ya da Gemini). on_ek: kararların ön eki
    ("g:" Gemini; "" yerel model): iki kaynağın kararları karışmaz."""

    def __init__(self, klasor, ilerleme=None, model=None, on_ek="g:"):
        self.klasor = Path(klasor)
        self.ilerleme = ilerleme or (lambda m: None)
        self._model = model
        self.on_ek = on_ek
        self.kararlar_yolu = self.klasor / "denetim_kararlar.json"
        try:
            self.kararlar = json.loads(self.kararlar_yolu.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.kararlar = {}
        self.degisiklik = []    # {gorev, kabul, once, sonra, baglam, neden}
        self.sure = {}

    @property
    def model(self):
        if self._model is None:
            from . import yz
            self._model = yz.Gemini(ilerleme=self.ilerleme)
        return self._model

    def _kaydet_kararlar(self):
        tmp = str(self.kararlar_yolu) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.kararlar, f, ensure_ascii=False)
        os.replace(tmp, self.kararlar_yolu)

    def _sor(self, gorev, istem, ogeler, grup, alan, ad):
        """ogeler: [(anahtar, madde metni)] -> {anahtar: cevap sözlüğü}. Önceki cevaplar saklıdır (yeniden sorulmaz)."""
        from .yz import json_al
        cevap = {}
        on = self.on_ek
        sorulacak = [(a, m) for a, m in ogeler if f"{on}{gorev}:{a}" not in self.kararlar]
        for a, _ in ogeler:
            if f"{on}{gorev}:{a}" in self.kararlar:
                cevap[a] = self.kararlar[f"{on}{gorev}:{a}"]
        if sorulacak and on:   # Gemini: Flash-Lite günde 500 istek: kitap başına ~50 isteğe sığan gruplar
            tablo = GEMINI_LITE_GRUP if "lite" in getattr(self.model, "ad", "") else GEMINI_GRUP
            grup = tablo.get(gorev, grup * 15)
        t0 = time.time()
        for k in range(0, len(sorulacak), grup):
            parca = sorulacak[k:k + grup]
            self.ilerleme(f"Denetim ({ad}): {k + len(parca)}/{len(sorulacak)}")
            metin = istem.format(maddeler="\n".join(f"{i}. {m}" for i, (_, m) in enumerate(parca, 1)))
            r = self.model.sor(SISTEM, metin, en_fazla=40 + 28 * len(parca))
            cevap_metni, veren = r if isinstance(r, tuple) else (r, getattr(self.model, "ad", ""))
            js = json_al(cevap_metni)
            liste = js if isinstance(js, list) else []
            no_ile = {int(x.get("no")): x for x in liste if isinstance(x, dict) and str(x.get("no", "")).isdigit()}
            for i, (a, _) in enumerate(parca, 1):
                x = no_ile.get(i)
                if x is not None and alan in x:
                    x = dict(x, _m=veren)
                    self.kararlar[f"{on}{gorev}:{a}"] = cevap[a] = x
            self._kaydet_kararlar()
        self.sure[ad] = round(time.time() - t0)
        return cevap

    # ------------------------------------------------------------ görevler
    def parantezler(self, bloklar):
        ogeler, yer = [], []
        rx = re.compile(r"\(([^()\n]{1,300})\)")
        for b in bloklar:
            if b["tur"] != "p":
                continue
            t = b["metin"]["tr"]
            for m in rx.finditer(t):
                if _okunmaz_icinde(t, m.start()):
                    continue
                ic = NOT.sub("", m.group(1)).strip()
                if not ic:
                    continue
                if SAYGI.match(ic) or TARIH.match(ic):
                    continue          # saygı kısaltması ve tarih: okunur (soru sorulmaz)
                once, sonra = _baglam(t, m.start(), m.end())
                a = _anahtar(ic, once[-60:], sonra[:60])
                ogeler.append((a, f"{once}«({ic})»{sonra}".replace("\n", " ")))
                yer.append((a, b, m.group(0), ic, once, sonra))
        cevap = self._sor("parantez", ISTEM_PARANTEZ, ogeler, 10, "tur", "parantez")
        isaret = []
        for a, b, tam, ic, once, sonra in yer:
            x = cevap.get(a)
            if not x or x.get("tur") != "kaynak":
                continue
            # 0.4.4: parantez kelimeye bitişikse ("İleri (Gazetesi)'nde") ya da hemen ardından ikinci parantez
            # geliyorsa ("(Mirza Hüseyin Ali)(1817-1892)") cümlenin parçasıdır: kaynak sayılmaz
            bitisik = bool(re.match(r"[\w'’(]", sonra[:1]))
            guclu = bool(GUCLU_KAYNAK.search(ic)) and not bitisik
            alinti_ardi = once.rstrip()[-1:] in KAPANIS or once.rstrip().endswith(("..", "!", "?"))
            kabul = (guclu or alinti_ardi) and not bitisik
            self.degisiklik.append({"gorev": "parantez", "kabul": kabul, "once": tam, "sonra": "(okunmaz)",
                                    "baglam": f"{once[-70:]}{tam}{sonra[:40]}",
                                    "neden": "cümleye bitişik (kaynak değil)" if bitisik else
                                    "kaynak işareti var" if guclu else "alıntının ardında" if alinti_ardi else
                                    "model 'kaynak' dedi ama metinde kaynak işareti yok"})
            if kabul:
                isaret.append((b, tam))
        return isaret

    def sayilar(self, bloklar, not_sayisi):
        ogeler, yer = [], []
        rx = re.compile(r"(?<=[^\W\d_]|[.,;:!?)" + re.escape(KAPANIS) + r"])([" + re.escape(KAPANIS) + r"]*)([0-9]{1,3})(?=[\s.,;:!?)]|$)")
        for b in bloklar:
            if b["tur"] != "p":
                continue
            t = b["metin"]["tr"]
            for m in rx.finditer(t):
                if _okunmaz_icinde(t, m.start()) or t[max(0, m.start() - 2):m.start()].endswith(("{{", "n0")):
                    continue
                n = int(m.group(2))
                if not 1 <= n <= not_sayisi + 100:
                    continue
                once, sonra = _baglam(t, m.start(), m.end(), 90)
                a = _anahtar(m.group(0), once[-50:], sonra[:50])
                ogeler.append((a, f"{once}«{m.group(0)}»{sonra}".replace("\n", " ")))
                yer.append((a, b, m.start(2), m.end(2), m.group(0), once, sonra))
        cevap = self._sor("sayi", ISTEM_SAYI, ogeler, 12, "dipnot_isareti", "sayı")
        isaret = []
        for a, b, bas, son, tam, once, sonra in yer:
            x = cevap.get(a)
            if not x or x.get("dipnot_isareti") is not True:
                continue
            self.degisiklik.append({"gorev": "sayi", "kabul": True, "once": tam, "sonra": "(okunmaz)",
                                    "baglam": f"{once[-60:]}{tam}{sonra[:30]}", "neden": "bağlanamamış dipnot işareti"})
            isaret.append((b, bas, son))
        return isaret

    def satirlar(self, bloklar):
        ogeler, yer = [], []
        for b in bloklar:
            if b["tur"] != "p":
                continue
            t = NOT.sub("", b["metin"]["tr"]).strip()
            if OK_AC in t or len(t.split()) > 45 or not KAYNAK_SATIRI.search(t):
                continue
            a = _anahtar(t)
            ogeler.append((a, t.replace("\n", " ")))
            yer.append((a, b, t))
        cevap = self._sor("satir", ISTEM_SATIR, ogeler, 10, "tur", "satır")
        isaret = []
        for a, b, t in yer:
            x = cevap.get(a)
            if not x or x.get("tur") != "kaynak":
                continue
            bas_no = bool(re.match(r"^\s*\(?\d{1,3}\)?\s*[-.)]?\s", t))
            kesim = None
            if len(t.split()) > 15:
                # 0.5.0: kaynak satırına ana metin yapışmış ("303 … İstanbul 2007 mes'elenin Eskişehir…"): yalnız kaynak kısmı
                # (en çok 15 kelime, son kaynak işaretine kadar: sayfa, yıl, "… gazeteleri", nüsha) okunmaz; arkasında en az 5 kelime kalır
                o = b["metin"]["tr"]
                for m in KAYNAK_SON.finditer(o):
                    if len(NOT.sub("", o[:m.end()]).split()) > 15:    # kaynak kısmı kısa olur (uzunsa ana metindir)
                        break
                    if len(NOT.sub("", o[m.end():]).split()) >= 5:
                        kesim = m.end()
            kabul = bas_no or len(t.split()) <= 15
            if kabul and len(t.split()) > 15 and kesim is None:
                kabul = False
            self.degisiklik.append({"gorev": "satir", "kabul": kabul, "once": t[:200],
                                    "sonra": "(okunmaz paragraf)" if kesim is None else
                                    f"(yalnız kaynak kısmı okunmaz: «{NOT.sub('', b['metin']['tr'][:kesim]).strip()[-60:]}»)",
                                    "baglam": "", "neden": "numaralı kaynak satırı" if bas_no else
                                    "kısa kaynak satırı" if kabul else "uzun paragraf: ana metin korunur"})
            if kabul:
                isaret.append((b, kesim))
        return isaret

    def resimler(self, bloklar):
        """Ana metne girmiş resim/gazete kupürü yazısı (Fince Kur'an sayfası, bozuk okunmuş kupür, belge fotoğrafı).
        Sorulan: kelimelerinin en az %20'si sözlükte olmayan (ya da Kiril harfli) paragraf; 0.5.2: bunların ±2 komşusundaki kısa
        (6 kelimeden az) satırlar da ("Bulmaca eki ve Şirinler'in 9. kitabı", "DOSYA RO : 1979/333").
        Kabul (0.5.2): model "resim" dedi ve (a) kelimelerin en az %35'i sözlükte yok ya da Kiril harfi var, ya da (b) dipnot atfı
        yok ve ±2 komşusundan biri de "resim" (kupür kümesi). Tek başına duran, dipnotlu ya da çoğu sözlükte olan paragraf yazarın
        metnidir ("Baden Württemberg Eyâlet Başbakanı Stefan Mappus…", "…pekçok yazı yazdılar.567"): okunur."""
        from . import rapor as R
        ps = [b for b in bloklar if b["tur"] == "p"]
        bilgi = []
        for b in ps:
            t = NOT.sub("", b["metin"]["tr"]).strip()
            ws = [w for w in KELIME.findall(t) if len(w) >= 3]
            oran = (sum(1 for w in ws if not R._gecerli(_kucuk(re.split(r"['’]", w)[0]))) / len(ws)) if ws else 0
            bilgi.append({"b": b, "t": t, "n": len(t.split()), "oran": oran, "kiril": bool(KIRIL.search(t)),
                          "not": bool(NOT.search(b["metin"]["tr"])), "isaretli": OK_AC in b["metin"]["tr"]})
        aday = set()
        for i, x in enumerate(bilgi):
            if not x["isaretli"] and x["t"] and ((len([w for w in KELIME.findall(x["t"]) if len(w) >= 3]) >= 6 and x["oran"] >= 0.20)
                                                 or x["kiril"]):
                aday.add(i)
        for i in list(aday):
            for k in range(max(0, i - 2), min(len(bilgi), i + 3)):
                if k not in aday and not bilgi[k]["isaretli"] and 0 < bilgi[k]["n"] < 6 and not bilgi[k]["not"]:
                    aday.add(k)
        sirali = sorted(aday)
        ogeler = [(_anahtar(bilgi[i]["t"]), bilgi[i]["t"][:500].replace("\n", " ")) for i in sirali]
        cevap = self._sor("resim", ISTEM_RESIM, ogeler, 5, "tur", "resim")
        resim = {i for i in sirali if (cevap.get(_anahtar(bilgi[i]["t"])) or {}).get("tur") == "resim"}
        isaret = []
        guclu_set = {i for i in resim if bilgi[i]["oran"] >= 0.35 or bilgi[i]["kiril"]}
        # 0.5.3: "resim" kararları arada en çok 2 paragraf boşlukla kümelenir; kümede güçlü (%35+ ya da Kiril) üye yoksa ve
        # üyelerin sözlükte olmayan kelime oranları toplamı 0,5'e varmıyorsa küme yazarın metnidir (yanlış "resim" kararları
        # birbirini sürüklemesin: "Şu yaptığınız yalan…" + "Ne kadar yalancı olduğunuzu,")
        kume_guclu, onceki, kume = {}, None, []
        for i in sorted(resim) + [None]:
            if kume and (i is None or i - onceki > 3):
                g = any(k in guclu_set for k in kume) or sum(bilgi[k]["oran"] for k in kume) >= 0.5
                kume_guclu.update({k: g for k in kume})
                kume = []
            if i is not None:
                kume.append(i)
                onceki = i
        for i in sorted(resim):
            x = bilgi[i]
            guclu = i in guclu_set
            # 0.5.3: küme yalnız güçlü bir resim komşusuyla kurulur (yanlış bir "resim" kararı komşularını sürüklemesin:
            # "Ne kadar yalancı olduğunuzu," alıntı satırları); iki nokta ile biten kısa satır yazarın alıntı girişidir
            # ("Fethullah Gülen:", "«Sonuç bildirgesinden:")
            kume = kume_guclu.get(i, False)
            kisa_yazar = x["n"] < 6 and x["t"].rstrip().endswith(":") and not re.search(r"[\u0600-\u06ff]", x["t"])
            kabul = guclu or (kume and not x["not"] and not kisa_yazar)
            neden = (f"kelimelerin %{round(x['oran'] * 100)}'i sözlükte yok" + (", Kiril harfi" if x["kiril"] else "")) if guclu else \
                "kupür kümesinde" if kabul else \
                ("dipnot atfı var (yazarın metni)" if x["not"] else
                 "kısa satır yazarın alıntı girişi (iki nokta ile bitiyor)" if kisa_yazar else
                 "yanında kupür yok, kelimelerin çoğu sözlükte var (yazarın metni)")
            self.degisiklik.append({"gorev": "resim", "kabul": kabul, "once": x["t"][:160], "sonra": "(okunmaz paragraf)",
                                    "baglam": "", "neden": neden})
            if kabul:
                isaret.append(x["b"])
        return isaret

    def kelimeler(self, kit, metinler):
        from . import rapor as R
        say = collections.Counter()
        kucuk_say = collections.Counter()
        ornek = {}
        for t in metinler:
            temiz = NOT.sub(" ", t)
            for m in KELIME.finditer(temiz):
                w = m.group(0)
                say[w] += 1
                kucuk_say[_kucuk(w)] += 1
                if w not in ornek:
                    ornek[w] = _baglam(temiz, m.start(), m.end(), 45)

        def gecerli(w):
            k = _kucuk(re.split(r"['’]", w)[0])
            return len(k) <= 1 or R._gecerli(k)

        def taninir(w):
            """Doğru biçim sözlükte ya da kitabın başka yerinde (en az 2 kez) var mı."""
            return all(gecerli(p) or kucuk_say[_kucuk(p)] >= 2 for p in w.split())
        self.ilerleme("Denetim (kelime): adaylar seçiliyor")
        adaylar = [w for w in say if say[w] <= 3 and len(w) >= 3 and not gecerli(w) and not re.search(r"[؀-ۿ]", w)
                   and len(YABANCI.findall(" ".join(ornek[w]))) < 2      # 0.4.4: yabancı dilde alıntı sorulmaz
                   and not re.search(r"\w-\s*$", ornek[w][0])]           # "al- mişlardır": satır sonu bölünmesi
        ogeler = [(_anahtar(w), f"«{w}» — {ornek[w][0]}{w}{ornek[w][1]}".replace("\n", " ")) for w in adaylar]
        cevap = self._sor("kelime", ISTEM_KELIME, ogeler, 20, "hata", "kelime")
        duzelt = {}
        for w in adaylar:
            x = cevap.get(_anahtar(w))
            if not x or x.get("hata") is not True:
                continue
            d = str(x.get("dogru") or "").strip().strip(".,;:")
            if not d or d == w:
                continue
            uz = _uzaklik(_imsiz(w), _imsiz(d))           # 0.4.4: ı/i, ş/s, ç/c… farkı sayılmaz
            ham = _uzaklik(_kucuk(w), _kucuk(d))
            neden = None
            if uz > 2 or uz > max(1, len(w) // 4) or ham > max(2, len(w) // 2):
                neden = f"çok farklı ({uz} harf)"
            elif _imla(w) == _imla(d):
                neden = "eski yazım farkı (yazarın imlâsı korunur)"
            elif bool(OLUMSUZ.search(_imsiz(w))) != bool(OLUMSUZ.search(_imsiz(d))):
                neden = "olumsuzluk eki değişiyor (anlam tersine döner)"
            elif not taninir(d) and not _nokta_geri(w, d):
                neden = "önerilen kelime ne sözlükte ne kitapta var"
            elif len(d.split()) > 2:
                neden = "ikiden fazla kelime"
            kabul = neden is None
            if kabul:
                if w[:1].isupper() and not d[:1].isupper():
                    d = d[:1].upper() + d[1:]
                duzelt[w] = d
            self.degisiklik.append({"gorev": "kelime", "kabul": kabul, "once": w, "sonra": d,
                                    "baglam": f"{ornek[w][0][-60:]}{w}{ornek[w][1][:40]}",
                                    "neden": "OCR harf hatası" if kabul else neden, "adet": say[w]})
        return duzelt

    # ------------------------------------------------------------ uygulama

    def calistir(self, kit):
        """Kitabı (kitap.json sözlüğü) yerinde denetler: okunmaz parçalar metinde OK_AC…OK_KAPA ile işaretlenir, kelime
        düzeltmeleri uygulanır. Dönen: aynı kit. Kaydetmek çağıranın işidir (Stüdyo: ses_yok'a çevirir; Hazırlık: EPUB'da span)."""
        bloklar = [b for b in kit["bloklar"] if not b.get("silindi") and isinstance(b.get("metin"), dict) and "tr" in b["metin"]]
        dipnotlar = kit.get("dipnotlar") or {}
        t0 = time.time()
        p_isaret = self.parantezler(bloklar)
        s_isaret = self.sayilar(bloklar, len(dipnotlar))
        satir_isaret = self.satirlar(bloklar)
        resim_isaret = self.resimler(bloklar)
        resimli = {id(b) for b in resim_isaret}
        metinler = [b["metin"]["tr"] for b in bloklar if id(b) not in resimli] + [v["metin"]["tr"] for v in dipnotlar.values()
                                                          if isinstance(v.get("metin"), dict) and "tr" in v["metin"]]
        duzelt = self.kelimeler(kit, metinler)

        # okunmaz işaretleri (blok içinde konuma göre, sondan başa)
        konum = collections.defaultdict(list)
        for b, tam in p_isaret:
            i = b["metin"]["tr"].find(tam)
            while i >= 0 and _okunmaz_icinde(b["metin"]["tr"], i):
                i = b["metin"]["tr"].find(tam, i + 1)
            if i >= 0:
                konum[id(b)].append((i, i + len(tam), b))
        for b, bas, son in s_isaret:
            konum[id(b)].append((bas, son, b))
        for b, kesim in satir_isaret:
            if kesim is None:
                konum[id(b)] = [(0, len(b["metin"]["tr"]), b)]
            else:
                konum[id(b)].append((0, kesim, b))
        for b in resim_isaret:
            konum[id(b)] = [(0, len(b["metin"]["tr"]), b)]
        for aralik in konum.values():
            b = aralik[0][2]
            t = b["metin"]["tr"]
            son_bas = len(t) + 1
            for bas, son, _ in sorted(aralik, key=lambda x: -x[0]):
                if son > son_bas:     # iç içe/örtüşen aralık: dıştaki yeter
                    continue
                t = t[:bas] + OK_AC + t[bas:son] + OK_KAPA + t[son:]
                son_bas = bas
            b["metin"]["tr"] = t
        # kelime düzeltmeleri (tam kelime, büyük/küçük harf aynen)
        if duzelt:
            rx = re.compile(r"(?<![\w])(" + "|".join(re.escape(w) for w in sorted(duzelt, key=len, reverse=True)) + r")(?![\w])")
            for b in bloklar:
                b["metin"]["tr"] = rx.sub(lambda m: duzelt[m.group(1)], b["metin"]["tr"])
            for v in dipnotlar.values():
                if isinstance(v.get("metin"), dict) and "tr" in v["metin"]:
                    v["metin"]["tr"] = rx.sub(lambda m: duzelt[m.group(1)], v["metin"]["tr"])
        self.sure["toplam"] = round(time.time() - t0)
        return kit

    def ozet(self):
        o = {}
        for d in self.degisiklik:
            g = o.setdefault(d["gorev"], {"kabul": 0, "ret": 0})
            g["kabul" if d["kabul"] else "ret"] += 1
        return o

    def rapor_metni(self, ad, ust=()):
        """Rapor: başlık + model satırı + ust (çağıranın satırları) + görev görev kabul/ret listesi."""
        m = self.model if self._model is not None else None
        kullanilan = dict(getattr(m, "kullanilan", {}) or {})
        s = [f"Dedplay — yapay zekâ denetimi: {ad}",
             f"model: {getattr(m, 'ad', '-')}" + (f" (kullanılan: {kullanilan})" if kullanilan else "")
             + f"; çağrı {getattr(m, 'sayac', {}).get('cagri', 0)}, süre {self.sure}"] + list(ust) + [""]
        adlar = {"parantez": "Kaynak parantezleri (okunmaz)", "sayi": "Bağlanamamış dipnot numaraları (okunmaz)",
                 "satir": "Ana metne karışmış kaynak satırları (okunmaz)",
                 "resim": "Ana metne girmiş resim/kupür yazısı (okunmaz)", "kelime": "Kelime düzeltmeleri (OCR)"}
        for g, baslik in adlar.items():
            ds = [d for d in self.degisiklik if d["gorev"] == g]
            kab = [d for d in ds if d["kabul"]]
            s.append(f"== {baslik}: {len(kab)} uygulandı, {len(ds) - len(kab)} önerildi ama kabul edilmedi")
            for d in kab:
                s.append(f"  + {d['once']}  ->  {d['sonra']}" + (f"  ({d['adet']} kez)" if d.get("adet") else "")
                         + (f"   « {d['baglam']} »" if d["baglam"] else ""))
            for d in ds:
                if not d["kabul"]:
                    s.append(f"  - {d['once']}  ->  {d['sonra']}   [{d['neden']}]" + (f"   « {d['baglam']} »" if d["baglam"] else ""))
            s.append("")
        return "\n".join(s)
