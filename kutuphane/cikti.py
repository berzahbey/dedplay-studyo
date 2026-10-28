"""Hazır kitapların dışarıya verilmesi.

1) Çıktı klasörü (CIKTI_DIR, varsayılan /dedplay/EPUB = /media/ZimaOS-HD/dedplay/EPUB): EPUB'lar dile göre klasörlerde
   Türkçe/, Osmanlıca/, Türkçe-Osmanlıca/, Arapça/, Arapça-Türkçe/  ->  "Eser adı - Yazar.epub"
2) Stüdyo'ya gönderme (tur 2/A): bölümlerin Türkçesi ve Kütüphane'nin Osmanlıcası (elle düzeltmeler dahil) satır satır
   eşleşik parçalar olarak, aynı süreçte gider; Stüdyo Osmanlıcayı yeniden çevirmez, seslendirir ve öteki biçimleri üretir.
"""
import os
import re
import shutil
import time
import unicodedata

import requests

from . import epub as EPUB
from . import kitap as K

CIKTI = os.environ.get("CIKTI_DIR", "/dedplay/EPUB")   # 0.5.40: varsayılan da dedplay (eskiden /cikti = .seslendirme)
STUDYO_URL = os.environ.get("STUDYO_URL", "http://host.docker.internal:8070").rstrip("/")
KLASOR_ADI = {("tr",): "Türkçe", ("osm",): "Osmanlıca", ("tr", "osm"): "Türkçe-Osmanlıca", ("ar",): "Arapça",
              ("ar", "tr"): "Arapça-Türkçe", ("en",): "İngilizce", ("en", "tr"): "İngilizce-Türkçe",
              ("fr",): "Fransızca", ("fr", "tr"): "Fransızca-Türkçe"}
_YASAK = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')
PARCA_HARF = 15000  # Stüdyo'ya giden bir parçanın (bir ses dosyasının) en fazla uzunluğu
DIPNOT_OSM = "حواشی"  # "DİPNOTLAR" başlığının Osmanlıcası (havâşî)


def epublari_sil(kit, yazilan):
    """0.5.39: kitap silinirken "dosyalarını da sil": kitabın CIKTI'deki EPUB'ları (durumdaki yollar ve kitabın adıyla
    her dil klasörü; aynı adlı kitap aynı kitaptır, 0.5.27). Dönen: silinen yollar."""
    silinen = []
    if not os.path.isdir(CIKTI):
        return silinen
    kok = os.path.realpath(CIKTI).rstrip("/") + "/"
    adaylar = list(yazilan or [])
    if kit:
        ad = dosya_adi(kit)
        adaylar += [os.path.join(k, ad + ".epub") for k in sorted(set(KLASOR_ADI.values()))]
    for rel in dict.fromkeys(adaylar):
        yol = os.path.join(CIKTI, rel)
        if os.path.isfile(yol) and os.path.realpath(yol).startswith(kok):
            os.remove(yol)
            silinen.append(yol)
    return silinen


def dosya_adi(kit):
    ku = kit["kunye"]
    asil = ku.get("asil_dil", "tr")
    baslik = ku["baslik"].get("tr") or ku["baslik"].get(asil) or "Kitap"
    yazar = ku.get("yazar", {}).get("tr") or ku.get("yazar", {}).get(asil) or ""
    ad = f"{baslik} - {yazar}" if yazar and yazar != baslik else baslik
    return re.sub(r"\s+", " ", _YASAK.sub(" ", ad)).strip(" .")[:120] or "Kitap"


