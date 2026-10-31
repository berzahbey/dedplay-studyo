"""0.5.53: yapay zekâ denetimi Stüdyo'da (kutuphane/denetim.py + yz.py, Hazırlık 0.5.3 kurallarıyla).
(1) denetim akışı (sahte modelle): kaynak parantezi ve resim yazısı okunmaz (blokta ses_yok, metin aynen), OCR kelimesi düzelir,
    seste yoktur; yeniden denetimde işaret yinelenmez, model yeniden sorulmaz; (2) Gemini model zinciri (sahte Gemini sunucusu):
    anahtar başlıkta gider, günlük sınırı dolan model atlanır, hepsi dolunca GunlukSinir; (3) seslendirme bekletme ayarı.
  python tests/test_0553.py   (DATA_DIR geçici klasöre çevrilir)"""
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

KOK = tempfile.mkdtemp(prefix="t0553-")
os.environ["DATA_DIR"] = KOK
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

hata = 0


def kontrol(ad, kosul):
    global hata
    print(("TAMAM " if kosul else "HATA  ") + ad)
    hata += not kosul


# ---------------------------------------------------------------- (2) sahte Gemini sunucusu
DURUM = {"istek": [], "adreste_anahtar": 0, "dolu": {"gemini-9.5-flash-lite"}}
ANAHTAR = "AIzaSahteAnahtar0123456789abcdefghij"


