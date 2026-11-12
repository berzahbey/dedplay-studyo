"""0.5.71 (12 Kasım 2026, Zahir'in tasarımı): Osmanlıca çeviriden önce yapay zekâ köken adımı.
Çevirici (Osmanlıca uygulaması) metindeki, hiçbir sözlükte ve kayıtta bulunmayan kelimeleri verir (/api/bilinmeyen). Bunlar Gemini'ye
150'şerli gruplar hâlinde sorulur: kelimenin kökeni (tr / ar / fa / Batı dili), Arapça-Farsça ise kökün aslî yazılışı, Batı dili ise
okunuşu ve kısa Türkçe karşılığı. Cevaplar çeviriciye yazılır (/api/yz-kayit); çevirici denetler (harf uyumu), kalıcı kaydeder ve
sözlük gibi kullanır. Her kelime bir kez sorulur. Yapay zekâ Osmanlıca yazmaz: yazımı çeviricinin sözlük ve kuralları yapar.
Yapay zekâ kapalıysa, günlük sınır dolduysa ya da çevirici eski sürümse adım atlanır; çeviri her durumda sürer."""
import concurrent.futures
import logging
import threading

import requests

from . import yz

log = logging.getLogger("koken")
from .osmanlica import URL

GRUP = 40          # 0.5.72: 150 kelimelik cevap çok uzun sürüyordu (zaman aşımı); 40'lık gruplar, 3'ü aynı anda
ES_ZAMANLI = 3

SISTEM = """Sen Türkçe metinlerdeki kelimelerin kökenini belirleyen bir dil uzmanısın. Sana Türkçe bir kitaptan kelimeler verilecek;
kelimelere Türkçe ekler gelmiş olabilir. Her kelime için kökünün dilini ve gerekli bilgiyi ver. Yalnız JSON dizisi döndür:
[{"no": 1, "koken": "...", "kok": "...", "yazilis": "...", "okunus": "...", "anlam": "..."}, ...]
Kurallar:
- koken: kelimenin KÖKÜNÜN dili: tr (Türkçe), ar (Arapça), fa (Farsça), en, fr, de, la (Latince), it, el (Yunanca), ru, es ...
  Emin değilsen "?" yaz.
- kok: eksiz kök, Latin harfle (mahmuzuyla -> mahmuz, kahramanları -> kahraman, Robespierre'in -> Robespierre).
- ar ve fa: "yazilis" kökün Osmanlıca (Arap harfli, harekesiz) aslî yazılışı: mahmuz -> مهمیز, kahraman -> قهرمان, dert -> درد.
  Eksiz kökü yaz, Türkçe eki yazma.
- tr: yazilis ve okunus boş kalır. Batı dilinden gelip Türkçeleşmiş kelime (kültür, sosyal, demokrasi, piskopos) tr DEĞİLDİR:
  aslının dilini yaz.
- Batı dilleri ve öteki diller: "okunus" kelimenin (eksiz kökün) aslındaki okunuşunun Türkçe harflerle yazımı:
  Charakter -> Karakter, Robespierre -> Robespiyer, Cambridge -> Keymbriç, caritas -> karitas, kültür -> kültür.
- Kişi ve yer adları da aynı kurala göre: Türk adı tr; Arap/Fars adı ar/fa + yazılış; Batılı ad dil + okunuş.
- anlam: kısa Türkçe karşılık (en çok 5 kelime); özel adda "kişi adı" / "yer adı".
- Her kelime için bir nesne ver; "no" verilen numara olsun."""


def _bilinmeyenler(metin):
    try:
        r = requests.post(f"{URL}/api/bilinmeyen", data={"text": metin}, timeout=300)
    except requests.RequestException:
        return None
    if r.status_code == 404:
        return None              # çevirici eski sürüm (Tur YZ1 öncesi): adım atlanır
    r.raise_for_status()
    return r.json().get("kelimeler") or []


def _kaydet(kayitlar):
    r = requests.post(f"{URL}/api/yz-kayit", json={"kayitlar": kayitlar}, timeout=120)
    r.raise_for_status()
    return r.json()