def ciktiya_yaz(kit, epublar, epub_klasoru, onceki=None):
    """EPUB'ları dil klasörlerine kopyalar. Döndürür: yazılan yollar (CIKTI'ye göre). Klasör bağlı değilse None.
    onceki: bir önceki yazımın yolları (kitap adı değiştiyse eski dosyalar kaldırılır)."""
    if not os.path.isdir(CIKTI):
        ust = os.path.dirname(CIKTI.rstrip("/"))
        if ust != os.environ.get("DEDPLAY_DIR", "/dedplay").rstrip("/") or not os.path.isdir(ust):
            return None                     # çıktı klasörü bağlı değil (konteynerin içine yazılmasın)
        os.makedirs(CIKTI, exist_ok=True)   # /dedplay bağlı, EPUB klasörü henüz yok (tur 2/D)
    temel = dosya_adi(kit)
    ad, n = temel, 1
    # 0.5.25: aynı kitap yeniden işlenince eski EPUB'ın üzerine yazılır ("(2)" kopyası olmaz)
    while False and any(os.path.exists(os.path.join(CIKTI, KLASOR_ADI.get(tuple(e["diller"]), "-".join(e["diller"])), ad + ".epub"))
              and os.path.join(KLASOR_ADI.get(tuple(e["diller"]), "-".join(e["diller"])), ad + ".epub") not in (onceki or [])
              for e in epublar):
        n += 1                              # aynı adlı başka bir kitabın dosyası: üstüne yazma (tur 2/D)
        ad = f"{temel} ({n})"
    yeni = []
    for e in epublar:
        klasor = KLASOR_ADI.get(tuple(e["diller"]), "-".join(e["diller"]))
        hedef_klasor = os.path.join(CIKTI, klasor)
        os.makedirs(hedef_klasor, exist_ok=True)
        hedef = os.path.join(hedef_klasor, ad + ".epub")
        shutil.copyfile(os.path.join(epub_klasoru, e["dosya"]), hedef + ".tmp")
        os.replace(hedef + ".tmp", hedef)
        yeni.append(os.path.relpath(hedef, CIKTI))
    for eski in onceki or []:  # ad değişmişse eski kopya kalmasın (başka kitabın dosyasına dokunulmaz: sadece bizim yazdığımız)
        if eski not in yeni:
            try:
                os.remove(os.path.join(CIKTI, eski))
            except OSError:
                pass
    return yeni


# ---------------- Stüdyo ----------------
def _temiz(t):
    return re.sub(r"\s+", " ", K.NOT_ISARETI.sub("", t or "")).strip()

# ---------------- 0.5.42: seslendirmeye gitmeyen bölümler ----------------
# Kitabın ana metni olmayan bölümleri (kaynakça, dizin, sözlük, kısaltmalar, kronoloji, sonnotlar, yanlış-doğru cetveli, yayınevi künyesi)
# EPUB'da ve PDF/DOCX/TXT/HTML'de kalır; seslendirmeye gitmez (Stüdyo parçası "Ek_": Kitap Okuma yalnız "Parca_" okur).
def _ses_sade(t):
    t = K.NOT_ISARETI.sub("", t or "").replace("I", "ı").replace("İ", "i").lower().replace("ı", "i")
    t = "".join(c for c in unicodedata.normalize("NFD", t) if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z\s]", " ", t).split())


_SES_DISI_AD = re.compile(
    r"^(?:kaynakca|kaynaklar|bibli[a-z]*|secme bibli[a-z]*|yararlanilan (?:eser|kaynak)[a-z]*|okuma listesi)$"
    r"|(?:^|\s)dizin[a-z]*$|(?:^|\s)(?:indeks|index)[a-z]*$"
    r"|(?:^|\s)sozlug[a-z]*$|^sozluk$|^lugat[a-z]*$"
    r"|^kisaltma[a-z]*$|^kronoloji[a-z]*(?: tablo[a-z]*)?$"
    r"|^(?:dipnot[a-z]*|notlar|son ?not[a-z]*|aciklamalar)$|\sdipnot[a-z]*$"
    r"|yanlis.?dogru|dogru.?yanlis|hata.?sevap"
    r"|(?:^|\s)(?:yayinlari|yayinevi|matbaasi)$")
_SES_YIL = re.compile(r"\b(?:1[5-9]\d\d|20\d\d)\b")
_SES_KAYNAK = re.compile(r"\b(?:Yay\.|Yayınları|baskı|bsk\.|ed\.|trans\.|vol\.|Vol\.|pp\.|Press|Verlag|éd\.|Bd\.|Paris|London|Londra|Leiden|"
                         r"Kahire|Cairo|Beyrut|Beirut|Berlin|Oxford|Cambridge|Leipzig|İstanbul|Ankara|Bulak)\b")
_SES_NOT = re.compile(r"^\s*\(?\d{1,3}\)?\s*[-—–~.)]+\s*(?P<r>.*)$", re.S)          # not işaretiyle başlayan paragraf
_SES_NOT_KATI = re.compile(r"^\s*(?:\(\d{1,3}\)|\d{1,3}\s*[-—–~]+)\s*(?P<r>.*)$", re.S)  # "(3) …", "3 — …" (nokta değil)
_SES_DIZIN = re.compile(r"^[^:.!?]{2,50}:\s*[^.!?]{0,60}?\b\d{1,3}(?:\s*(?:vd\.?|n\.\s*\d+))?(?:\s*[,;]\s*\d{1,3}(?:\s*(?:vd\.?|n\.\s*\d+))?)*\s*\.?$")


