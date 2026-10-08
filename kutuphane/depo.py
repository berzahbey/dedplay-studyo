"""Kitapların diskteki düzeni ve arka plan işleri.

/data/kitaplar/<kimlik>/kitap.json   tek kaynak
/data/kitaplar/<kimlik>/durum.json   iş durumu, EPUB listesi, denetim sonuçları
/data/kitaplar/<kimlik>/kaynak.txt   indirilen asıl metin (yeniden okumak için)
/data/kitaplar/<kimlik>/epub/*.epub
"""
import json
import os
import queue
import re
import shutil
import threading
import time
import traceback
import unicodedata

import requests

from . import epub as EPUB
from . import cikti, epubcheck, kaynak, katalog, openiti, osmanlica
from . import kitap as K

VERI = os.environ.get("DATA_DIR", "/data")
KITAPLAR = os.path.join(VERI, "kitaplar")
KIMLIK = re.compile(r"^[A-Za-z0-9._-]{1,120}$")
DIL_AD = {"ar": "arapca", "en": "ingilizce", "fr": "fransizca", "fa": "farsca"}
_kuyruk = queue.Queue()  # hafif şerit (0.5.17): EPUB/DOCX/TXT, katmanlı ya da önbellekteki PDF, Osmanlıca, EPUB işleri
_kuyruk_agir = queue.Queue()  # ağır şerit: OCR gerektiren PDF'ler, birer birer (Surya bütün işlemciyi kullanır)
_is_kilitleri = {}  # aynı kitabın iki işi aynı anda çalışmasın
_kilit = threading.Lock()
_kitap_kilitleri = {}
_bekleyen_epub = set()  # kuyrukta bekleyen EPUB işleri: art arda düzeltmelerde tek iş
# 0.5.19: kuyruktaki kitap silinebilir. Her kitabın bir "nesli" var; silinince artar ve kuyrukta kalan eski işleri
# geçersiz olur (aynı kitap yeniden eklenirse yeni nesille çalışır). İşi çalışan kitap "silinecek" diye işaretlenir:
# iş bir sonraki ilerleme bildiriminde durur, sonra kitap silinir.
_nesil = {}
_calisan = {}       # şerit adı -> kitap kimliği
_silinecek = set()


class IsIptal(Exception):
    pass


def kitap_kilidi(kid):
    """kitap.json'u yazan her iş (arka plan ya da okuma ekranı) bu kilidi tutar: düzeltmeler kaybolmaz."""
    with _kilit:
        return _kitap_kilitleri.setdefault(kid, threading.Lock())


def klasor(kid):
    if not KIMLIK.match(kid or ""):
        raise ValueError("geçersiz kitap kimliği")
    return os.path.join(KITAPLAR, kid)