def cevaplari_coz(kelimeler, cevap, model=""):
    """Gemini cevabını (JSON dizisi) çeviricinin kayıt biçimine çevirir; numarası tutmayan / boş olanlar atlanır."""
    out = []
    for d in (yz.json_al(cevap) or []):
        if not isinstance(d, dict):
            continue
        try:
            no = int(d.get("no"))
        except (TypeError, ValueError):
            continue
        if not 1 <= no <= len(kelimeler):
            continue
        koken = str(d.get("koken") or "").strip().lower()
        if not koken or koken == "?":
            continue
        out.append({"kelime": kelimeler[no - 1], "koken": koken, "kok": d.get("kok") or "", "yazilis": d.get("yazilis") or "",
                    "okunus": d.get("okunus") or "", "anlam": d.get("anlam") or "", "model": model})
    return out


def kokenleri_sor(metinler, ilerleme=None):
    """Çeviriden önce: bilinmeyen kelimeleri yapay zekâya sorar ve çeviriciye kaydeder. Dönen: özet sözlüğü.
    0.5.72: 40'lık gruplar, aynı anda 3 istek (dakika sınırı yz modülünde ortak sayılır); grup cevapsız kalırsa atlanır
    (o kelimeler sonraki çeviride yeniden sorulur); her grup günlüğe yazılır."""
    ilerleme = ilerleme or (lambda m: None)
    ozet = {"bilinmeyen": 0, "soruldu": 0, "onayli": 0, "kontrol": 0, "durum": "atlandi"}
    if not yz.acik():
        return ozet
    kelimeler = _bilinmeyenler("\n".join(m for m in metinler if m))
    if kelimeler is None:
        return ozet
    ozet["bilinmeyen"] = len(kelimeler)
    log.warning("köken: %d bilinmeyen kelime", len(kelimeler))
    if not kelimeler:
        ozet["durum"] = "tamam"
        return ozet
    gruplar = [kelimeler[i:i + GRUP] for i in range(0, len(kelimeler), GRUP)]
    kilit, dur = threading.Lock(), threading.Event()

    def sor(grup):
        if dur.is_set():
            return
        g = yz.Gemini(lambda m: None)
        g.zaman, g.deneme = 120, 3
        kullanici = "KÖKEN GÖREVİ\n" + "\n".join(f"{n}. {w}" for n, w in enumerate(grup, 1))
        try:
            cevap, model = g.sor(SISTEM, kullanici, en_fazla=2500)
        except yz.GunlukSinir:
            dur.set()
            with kilit:
                ozet["durum"] = "gunluk_sinir"
            return
        except Exception as e:      # noqa: BLE001  geçici hata: bu grup sonraki çeviride yeniden sorulur
            log.warning("köken: grup cevapsız (%s)", type(e).__name__)
            return
        kayitlar = cevaplari_coz(grup, cevap, model)
        s = _kaydet(kayitlar) if kayitlar else {}
        with kilit:
            ozet["soruldu"] += len(grup)
            ozet["onayli"] += s.get("onayli", 0)
            ozet["kontrol"] += s.get("kontrol", 0)
            log.warning("köken: %d/%d soruldu (grup %d kelime, %d cevap, model %s)", ozet["soruldu"], len(kelimeler),
                        len(grup), len(kayitlar), model)
            ilerleme(f"Kelime kökenleri soruluyor: {ozet['soruldu']}/{len(kelimeler)}")

    ilerleme(f"Kelime kökenleri soruluyor: 0/{len(kelimeler)}")
    with concurrent.futures.ThreadPoolExecutor(ES_ZAMANLI) as ex:
        list(ex.map(sor, gruplar))
    if ozet["durum"] != "gunluk_sinir":
        ozet["durum"] = "tamam"
    else:
        ilerleme("Yapay zekâ günlük sınırı doldu; kalan kelimeler sonraki çeviride sorulacak")
    return ozet