def _ses_disi_bolum(baslik, metinler):
    """Bölüm seslendirmeye gitmez mi: (neden) ya da None. baslik: bölüm başlığı (yoksa ""), metinler: bölümün paragrafları."""
    if baslik and _SES_DISI_AD.search(_ses_sade(baslik)):
        return "başlık: " + baslik.strip()[:40]
    m = [K.NOT_ISARETI.sub("", t or "").strip() for t in metinler]
    m = [t for t in m if t]
    if len(m) < 5:
        return None
    n = len(m)
    def notmu(t):   # sonnot: "3 — Sübkî, Tabakât, IV, 102" ya da "(3) …"; gövdedeki numaralı paragraf ("3. Hanbeli …") sayılmaz
        r = _SES_NOT_KATI.match(t)
        return bool(r) and len(t.split()) <= 60 and bool(re.search(r"\d|,\s*[IVXL]+\s*,", r.group("r")))
    if sum(1 for t in m if notmu(t)) >= 0.7 * n:
        return "sonnot"
    if sum(1 for t in m if _SES_YIL.search(t) and _SES_KAYNAK.search(t)) >= 0.5 * n:
        return "kaynakça"
    if sum(1 for t in m if _SES_DIZIN.match(t)) >= 0.5 * n:
        return "dizin"
    return None


def ses_disi_bloklar(gor, ana_dil="tr"):
    """{blok kimliği: neden}: kitabın başlıklarıyla ayrılan bölümlerinden seslendirmeye gitmeyenler. Kısa bölüm (5 paragraftan az)
    iki yanı da gitmeyen bölümse o da gitmez (sonnotların arasındaki 'SONUÇ' alt başlığı)."""
    bolumler, cur = [], None
    for b in gor["bloklar"]:
        if b["tur"] == "baslik" or cur is None:
            cur = {"baslik": (b["metin"].get(ana_dil) or "") if b["tur"] == "baslik" else "", "bloklar": []}
            bolumler.append(cur)
        cur["bloklar"].append(b)
    nedenler = [_ses_disi_bolum(bo["baslik"], [b["metin"].get(ana_dil) for b in bo["bloklar"] if b["tur"] != "baslik"])
                for bo in bolumler]
    # Ana metin dışı bölgenin devamı (alt başlıklarıyla sürer):
    #  - sonnotlarda ("DİPNOTLAR") alt başlık kitabın önceki bir başlığının tekrarıdır ("BİRİNCİ MES'ELE": o bölümün notları) ya da
    #    paragraflarının en az %20'si not işaretiyle başlar;
    #  - dizin/kaynakçada alt başlıklı devam liste biçimindedir (kısa satırlar, çoğu "ad: sayfa": "Bağdat: xx, 218, 221").
    import difflib
    bolge = None   # ana metin dışı bölgenin başladığı bölüm sırası
    for i in range(len(bolumler)):
        if nedenler[i]:
            bolge = i if bolge is None else bolge
            continue
        if bolge is None:
            continue
        ps = [K.NOT_ISARETI.sub("", b["metin"].get(ana_dil) or "").strip() for b in bolumler[i]["bloklar"] if b["tur"] != "baslik"]
        ps = [t for t in ps if t]
        bas = _ses_sade(bolumler[i]["baslik"])
        onceki = [_ses_sade(bo["baslik"]) for bo in bolumler[:bolge] if bo["baslik"]]
        notlu = any(re.search(r"dipnot|notlar|son ?not|sonnot", _ses_sade(n)) for n in nedenler[bolge:i] if n)
        if notlu and bas and any(difflib.SequenceMatcher(None, bas, o).ratio() >= 0.85 for o in onceki):
            nedenler[i] = "sonnot (devam: " + bolumler[i]["baslik"].strip()[:30] + ")"
        elif notlu and ps and sum(1 for t in ps if _SES_NOT.match(t)) >= 0.2 * len(ps):
            nedenler[i] = "sonnot (devam)"
        elif ps and sum(len(t.split()) for t in ps) <= 15 * len(ps) and \
                sum(1 for t in ps if re.search(r":\s*(?:\d{1,4}|[ivxlc]{2,})\b", t, re.I)) >= 0.5 * len(ps):
            nedenler[i] = "liste (devam)"
        else:
            bolge = None
    for i in range(1, len(bolumler) - 1):
        if not nedenler[i] and nedenler[i - 1] and nedenler[i + 1] and len(bolumler[i]["bloklar"]) <= 6:
            nedenler[i] = "ara"
    return {b["id"]: n for bo, n in zip(bolumler, nedenler) if n for b in bo["bloklar"]}



