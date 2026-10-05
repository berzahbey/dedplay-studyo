"""Tur 2/A testleri: Osmanlıca bitince Türkçe kitap kendiliğinden Stüdyo'ya gider (Osmanlıca hazır, aynı süreçte);
seslendirme tek tek. Osmanlıca çevirici, Kitap Okuma ve epubcheck taklit edilir; hiçbir servis çağrılmaz.
Çalıştırma (sunucuda, kod klasöründe):
  docker run --rm -v "$PWD":/k -w /k -e PYTHONPATH=/app:/k berzahbey/dedplay-studyo:latest python tests/test_zincir.py"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
kok = tempfile.mkdtemp()
os.environ["DATA_DIR"] = os.path.join(kok, "kutuphane")
os.environ["STUDYO_DATA_DIR"] = os.path.join(kok, "studyo")
os.makedirs(os.environ["STUDYO_DATA_DIR"])

from app import birlesik  # noqa: F401  (tek uygulama: önce Kütüphane, sonra Stüdyo)
from app import clients, db, export, worker
from app import main as studyo
from kutuphane import depo, osmanlica
from kutuphane import kitap as K

BASARI = []


def ok(kosul, ad):
    BASARI.append(bool(kosul))
    print(("GECTI " if kosul else "KALDI ") + ad)


db.init()
depo.KITAPLAR = os.path.join(kok, "kutuphane", "kitaplar")
depo.epub_uret = lambda kid: depo.durum_yaz(kid, asama="hazır", epublar=[{"dosya": "x.epub", "diller": ["tr"]}])


def _yasak(*a, **k):
    raise AssertionError("Stüdyo Osmanlıcayı yeniden çevirmemeli")


clients.osm_convert = _yasak
clients.osm_convert_paras = _yasak
osm_cagri = []


def sahte_cevir(kit, ilerleme=None, zorla=False):  # Kütüphane'nin Osmanlıcası (elle düzeltilmiş olan korunur)
    osm_cagri.append(1)
    for b in kit["bloklar"]:
        if b["metin"].get("tr") and not b.get("elle", {}).get("osm"):
            b["metin"]["osm"] = "عثمانلیجه " + str(len(b["metin"]["tr"]))
    for n in kit.get("dipnotlar", {}).values():
        n["metin"]["osm"] = "حاشیه متنی"
    kit["kunye"]["baslik"]["osm"] = "اعتقادده سوزڭ اوزی"
    return kit


osmanlica.kitabi_cevir = sahte_cevir


def kitap_kur(kid, asil="tr"):
    if asil == "tr":
        kit = K.yeni({"baslik": {"tr": "İtikatta Sözün Özü"}, "yazar": {"tr": "İmam Gazali"}, "asil_dil": "tr",
                      "kaynak": {"tur": "dosya"}})
        K.blok_ekle(kit, "baslik", {"tr": "GİRİŞ"}, seviye=1)
        K.blok_ekle(kit, "p", {"tr": "Hamd Allah'adır.{{n0001}}"})
        K.blok_ekle(kit, "p", {"tr": "Elle düzeltilmiş satır.", "osm": "الله دوزلتیلمش"})
        kit["bloklar"][-1]["elle"] = {"osm": True}
        kit["dipnotlar"] = {"n0001": {"metin": {"tr": "Dipnot metni."}}}
    else:
        kit = K.yeni({"baslik": {"ar": "كتاب"}, "yazar": {"ar": ""}, "asil_dil": "ar", "kaynak": {"tur": "openiti"}})
        K.blok_ekle(kit, "p", {"ar": "نص"})
    os.makedirs(depo.klasor(kid), exist_ok=True)
    K.kaydet(kit, depo.kitap_yolu(kid))
    depo.durum_yaz(kid, asama="hazır")


def is_sayisi():
    return len(db.q("SELECT id FROM jobs"))


# 1) Osmanlıca işi bitince kendiliğinden Stüdyo'ya
kitap_kur("tr.kitap")
depo._isle("osmanlica", "tr.kitap", None)
d = depo.durum_oku("tr.kitap")
ok(osm_cagri and d.get("studyo", {}).get("is"), "Osmanlıca bitince kitap kendiliğinden Stüdyo'ya gitti")
jid = d["studyo"]["is"]
j = db.get(jid)
ok(j and j["stage"] == "produce" and j["status"] == "active" and j["lang"] == "tr", "Stüdyo işi seslendirmeye hazır")
ok(j["osm_state"] == "bitti", "Stüdyo'nun Osmanlıca adımı atlanır (çift çeviri yok)")
ok(j["osm_title"] == "اعتقادده سوزڭ اوزی", "Kitap adının Osmanlıcası Kütüphane'den gelir")
parcalar = db.all_parts(jid)
tum_osm = "\n".join(p["osm"] or "" for p in parcalar)
ok("الله دوزلتیلمش" in tum_osm, "Okuma ekranındaki elle Osmanlıca düzeltme Stüdyo'ya ulaşır")
ok(all(len((p["tr"] or "").split("\n")) == len((p["osm"] or "").split("\n")) for p in parcalar),
   "Türkçe ve Osmanlıca satırlar eşleşik")
ok(not d.get("studyo_uyari") and d.get("asama") == "hazır", "Kitap hazır, uyarı yok")

# Stüdyo çıktısı (iki dilli TXT) Kütüphane'nin Osmanlıcasını kullanır
veri, _, ad = export.build(db.get(jid), parcalar, "txt", "iki")
metin = veri.decode("utf-8") if isinstance(veri, bytes) else veri
ok("Hamd Allah'adır." in metin and "الله دوزلتیلمش" in metin and "{{" not in metin, f"İki dilli çıktı doğru ({ad})")

# 2) Yeniden Osmanlıca (ör. 'Osmanlıcayı yeniden çevir'): ikinci iş açılmaz
n = is_sayisi()
depo._isle("osmanlica", "tr.kitap", "1")
ok(is_sayisi() == n and depo.durum_oku("tr.kitap")["studyo"]["is"] == jid, "Stüdyo işi varken yeni iş açılmaz")

# 3) Stüdyo'daki iş silindiyse yeniden gönderilir
db.delete_job(jid)
depo._isle("osmanlica", "tr.kitap", None)
yeni = depo.durum_oku("tr.kitap")["studyo"]["is"]
ok(yeni != jid and db.get(yeni) is not None, "Stüdyo'da silinen iş için kitap yeniden gider")

# 4) Osmanlıca çevrilemediyse gönderilmez (Stüdyo ikinci kez çevirmesin)
kitap_kur("hata.kitap")
osmanlica.kitabi_cevir = lambda *a, **k: (_ for _ in ()).throw(ConnectionError("kapalı"))
n = is_sayisi()
depo._isle("osmanlica", "hata.kitap", None)
d = depo.durum_oku("hata.kitap")
ok(is_sayisi() == n and not d.get("studyo") and "Osmanlıca çevrilemediği" in (d.get("studyo_uyari") or ""),
   "Osmanlıca çevrilemezse Stüdyo'ya gitmez, açıklama yazılır")
ok(d.get("asama") == "hazır", "Kitap yine hazır (Türkçe EPUB)")
osmanlica.kitabi_cevir = sahte_cevir
depo._isle("osmanlica", "hata.kitap", "1")
d = depo.durum_oku("hata.kitap")
ok(d.get("studyo") and not d.get("studyo_uyari"), "Osmanlıca sonra başarılı olunca kendiliğinden gider, uyarı kalkar")

# 5) Arapça (OpenITI) kitap gitmez
kitap_kur("ar.kitap", "ar")
n = is_sayisi()
depo._studyoya_zincirle("ar.kitap")
ok(is_sayisi() == n and not depo.durum_oku("ar.kitap").get("studyo"), "Türkçe olmayan kitap Stüdyo'ya gitmez")

# 6) Elle gönderme (eski düğme ve HTTP adresi) çalışmaya devam eder
r = studyo.job_from_kutuphane(studyo.KutuphaneKitap(title="Deneme", parts=[{"name": "Parca_001", "tr": "Bir satır."}]))
ok(isinstance(r, dict) and db.get(r["id"])["osm_state"] == "calisiyor", "from-kutuphane adresi (Osmanlıcasız) eskisi gibi")

# 7) Seslendirme tek tek
gonderilen = []
clients.ok_submit = lambda yol, ad: gonderilen.append(ad)
for o in db.active_jobs():
    db.update(o["id"], status="done")
a = studyo.kutuphane_isi("Kitap A", "", [{"name": "Parca_001", "tr": "A metni.", "osm": "ا"}])
b = studyo.kutuphane_isi("Kitap B", "", [{"name": "Parca_001", "tr": "B metni.", "osm": "ب"}])
w = worker.Worker()
w.step_okuma(db.get(a), db.source_path(a, "Kitap A.epub"))
w.step_okuma(db.get(b), db.source_path(b, "Kitap B.epub"))
ok(gonderilen == ["Kitap A.epub"] and db.get(b)["ok_state"] == "bekliyor", "Bir kitap seslendirilirken öteki sırada bekler")
db.update(a, ok_state="bitti")
w.step_okuma(db.get(b), db.source_path(b, "Kitap B.epub"))
ok(gonderilen == ["Kitap A.epub", "Kitap B.epub"], "Önceki bitince sıradaki seslendirmeye gider")
db.update(b, ok_state="calisiyor", status="error")
c = studyo.kutuphane_isi("Kitap C", "", [{"name": "Parca_001", "tr": "C metni.", "osm": "ج"}])
w.step_okuma(db.get(c), db.source_path(c, "Kitap C.epub"))
ok(gonderilen[-1] == "Kitap C.epub", "Hatada duran işin seslendirmesi sırayı tutmaz")

print("SONUC:", "HEPSI GECTI" if all(BASARI) else f"{BASARI.count(False)} TEST KALDI")
sys.exit(0 if all(BASARI) else 1)