class Sahte(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _yaz(self, kod, veri):
        b = json.dumps(veri).encode()
        self.send_response(kod)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        DURUM["adreste_anahtar"] += ANAHTAR in self.path
        if self.headers.get("x-goog-api-key") != ANAHTAR:
            return self._yaz(400, {"error": {"message": "API key not valid"}})
        self._yaz(200, {"models": [{"name": f"models/{m}", "supportedGenerationMethods": ["generateContent"]}
                                   for m in ("gemini-9.1-flash-lite", "gemini-9.5-flash-lite", "gemini-9.5-flash",
                                             "gemini-9.5-flash-lite-preview")]})

    def do_POST(self):
        DURUM["adreste_anahtar"] += ANAHTAR in self.path
        model = self.path.split("/models/")[1].split(":")[0]
        DURUM["istek"].append(model)
        uz = int(self.headers.get("Content-Length") or 0)
        govde = json.loads(self.rfile.read(uz))
        if model in DURUM["dolu"]:
            return self._yaz(429, {"error": {"code": 429, "details": [{"@type": "type.googleapis.com/google.rpc.QuotaFailure",
                                                                       "violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}})
        from kutuphane import yz
        metin = yz.sahte_cevap(govde["contents"][0]["parts"][0]["text"])
        self._yaz(200, {"candidates": [{"content": {"parts": [{"text": metin}]}}], "usageMetadata": {"promptTokenCount": 10}})


sunucu = HTTPServer(("127.0.0.1", 0), Sahte)
threading.Thread(target=sunucu.serve_forever, daemon=True).start()
os.environ["STUDYO_GEMINI_URL"] = f"http://127.0.0.1:{sunucu.server_port}/v1beta"

from kutuphane import cikti, depo, yz  # noqa: E402
from kutuphane import denetim as D  # noqa: E402
from kutuphane import kitap as K  # noqa: E402
from app.ses import ses_metni  # noqa: E402

kontrol("anahtarsız: denetim kapalı", not yz.acik())
yz.ayar_yaz(anahtar=ANAHTAR)
kontrol("anahtar kayıtlı: denetim açık, seslendirme kendiliğinden kapalı", yz.acik() and not yz.ozet()["seslendirme_otomatik"])
kontrol("sayfaya anahtarın yalnız son 4 hanesi", ANAHTAR not in json.dumps(yz.ozet()) and yz.ozet()["anahtar_son"] == ANAHTAR[-4:])
kontrol("yalnız kararlı Flash-Lite modelleri, yeniden eskiye", yz.modeller() == ["gemini-9.5-flash-lite", "gemini-9.1-flash-lite"])
g = yz.Gemini()
cevap, veren = g.sor("sistem", "SAYI GÖREVİ.\n1. «12» deneme")
kontrol("günlük sınırı dolu model atlanır, sıradaki cevap verir", veren == "gemini-9.1-flash-lite" and "dipnot_isareti" in cevap)
kontrol("dolan model sayaçta", "gemini-9.5-flash-lite" in yz.ozet()["tukenen"])
kontrol("anahtar adreste değil", DURUM["adreste_anahtar"] == 0)
DURUM["dolu"].add("gemini-9.1-flash-lite")
try:
    yz.Gemini().sor("sistem", "SAYI GÖREVİ.\n1. «12» deneme")
    kontrol("hepsi dolunca GunlukSinir", False)
except yz.GunlukSinir:
    kontrol("hepsi dolunca GunlukSinir", True)
DURUM["dolu"].clear()
os.remove(yz.SAYAC)

# ---------------------------------------------------------------- (1) denetim akışı (sahte Gemini sunucusu üzerinden)
kid = "Deneme-Kitap-d0553"
txt = os.path.join(KOK, "Deneme Kitap.txt")
open(txt, "w", encoding="utf-8").write(
    "BİRİNCİ BÖLÜM\n\nKimine göre Şeyh, İranlı bir Şiî'dir (B. Lewis, The Middle East and the West), kimine göre değil. "
    "Uyku hâli (uyku ile uyanıklık arası) diye anlatılır. Bu kitapx çok güzeldir. Bu kitap okunur.\n\n"
    "Ekaita hunajavirtoja jotka siellä asuvat saavat Herralta kaikenlaisia hedelmiä anteeksiannon ovatko niinkuin joilla.\n\n"
    "Kalbimizdeki sevgi uzun bir hikâyedir ve bunu herkes bilir, kitap da bunu anlatır.")
depo.durum_yaz(kid, kaynak_kimlik=txt, baslik="Deneme Kitap")
depo._dosya_ekle(kid, txt)
once = K.yukle(depo.kitap_yolu(kid))
istek_once = len(DURUM["istek"])
sonra = depo._denetim(kid)
kontrol("denetimden sonra Osmanlıca sırası", sonra == ("osmanlica", kid))
kit = K.yukle(depo.kitap_yolu(kid))
metin = " ".join(b["metin"]["tr"] for b in kit["bloklar"])
sy = [x["metin"] for b in kit["bloklar"] for x in (b.get("ses_yok") or {}).get("tr", [])]
kontrol("kaynak parantezi okunmaz (ses_yok), metinde aynen", "(B. Lewis, The Middle East and the West)" in sy
        and "(B. Lewis, The Middle East and the West)" in metin)
kontrol("açıklama parantezi okunur", not any("uyku ile" in x for x in sy))
kontrol("resim/kupür yazısı (Fince) okunmaz", any(x.startswith("Ekaita hunajavirtoja") for x in sy))
kontrol("Türkçe paragraf okunur", not any(x.startswith("Kalbimizdeki") for x in sy))
kontrol("OCR kelimesi düzeldi (kitapx -> kitap)", "Bu kitap çok güzeldir" in metin and "kitapx" not in metin)
kontrol("metinde işaret karakteri yok", K.SES_AC not in metin and K.SES_KAPA not in metin)
kontrol("denetimsiz kopya saklandı", os.path.exists(os.path.join(depo.klasor(kid), "kitap.denetimsiz.json")))
d = depo.durum_oku(kid)["denetim"]
kontrol("durumda özet ve rapor", d["durum"] == "hazir" and d["okunmaz"] == len(sy) and
        os.path.exists(os.path.join(depo.klasor(kid), "denetim.txt")))
kararlar = json.load(open(os.path.join(depo.klasor(kid), "denetim_kararlar.json"), encoding="utf-8"))
kontrol("cevaplar model adıyla saklandı", all(v.get("_m") == "gemini-9.5-flash-lite" for v in kararlar.values()))
parca = "\n".join(p["tr"] for p in cikti.studyo_parcalari(kit) if p["name"].startswith("Parca_"))
ses = "\n".join(ses_metni(x) for x in parca.split("\n"))
kontrol("seste kaynak ve Fince yok, ana metin var", "Lewis" not in ses and "hunajavirtoja" not in ses and "Kalbimizdeki" in ses)
istek = len(DURUM["istek"])
kontrol("denetim Gemini'ye gitti", istek > istek_once)
depo._denetim(kid)
kit2 = K.yukle(depo.kitap_yolu(kid))
sy2 = [x["metin"] for b in kit2["bloklar"] for x in (b.get("ses_yok") or {}).get("tr", [])]
kontrol("yeniden denetim: işaret yinelenmez, sonuç aynı", sy2 == sy and kit2["bloklar"] == kit["bloklar"])
kontrol("yeniden denetim: model yeniden sorulmaz", len(DURUM["istek"]) == istek)
depo._dosya_ekle(kid, txt)
kontrol("yeniden işleme denetimsiz kopyayı yeniler", not os.path.exists(os.path.join(depo.klasor(kid), "kitap.denetimsiz.json")))

# Hazırlık'ın işaretli EPUB'undan gelen ses_yok korunur, yinelenmez
kit3 = K.yukle(depo.kitap_yolu(kid))
for b in kit3["bloklar"]:
    if "Lewis" in b["metin"]["tr"]:
        b["ses_yok"] = {"tr": [{"once": "İranlı bir Şiî'dir", "metin": "(B. Lewis, The Middle East and the West)"}]}
K.kaydet(kit3, depo.kitap_yolu(kid))
depo._denetim(kid)
kit4 = K.yukle(depo.kitap_yolu(kid))
sy4 = [x["metin"] for b in kit4["bloklar"] for x in (b.get("ses_yok") or {}).get("tr", [])]
kontrol("EPUB'dan gelen işaret yinelenmez", sy4.count("(B. Lewis, The Middle East and the West)") == 1)

# ---------------------------------------------------------------- (3) seslendirme bekletme
gonderilen = []
cikti.studyoya_gonder = lambda kit: gonderilen.append(1) or {"is": 1}
depo._studyoya_zincirle(kid)
kontrol("seslendirme kendiliğinden kapalı: gönderilmez, uyarı yazılır", not gonderilen and
        depo.durum_oku(kid)["studyo_uyari"].startswith("Seslendirme bekletiliyor"))
yz.ayar_yaz(seslendirme_otomatik=True)
depo._studyoya_zincirle(kid)
kontrol("açılınca gönderilir", gonderilen == [1])

# ---------------------------------------------------------------- denetim modülü: Hazırlık'ın sınanmış kuralları
kontrol("kural: harf işareti farkı sayılmaz", D._uzaklik(D._imsiz("Birakiniz"), D._imsiz("Bırakınız")) == 0)
kontrol("kural: eski yazım korunur", D._imla("kalblere") == D._imla("kalplere"))
kontrol("kural: olumsuzluk eki değişemez", bool(D.OLUMSUZ.search("bilmiyorlar")) != bool(D.OLUMSUZ.search("biliyorlar")))
sunucu.shutdown()
print("SONUC:", "HEPSI GECTI" if not hata else f"{hata} HATA")
sys.exit(1 if hata else 0)