def durum_oku(kid):
    yol = os.path.join(klasor(kid), "durum.json")
    try:
        return json.load(open(yol, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def durum_yaz(kid, **kw):
    with _kilit:
        d = durum_oku(kid)
        d.update(kw)
        d["guncellendi"] = int(time.time())
        yol = os.path.join(klasor(kid), "durum.json")
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol + ".tmp", "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(yol + ".tmp", yol)
        return d


def liste():
    if not os.path.isdir(KITAPLAR):
        return []
    out = []
    for kid in sorted(os.listdir(KITAPLAR)):
        if not KIMLIK.match(kid) or not os.path.isdir(os.path.join(KITAPLAR, kid)):
            continue
        d = durum_oku(kid)
        out.append({"kimlik": kid, **{k: d.get(k) for k in ("baslik", "baslik_asil", "yazar", "asama", "hata", "uyari", "guncellendi",
                                                            "cikti", "cikti_uyari", "studyo", "studyo_uyari",
                                                            "eklendi", "epublar")}})
    return sorted(out, key=lambda x: -(x.get("eklendi") or 0))


def kitap_yolu(kid):
    return os.path.join(klasor(kid), "kitap.json")


def surumler(kit):
    """Kitaptaki dillere göre üretilecek EPUB sürümleri (dosya eki, diller)."""
    d = K.diller(kit)
    asil = kit["kunye"].get("asil_dil", "ar")
    out = []
    if "tr" in d:
        out.append(("turkce", ["tr"]))
    if "osm" in d:
        out.append(("osmanlica", ["osm"]))
    if "tr" in d and "osm" in d:
        out.append(("turkce-osmanlica", ["tr", "osm"]))
    if asil not in ("tr", "osm"):  # yabancı asıl (Arapça, İngilizce…): asıllı sürümler
        ad = DIL_AD.get(asil, asil)
        if asil in d and "tr" in d:
            out.append((f"{ad}-turkce", [asil, "tr"]))
        if asil in d:
            out.append((ad, [asil]))
    return out


def _dosya_adi(kid, kit):
    """Sade harfli dosya adı (şapka/Türkçe harf yok): her cihazda ve ağ paylaşımında sorunsuz."""
    b = kit["kunye"]["baslik"].get("tr") or (kid.split(".")[1] if "." in kid else kid)
    b = b.translate(str.maketrans("İıŞşĞğÇçÖöÜü", "IiSsGgCcOoUu"))
    b = "".join(c for c in unicodedata.normalize("NFKD", b) if not unicodedata.combining(c))
    b = re.sub(r"[^A-Za-z0-9\s-]", "", b).strip()
    return re.sub(r"\s+", "_", b)[:60] or "kitap"


def epub_uret(kid):
    """kitap.json'dan bütün sürümleri üretir ve denetler. Eski EPUB'lar silinir, yenileri yazılır."""
    kit = K.yukle(kitap_yolu(kid))
    sorunlar = K.denetle(kit)
    if sorunlar:
        raise ValueError("kitap.json yapısal hata: " + "; ".join(sorunlar[:5]))
    ek = os.path.join(klasor(kid), "epub")
    gecici = ek + ".yeni"
    shutil.rmtree(gecici, ignore_errors=True)
    os.makedirs(gecici)
    ad = _dosya_adi(kid, kit)
    sonuc = []
    for ekad, diller in surumler(kit):
        dosya = f"{ad}_{ekad}.epub"
        durum_yaz(kid, asama=f"EPUB üretiliyor: {ekad}")
        kapak = None  # kitabın kendi kapak görseli (PDF'in ilk sayfası / EPUB'un kapağı) varsa o
        if kit["kunye"].get("kapak") and os.path.exists(os.path.join(klasor(kid), kit["kunye"]["kapak"])):
            kapak = open(os.path.join(klasor(kid), kit["kunye"]["kapak"]), "rb").read()
        EPUB.uret(kit, diller, os.path.join(gecici, dosya), kapak_png=kapak)
        durum_yaz(kid, asama=f"Denetleniyor: {ekad}")
        dn = epubcheck.denetle(os.path.join(gecici, dosya))
        sonuc.append({"dosya": dosya, "diller": diller, "boyut": os.path.getsize(os.path.join(gecici, dosya)),
                      "denetim": dn})
    shutil.rmtree(ek, ignore_errors=True)  # hepsi başarıyla üretildikten sonra eskiler kalkar
    os.replace(gecici, ek)
    try:  # dil klasörlerine (Türkçe/, Osmanlıca/, Türkçe-Osmanlıca/ ...)
        yazilan = cikti.ciktiya_yaz(kit, sonuc, ek, durum_oku(kid).get("cikti"))
        durum_yaz(kid, cikti=yazilan, cikti_uyari=None if yazilan is not None else "Çıktı klasörü bağlı değil")
    except Exception as e:
        durum_yaz(kid, cikti_uyari=f"Çıktı klasörüne yazılamadı: {type(e).__name__}: {str(e)[:120]}")
    ku = kit["kunye"]
    durum_yaz(kid, epublar=sonuc, asama="hazır", hata=None,
              baslik=ku["baslik"].get("tr") or ku["baslik"].get(ku.get("asil_dil", "ar")),
              baslik_asil=ku["baslik"].get(ku.get("asil_dil", "ar")),
              yazar=ku["yazar"].get("tr") or ku["yazar"].get(ku.get("asil_dil", "ar")) or ku["yazar"].get("lat"))
    return sonuc


def _openiti_ekle(kid, version_uri):
    satir = katalog.bul(VERI, version_uri)
    if not satir:
        raise ValueError("katalogda bulunamadı: " + version_uri)
    yol = os.path.join(klasor(kid), "kaynak.txt")
    if not os.path.exists(yol):
        durum_yaz(kid, asama="Metin indiriliyor")
        r = requests.get(satir["url"], timeout=300)
        r.raise_for_status()
        r.encoding = "utf-8"
        with open(yol + ".tmp", "w", encoding="utf-8") as f:
            f.write(r.text)
        os.replace(yol + ".tmp", yol)
    durum_yaz(kid, asama="Bölümler ve sayfalar ayrılıyor")
    kit = openiti.cevir(open(yol, encoding="utf-8").read(), satir)
    eski = kitap_yolu(kid)
    if os.path.exists(eski):  # yeniden ekleme: elle yapılan düzeltmeler ve Türkçe künye korunur
        onceki = K.yukle(eski)
        kit["kunye"]["baslik"].update({k: v for k, v in onceki["kunye"]["baslik"].items() if k != "ar"})
        kit["kunye"]["yazar"].update({k: v for k, v in onceki["kunye"]["yazar"].items() if k not in ("ar", "lat")})
    K.kaydet(kit, eski)


def _dosya_ekle(kid, yol):
    """Elindeki kitap (PDF/EPUB/DOCX/TXT) -> kitap.json (Türkçe) -> Osmanlıca -> EPUB'lar."""
    if not os.path.exists(yol):
        raise FileNotFoundError("Kaynak dosya bulunamadı: " + yol)
    kit = kaynak.cevir(yol, lambda m: durum_asama(kid, m), {"yol": yol}, kapak_yolu=os.path.join(klasor(kid), "kapak"))
    try:  # 0.5.23: kitap raporu (rapor.json, rapor.txt); hata kitabı durdurmaz
        from . import rapor
        rapor.kaydet(klasor(kid), rapor.al())
    except Exception:
        pass
    eski = kitap_yolu(kid)
    if os.path.exists(eski):  # yeniden işleme: önceki hâl yedeklenir, Türkçe künye düzeltmeleri korunur
        onceki = K.yukle(eski)
        shutil.copy2(eski, eski + ".yedek")
        for alan in ("baslik", "yazar"):
            if onceki["kunye"].get(alan, {}).get("elle"):
                kit["kunye"][alan] = onceki["kunye"][alan]
    K.kaydet(kit, eski)  # Osmanlıca sonra, ayrı iş (önce kitabın kendi dilindeki EPUB'u hazır olur)


def _osmanlica(kid, zorla=False):
    kit = K.yukle(kitap_yolu(kid))
    durum_asama(kid, "Osmanlıcaya çevriliyor")
    try:
        osmanlica.kitabi_cevir(kit, lambda m: durum_asama(kid, m), zorla=zorla)
        K.kaydet(kit, kitap_yolu(kid))
        durum_yaz(kid, uyari=None)
    except Exception as e:  # çevirici kapalıysa Türkçe EPUB yine üretilir
        durum_yaz(kid, uyari=f"Osmanlıca çevrilemedi ({type(e).__name__}: {str(e)[:120]}); sadece Türkçe üretildi")


def _studyoya_zincirle(kid, guncelle=False, yalniz_var_olan=False):
    """Tur 2/A: Osmanlıca ve EPUB'lar bitince Türkçe kitap kendiliğinden Stüdyo'ya gider (seslendirme ve öteki biçimler).
    Kitabın Stüdyo işi zaten varsa yeni iş açılmaz (düzeltmeden sonra yenileme tur 2/C). Osmanlıca çevrilemediyse
    gönderilmez: Stüdyo Osmanlıcayı ikinci kez çevirmesin; 'Osmanlıcayı yeniden çevir' başarılı olunca gider."""
    kit = K.yukle(kitap_yolu(kid))
    if kit["kunye"].get("asil_dil") != "tr" or "tr" not in K.diller(kit):
        return
    d = durum_oku(kid)
    if d.get("uyari"):
        durum_yaz(kid, studyo_uyari="Osmanlıca çevrilemediği için seslendirmeye gönderilmedi; "
                                    "'Osmanlıcayı yeniden çevir' başarılı olunca kendiliğinden gider.")
        return
    eski = (d.get("studyo") or {}).get("is")
    if eski and cikti.studyo_isi_var(eski):
        if guncelle:   # tur 2/C: var olan iş yeni metinle yenilenir (yalnız değişen bölümlerin sesi yeniden üretilir)
            try:
                durum_yaz(kid, studyo=cikti.studyoyu_guncelle(kit, eski), studyo_uyari=None)
            except Exception as e:
                traceback.print_exc()
                durum_yaz(kid, studyo_uyari=f"Seslendirme yenilenemedi: {type(e).__name__}: {str(e)[:150]}")
        return
    if yalniz_var_olan:
        return
    try:
        durum_yaz(kid, studyo=cikti.studyoya_gonder(kit), studyo_uyari=None)
    except Exception as e:
        traceback.print_exc()
        durum_yaz(kid, studyo_uyari=f"Seslendirmeye gönderilemedi: {type(e).__name__}: {str(e)[:150]}")


def durum_asama(kid, mesaj):
    if kid in _silinecek:  # 0.5.19: kitap silinmek istendi: iş burada durur (OCR'da en geç 4 sayfada bir)
        raise IsIptal("Kitap silinmek üzere: iş durduruldu")
    durum_yaz(kid, asama=mesaj)


def _is_kilidi(kid):
    with _kilit:
        return _is_kilitleri.setdefault(kid, threading.Lock())


_kuyruk_osm = type(_kuyruk)()  # 0.5.25: Osmanlıca ayrı şerit (inceleme sırasını beklemez)


def isci(agir=False):
    """0.5.17: iki şerit. Hafif şerit, OCR gerektiren dosya işini ağır şeride devreder. Aynı kitabın iki işi aynı anda
    çalışmaz: kitabın işi ağır şeritte sürerken gelen hafif iş ağır şeridin arkasına geçer."""
    kuyruk = _kuyruk_osm if agir == "osm" else (_kuyruk_agir if agir else _kuyruk)
    serit = "osm" if agir == "osm" else ("agir" if agir else "hafif")
    if agir == "osm":
        agir = False  # hafif şerit gibi: kitabın başka işi sürüyorsa ağır şeridin arkasına geçer
    while True:
        tur, kid, arg, nesil = kuyruk.get()
        with _kilit:  # 0.5.19: silinen kitabın kuyrukta kalan işi atlanır
            gecerli = nesil == _nesil.get(kid, 0)
            if gecerli:
                _calisan[serit] = kid
        if not gecerli:
            kuyruk.task_done()
            continue
        try:
            if not agir and tur == "dosya":
                durum_asama(kid, "Dosya inceleniyor")
                if kaynak.ocr_gerekir(arg):
                    durum_yaz(kid, asama="OCR sırasında")
                    _kuyruk_agir.put((tur, kid, arg, nesil))
                    continue
            kilit = _is_kilidi(kid)
            if not agir and not kilit.acquire(blocking=False):
                # bu kitabın işi ağır şeritte sürüyor (hafif şerit tek iş parçacığı): iş ağır şeridin arkasına geçer,
                # hafif şerit beklemez ve dönüp durmaz
                _kuyruk_agir.put((tur, kid, arg, nesil))
                continue
            if agir:
                kilit.acquire()  # hafif şeritteki kısa iş bitene kadar bekler
            try:
                _isle(tur, kid, arg)
            finally:
                kilit.release()
        except IsIptal:
            pass
        except Exception:
            traceback.print_exc()
        finally:
            with _kilit:
                _calisan.pop(serit, None)
                sonra_sil = kid in _silinecek and kid not in _calisan.values()
                if sonra_sil:
                    _silinecek.discard(kid)
            if sonra_sil:
                sil(kid)
            kuyruk.task_done()


def _isle(tur, kid, arg):
    if True:
        with _kilit:
            _bekleyen_epub.discard(kid)
        try:
            if tur in ("openiti", "dosya", "osmanlica", "kunye"):
                with kitap_kilidi(kid):  # bu sırada okuma ekranından düzeltme yapılamaz
                    if tur == "openiti":
                        _openiti_ekle(kid, arg)
                    elif tur == "dosya":
                        _dosya_ekle(kid, arg)
                    elif tur == "osmanlica":
                        _osmanlica(kid, zorla=bool(arg))
                    elif tur == "kunye":
                        kit = K.yukle(kitap_yolu(kid))
                        try:
                            osmanlica.kunye_cevir(kit)
                            K.kaydet(kit, kitap_yolu(kid))
                        except Exception as e:
                            durum_yaz(kid, uyari=f"Künyenin Osmanlıcası çevrilemedi: {type(e).__name__}")
            if kid in _silinecek:  # 0.5.19: kitap silinecek: EPUB, Stüdyo ve Osmanlıca zinciri yok
                return
            epub_uret(kid)
            if tur == "osmanlica":  # tur 2/A: Osmanlıca ve EPUB'lar hazır -> kendiliğinden Stüdyo
                _studyoya_zincirle(kid, guncelle=True)
            elif tur in ("epub", "kunye"):  # tur 2/C: okuma ekranında düzeltme -> Stüdyo işi (ses ve biçimler) yenilenir
                _studyoya_zincirle(kid, guncelle=True, yalniz_var_olan=True)
            # 1. aşama bitti: kitap kendi dilinde Kütüphane'de. 2. aşama: Türkçeyse Osmanlıca (çeviri yok; OpenITI yalnız Arapça EPUB)
            if tur == "dosya":
                kit = K.yukle(kitap_yolu(kid))
                if kit["kunye"].get("asil_dil") == "tr":
                    is_ekle("osmanlica", kid, tur="epub")
        except IsIptal:
            return
        except Exception as e:
            if kid in _silinecek:
                return
            traceback.print_exc()
            durum_yaz(kid, asama="hata", hata=f"{type(e).__name__}: {e}")


def is_ekle(is_turu, kid, arg=None, **durum):
    with _kilit:
        if is_turu == "epub" and kid in _bekleyen_epub:
            return  # zaten kuyrukta: tek sefer üretilir
        if is_turu == "epub":
            _bekleyen_epub.add(kid)
    # 0.5.17: yazı işi söyler (Türkçe EPUB hazırken "sırada" yanıltıcıydı); işin türü yeniden başlatma için saklanır
    yazi = {"osmanlica": "Osmanlıca sırada", "epub": "EPUB sırada", "kunye": "EPUB sırada"}.get(is_turu, "sırada")
    durum_yaz(kid, asama=yazi, hata=None, is_turu=is_turu, is_arg=arg, **durum)
    (_kuyruk_osm if is_turu == "osmanlica" else _kuyruk).put((is_turu, kid, arg, _nesil.get(kid, 0)))


def baslat():
    threading.Thread(target=isci, daemon=True, name="kutuphane-hafif").start()
    threading.Thread(target=isci, args=(True,), daemon=True, name="kutuphane-agir").start()
    threading.Thread(target=isci, args=("osm",), daemon=True, name="kutuphane-osmanlica").start()
    # 0.5.8: çeviri kaldırıldı; çeviri izleyicisi başlatılmaz
    # yeniden başlatmada yarım kalan işler kuyruğa geri alınır
    for k in liste():
        if durum_oku(k["kimlik"]).get("silinecek"):  # 0.5.19: silinmek istenirken yeniden başlatıldı
            sil(k["kimlik"])
            continue
        if k.get("asama") not in (None, "hazır", "hata"):
            d = durum_oku(k["kimlik"])
            if d.get("is_turu"):  # 0.5.17: yarım kalan işin kendisi (Osmanlıca işi "epub" diye geri alınıyordu)
                is_ekle(d["is_turu"], k["kimlik"], d.get("is_arg"))
            else:
                is_ekle(d.get("tur", "epub"), k["kimlik"], d.get("kaynak_kimlik"))


def sil(kid):
    shutil.rmtree(klasor(kid), ignore_errors=True)


def sil_iste(kid):
    """0.5.19: kitabı sil. Sırada bekliyorsa (ya da hazır/hata) hemen silinir: kuyruktaki işleri atlanır.
    İşi şu an çalışıyorsa iş durdurulur ve kitap ardından silinir. Dönen: \"silindi\" ya da \"durduruluyor\"."""
    with _kilit:
        _nesil[kid] = _nesil.get(kid, 0) + 1
        _bekleyen_epub.discard(kid)
        calisiyor = kid in _calisan.values()
        if calisiyor:
            _silinecek.add(kid)
    if calisiyor:
        durum_yaz(kid, silinecek=True)
        return "durduruluyor"
    sil(kid)
    return "silindi"