def studyo_parcalari(kit):
    """Kitap -> Stüdyo parçaları: her bölüm bir Parca_ (seslendirmede bir ses parçası), dipnotlar sonda Dipnot_.
    Türkçe ve Osmanlıca satırlar birebir eşleşir (iki dilli çıktılar hizalı olsun). Dipnot işaretleri ve sayfa
    numaraları gitmez; bölüm, başlığıyla başlar ('Bölüm 001 (5-20)' etiketi seslendirmede okunmasın)."""
    gor = K.gorunur(kit)
    if "tr" not in K.diller(gor):
        raise ValueError("Kitabın Türkçesi yok: önce Türkçeye çevrilmeli")
    ana_dil = "tr"  # tur 2/A: Türkçe + Kütüphane'nin Osmanlıcası (Osmanlıcası olmayan satırın karşısı boş kalır)
    yapi = EPUB._Uretici(gor, [ana_dil]).yapi()
    bloklar = {b["id"]: b for b in gor["bloklar"]}
    parcalar, satirlar = [], []
    disi = ses_disi_bloklar(gor, ana_dil)   # 0.5.42: kaynakça, dizin, sonnotlar… seslendirmeye gitmez ("Ek_" parçası)
    for bolum in yapi:  # uzun bölüm, paragraf sınırından ~15.000 harflik parçalara (her parça bir ses dosyası)
        tr, osm, uz, ek = [], [], 0, False
        for bid in bolum["bloklar"]:
            t = _temiz(bloklar[bid]["metin"].get(ana_dil))
            if not t:
                continue
            t = K.ses_yok_isaretle(t, (bloklar[bid].get("ses_yok") or {}).get(ana_dil))   # 0.5.52: seslendirmede atlanır
            b_ek = bid in disi
            if tr and (uz + len(t) > PARCA_HARF or b_ek != ek):
                satirlar.append((tr, osm, ek))
                tr, osm, uz = [], [], 0
            ek = b_ek
            tr.append(t)
            osm.append(_temiz(bloklar[bid]["metin"].get("osm")))
            uz += len(t)
        if tr:
            satirlar.append((tr, osm, ek))
    sayac = {False: 0, True: 0}
    for tr, osm, ek in satirlar:
        sayac[ek] += 1
        parcalar.append({"name": f"{'Ek' if ek else 'Parca'}_{sayac[ek]:03d}", "tr": "\n".join(tr), "osm": "\n".join(osm)})
    # dipnotlar: EPUB'daki numaralarla (görünüş sırası)
    sira = []
    for b in gor["bloklar"]:
        for g in K.NOT_ISARETI.findall(b["metin"].get(ana_dil) or ""):
            if g not in sira:
                sira.append(g)
    if sira:
        tr = ["DİPNOTLAR"] + [f"{n}. {_temiz(gor['dipnotlar'][g]['metin'].get(ana_dil))}" for n, g in enumerate(sira, 1)]
        osm = [DIPNOT_OSM]
        for n, g in enumerate(sira, 1):
            o = _temiz(gor["dipnotlar"][g]["metin"].get("osm"))
            osm.append(f"{n}. {o}" if o else "")
        parcalar.append({"name": "Dipnot_001", "tr": "\n".join(tr), "osm": "\n".join(osm)})
    return parcalar


def studyoya_gonder(kit):
    """Tur 2/A: aynı süreçte (tek uygulama) Stüdyo işi açar; Osmanlıca hazır gider."""
    from app import main as studyo
    ku = kit["kunye"]
    baslik = ku["baslik"].get("tr") or ku["baslik"].get(ku.get("asil_dil", "tr")) or "Kitap"
    parcalar = studyo_parcalari(kit)
    try:   # tur 3: dosya adları bütün biçimlerde aynı ("Eser adı - Yazar"), EPUB'larla birlikte
        jid = studyo.kutuphane_isi(dosya_adi(kit), (ku["baslik"].get("osm") or "").strip(), parcalar)
    except ValueError as e:
        raise RuntimeError(f"Stüdyo kabul etmedi: {e}")
    return {"is": jid, "tarih": int(time.time()), "parca": len(parcalar)}


def studyoyu_guncelle(kit, jid):
    """Tur 2/C: kitabın mevcut Stüdyo işini yeni metinle yeniler (düzeltmeden sonra)."""
    from app import main as studyo
    parcalar = studyo_parcalari(kit)
    try:
        ok = studyo.kutuphane_guncelle(int(jid), (kit["kunye"]["baslik"].get("osm") or "").strip(), parcalar)
    except ValueError as e:
        raise RuntimeError(f"Stüdyo kabul etmedi: {e}")
    return {"is": int(jid), "tarih": int(time.time()), "parca": len(parcalar), "guncellendi": bool(ok)}


def studyo_isi_var(jid):
    """Bu numaralı Stüdyo işi hâlâ duruyor mu (Stüdyo'da silindiyse kitap yeniden gönderilebilir)."""
    from app import db as sdb
    try:
        return sdb.get(int(jid)) is not None
    except (TypeError, ValueError):
        return False
