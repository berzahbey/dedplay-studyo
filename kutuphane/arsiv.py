"""0.5.66: daha önce işlenmiş kitap uyarısı.

Kitap Stüdyo'dan silindikten sonra hangi kitabın verildiği bilinmiyordu. İki iz kullanılır:
  1) islenmis.json (DATA_DIR): işlenmiş bir kitap silinirken adı, yazarı, kaynak dosya adı ve tarihi burada kalır.
  2) dedplay klasöründeki çıktılar: EPUB (her dil klasörü) ve M4B. Bu sürümden önce silinmiş kitaplar da böyle bulunur.
Eşleşme adla yapılır (katalog.sade: büyük/küçük harf, şapka, Türkçe harf farkı yok sayılır)."""
import json
import os
import re
import threading
import time

from . import cikti, depo, kaynak
from .katalog import sade

DOSYA = os.path.join(depo.VERI, "islenmis.json")
M4B = os.path.join(os.environ.get("DEDPLAY_DIR", "/dedplay"), "M4B")
_kilit = threading.Lock()
_AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def _oku():
    try:
        with open(DOSYA, encoding="utf-8") as f:
            v = json.load(f)
        return v if isinstance(v, dict) else {}
    except (OSError, ValueError):
        return {}


def kaydet(kid, d, dosyalar_silindi=False):
    """Kitap silinirken çağrılır. Yalnız işlenmiş (EPUB'u ya da seslendirme işi olan) kitap kaydedilir."""
    if not d or not (d.get("epublar") or (d.get("studyo") or {}).get("is")):
        return False
    kay = d.get("kaynak_kimlik") or ""
    giris = {"baslik": d.get("baslik") or d.get("baslik_asil") or "", "yazar": d.get("yazar") or "",
             "kaynak_ad": os.path.basename(kay) if os.path.isabs(kay) else "",
             "eklendi": d.get("eklendi"), "silindi": int(time.time()),
             "seslendirme": bool((d.get("studyo") or {}).get("is")), "dosyalar_silindi": bool(dosyalar_silindi)}
    with _kilit:
        v = _oku()
        v[kid] = giris
        os.makedirs(os.path.dirname(DOSYA) or ".", exist_ok=True)
        with open(DOSYA + ".tmp", "w", encoding="utf-8") as f:
            json.dump(v, f, ensure_ascii=False, indent=1)
        os.replace(DOSYA + ".tmp", DOSYA)
    return True


def _gok(s):
    """Anlamlı ad mı (çok kısa adlar yanlış eşleşme verir)."""
    return len(re.sub(r"\s", "", s or "")) >= 3


def _adlar(gorunen_ad):
    """Dosya adından karşılaştırılacak sade adlar: tam ad ve başlık ("Yazar - Başlık" ya da "Başlık")."""
    kok = os.path.splitext(os.path.basename(gorunen_ad or ""))[0]
    baslik, _ = kaynak._dosya_adindan(gorunen_ad or "")
    return {s for s in (sade(kok), sade(baslik)) if _gok(s)}


def cikti_dizini():
    """dedplay klasöründeki EPUB ve M4B dosyaları: [(tür, göreli ad, {sade adlar})]. Çıktı adı "Başlık - Yazar"."""
    out = []

    def ekle(tur, rel, kok):
        adlar = {s for s in (sade(kok), sade(kok.split(" - ")[0])) if _gok(s)}
        if adlar:
            out.append((tur, rel, adlar))

    if os.path.isdir(cikti.CIKTI):
        for kl in sorted(os.listdir(cikti.CIKTI)):
            p = os.path.join(cikti.CIKTI, kl)
            if os.path.isdir(p) and not kl.startswith("."):
                for ad in sorted(os.listdir(p)):
                    if ad.lower().endswith(".epub"):
                        ekle("epub", f"{kl}/{ad}", ad[:-5])
    if os.path.isdir(M4B):
        for ad in sorted(os.listdir(M4B)):
            if ad.lower().endswith(".m4b"):
                ekle("ses", ad, re.sub(r" - \d+$", "", ad[:-4]))
    return out


def bul(gorunen_ad, dizin=None):
    """Silinmiş kitabın izi: {"kayit": {...} ya da None, "epub": [..], "ses": [..]} ya da None."""
    adlar = _adlar(gorunen_ad)
    if not adlar:
        return None
    kayit = None
    for kid, g in sorted(_oku().items(), key=lambda x: -(x[1].get("silindi") or 0)):
        if adlar & ({sade(g.get("baslik"))} | _adlar(g.get("kaynak_ad"))):
            kayit = dict(g, kimlik=kid)
            break
    if kayit and _gok(sade(kayit.get("baslik"))):
        adlar = adlar | {sade(kayit["baslik"])}
    epub, ses = [], []
    for tur, rel, c_adlar in (cikti_dizini() if dizin is None else dizin):
        if adlar & c_adlar:
            (epub if tur == "epub" else ses).append(rel)
    if not (kayit or epub or ses):
        return None
    return {"kayit": kayit, "epub": epub, "ses": ses}


def _tarih(t):
    lt = time.localtime(t)
    return f"{lt.tm_mday} {_AYLAR[lt.tm_mon - 1]} {lt.tm_year}"


def mesaj(ad, iz):
    """Onay penceresindeki metin."""
    k = iz.get("kayit") or {}
    ilk = (iz.get("ses") or iz.get("epub") or [""])[0]
    cikti_adi = re.sub(r" - \d+$", "", os.path.splitext(os.path.basename(ilk))[0]).split(" - ")[0]
    baslik = k.get("baslik") or cikti_adi or os.path.splitext(os.path.basename(ad))[0]
    satir = [f"“{baslik}” arşivde mevcut."]
    if k:
        ne = "işlenip seslendirmeye gönderilmişti" if k.get("seslendirme") else "işlenmişti"
        satir.append(f"Bu kitap daha önce {ne}; {_tarih(k['silindi'])} tarihinde Stüdyo'dan kaldırıldı"
                     + (" (dosyaları da silindi)." if k.get("dosyalar_silindi") else "."))
    if iz.get("ses"):
        satir.append(f"Sesli kitap: {', '.join(iz['ses'][:3])}" + (" …" if len(iz["ses"]) > 3 else ""))
    if iz.get("epub"):
        satir.append(f"EPUB: {', '.join(iz['epub'][:3])}" + (" …" if len(iz["epub"]) > 3 else ""))
    satir.append("Yeniden işlensin mi?")
    return "\n".join(satir)
