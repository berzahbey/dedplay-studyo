"""Stüdyo iş akışı.

Her kitap şu aşamalardan geçer:
  detect    → dil belirlenir
  (Türkçe olmayan kitap durur: Stüdyo yalnız Türkçe kitap alır; Translate 5 Ekim 2026'da kaldırıldı)
  produce   → Kitap Okuma seslendirir  +  Osmanlıca çevirici parçaları çevirir (aynı anda)
  done
"""
import glob
import json
import os
import re
import shutil
import threading
import time
import traceback

import requests

from . import clients, db, textsrc, duzelt
from .detect import detect_lang, sample_text

TEXT_DIR = os.environ.get("OKUMA_TEXT_DIR", "/okuma-text")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/cikti")
TICK = 4
OSM_BUDGET = 20  # saniye: her turda Osmanlıcaya ayrılan en fazla süre


def ok_filename(j):
    """Kitabın Kitap Okuma'ya hangi dosya adıyla gönderildiği."""
    if not j["book_name"]:
        return None
    if j["lang"] == "tr":
        return j["book_name"] + os.path.splitext(j["filename"])[1].lower()
    return j["book_name"] + ".epub"


def parts_to_epub(parts, title, out_path):
    """Temiz metin parçalarından EPUB: her parça ayrı bölüm (Kitap Okuma her bölümü bir ses parçası yapar)."""
    import html as _html
    from ebooklib import epub
    book = epub.EpubBook()
    book.set_identifier(f"dedplay-{abs(hash(title))}")
    book.set_title(title)
    book.set_language("tr")
    bolumler = []
    for i, p in enumerate(parts, 1):
        ch = epub.EpubHtml(title=f"{i}", file_name=f"b{i:04d}.xhtml", lang="tr")
        satirlar = [re.sub(r"^\s*\d{1,3}\s*[.)]\s*", "", x) for x in p["tr"].split("\n")]  # ayet/madde no okunmaz
        satirlar = [x for x in satirlar if x.strip()]
        # tur 2/C: parçanın ilk satırı (bölüm başlığı) <h1>: Kitap Okuma M4B bölüm adını buradan alır (Bolum_001 yerine)
        bas = f"<h1>{_html.escape(satirlar[0])}</h1>" if satirlar and len(satirlar[0]) <= 120 else ""
        govde = satirlar[1:] if bas else satirlar
        ch.content = "<html><body>" + bas + "".join(f"<p>{_html.escape(x)}</p>" for x in govde) + "</body></html>"
        book.add_item(ch)
        bolumler.append(ch)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = bolumler
    epub.write_epub(out_path, book)
    return out_path


def txt_to_epub(txt_path, title, out_path):
    """Kitap Okuma sadece PDF/EPUB kabul ettiği için düz metni basit bir EPUB'a çevirir."""
    import html as _html
    from ebooklib import epub
    text = open(txt_path, encoding="utf-8").read()
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    book = epub.EpubBook()
    book.set_identifier(f"dedplay-metin-{abs(hash(title))}")
    book.set_title(title)
    book.set_language("tr")
    ch = epub.EpubHtml(title=title, file_name="metin.xhtml", lang="tr")
    ch.content = "<html><body>" + "".join(f"<p>{_html.escape(p)}</p>" for p in paras) + "</body></html>"
    book.add_item(ch)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", ch]
    epub.write_epub(out_path, book)
    return out_path


def _natural(path):
    m = re.search(r"(\d+)", os.path.basename(path))
    return int(m.group(1)) if m else 0


def _read(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1254", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return ""


class Worker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.seen = {}  # job_id -> (dosya sayısı, kaç turdur sabit)
        self.no_orig = set()  # ilk metni çıkarılamayan işler (Kitap Okuma'nın metnine dönülür)
        self.kayip = {}  # job_id -> Kitap Okuma listesinde kaç turdur görünmüyor

    def run(self):
        while True:
            for job in db.active_jobs():
                try:
                    self.step(job)
                    if job["note"]:
                        db.update(job["id"], note=None)
                except requests.RequestException as e:
                    # Geçici bağlantı sorunu: işi durdurma, bir sonraki turda tekrar dene
                    db.update(job["id"], note=f"Bağlantı sorunu, tekrar denenecek: {str(e)[:150]}")
                except Exception as e:
                    traceback.print_exc()
                    db.update(job["id"], status="error", error=str(e)[:500])
            time.sleep(TICK)

    # ------------------------------------------------------------
    def step(self, j):
        jid, stage = j["id"], j["stage"]
        src = db.source_path(jid, j["filename"])

        if stage == "detect":
            lang = j["lang"]
            if lang == "auto":
                lang = detect_lang(sample_text(src))
                if lang is None and src.lower().endswith(".pdf"):
                    lang = _ocr_ile_dil(src)  # taranmış PDF: birkaç sayfayı OCR'layıp dili oradan anla
                if lang is None:
                    raise RuntimeError("Kitabın dili algılanamadı (taranmış bir kitap olabilir). "
                                       "Silip 'Kitap dili' seçeneğini elle belirleyerek yeniden ekleyin.")
            if lang == "tr":
                db.update(jid, lang="tr", tr_state="atlandi", stage="produce", book_name=j["title"])
            else:
                db.update(jid, lang=lang)
                raise RuntimeError(f"Kitap Türkçe değil ({lang}). Stüdyo yalnız Türkçe kitap alır (çeviri yok). "
                                   "Kitap Türkçeyse silip 'Kitap dili: Türkçe' seçerek yeniden ekleyin.")
            return

        if stage == "translate":  # eski iş (Translate kaldırıldı)
            raise RuntimeError("Bu iş Translate'te çevriliyordu; çeviri kaldırıldı. İşi silebilirsiniz.")

        if stage == "produce":
            self.step_okuma(db.get(jid), src)
            self.step_osm(db.get(jid))
            j = db.get(jid)
            if j["ok_state"] == "bitti" and j["osm_state"] == "bitti":
                if not j["osm_title"] and j["lang"] != "tr" and not j["auto_title"]:
                    db.update(jid, osm_title=j["title"])  # yabancı dosya adı Osmanlıcaya harf harf aktarılmaz
                    j = db.get(jid)
                if not j["osm_title"]:
                    try:
                        db.update(jid, osm_title=clients.osm_convert(j["title"]).strip())
                    except Exception:
                        pass
                db.update(jid, stage="done", status="done", finished=time.time())
                try:
                    save_outputs(jid)
                except Exception as e:
                    db.update(jid, note=f"Dosyalar çıktı klasörüne kaydedilemedi: {str(e)[:200]}")
                if ok_filename(j):
                    clients.ok_clear(ok_filename(j))  # Kitap Okuma'nın listesinden kaldır

    # ------------------------------------------------------------
    def step_okuma(self, j, src):
        jid, name, state = j["id"], j["book_name"], j["ok_state"]
        if state == "bitti":
            return
        if state == "bekliyor" and j["degisti"] and time.time() - j["degisti"] < DUZELTME_BEKLEME:
            return  # tur 2/C: kitap az önce düzeltildi; art arda düzeltmeler bitsin (her biri için M4B yeniden kurulmasın)
        if state == "bekliyor" and _baska_seslendirme_var(jid):
            return  # tur 2/A: kitaplar kendiliğinden geldiği için seslendirme tek tek (sayı tur 4'te ölçülerek)
        if state == "bekliyor":
            # Seslendirme de Stüdyo'nun temiz metninden yapılır (ön sayfalar, içindekiler ve dipnotlar hariç).
            ana = [p for p in db.all_parts(jid) if p["name"].startswith("Parca_")]
            if not ana and jid not in self.no_orig and j["osm_state"] == "bekliyor":
                return  # temiz metin henüz hazırlanıyor
            if ana:
                path = parts_to_epub(ana, name, os.path.join(db.job_dir(jid), name + ".epub"))
                clients.ok_submit(path, name + ".epub")
                db.update(jid, ok_state="sirada")
                return
            if j["lang"] == "tr":
                path, filename = src, name + os.path.splitext(j["filename"])[1].lower()
                if filename.endswith(".txt"):  # yapıştırılan metin: Kitap Okuma için EPUB'a çevir
                    path = txt_to_epub(src, name, os.path.join(db.job_dir(jid), name + ".epub"))
                    filename = name + ".epub"
            else:
                path, filename = os.path.join(db.job_dir(jid), name + ".epub"), name + ".epub"
            clients.ok_submit(path, filename)
            db.update(jid, ok_state="sirada")
            return
        status, done, total = clients.ok_status(name)
        upd = {}
        if total:
            upd.update(ok_done=done, ok_total=total)
        if status:
            low = status.lower()
            if "error" in low or "hata" in low:
                upd.update(ok_state="hata", error="Seslendirme hata verdi (Kitap Okuma).")
            elif state != "hata":
                upd["ok_state"] = "calisiyor" if "process" in low or "işlen" in low else "sirada"
        entry = clients.ok_library_entry(name)
        isleniyor = bool(status) and not any(k in status.lower() for k in ("complet", "bitti", "error", "hata"))
        # Bekçi: seslendirme sürüyor görünüp Kitap Okuma'nın listesinde hiç yoksa (Kitap Okuma yeniden
        # başladıysa yarım kalan işi unutur) ~1 dakika sonra yeniden gönder; kaldığı yerden devam eder.
        if not status and not entry and state in ("sirada", "calisiyor"):
            self.kayip[jid] = self.kayip.get(jid, 0) + 1
            if self.kayip[jid] >= 15:
                self.kayip.pop(jid, None)
                print(f"[{jid}] Kitap Okuma '{name}' kitabını listesinde tutmuyor; yeniden gönderiliyor.", flush=True)
                db.update(jid, ok_state="bekliyor")
                return
        else:
            self.kayip.pop(jid, None)
        if entry and not isleniyor:   # yeniden gönderilen kitapta eski M4B'yi "bitti" sanma (tur 2/C)
            upd.update(ok_state="bitti", audio=json.dumps(entry, ensure_ascii=False))
            if j["yenile"]:            # seslendirme sürerken kitap düzeltilmişti: bir kez daha gönder
                upd.update(ok_state="bekliyor", yenile=0)
            if upd.get("ok_total") or j["ok_total"]:
                upd["ok_done"] = upd.get("ok_total") or j["ok_total"]
        if upd:
            db.update(jid, **upd)

    def step_osm(self, j):
        jid, state = j["id"], j["osm_state"]
        if state == "bitti":
            return
        if state == "bekliyor" and jid not in self.no_orig:
            # Osmanlıca ve Türkçe dosyalar için kitabın İLK metni kullanılır
            # (Kitap Okuma'nın metni seslendirme için değiştirilmiştir).
            items = self.original_parts(j)
            if items:
                db.insert_parts(jid, items)
                db.update(jid, osm_state="calisiyor", osm_done=0, osm_total=len(items))
                return
            self.no_orig.add(jid)
            print(f"[{jid}] Kitabın ilk metni çıkarılamadı; Kitap Okuma'nın metni kullanılacak.", flush=True)
        if state == "bekliyor":
            files = sorted(glob.glob(os.path.join(TEXT_DIR, glob.escape(j["book_name"]), "Parca_*.txt")),
                           key=_natural)
            if not files:
                return
            # Kitap Okuma parçaları yazmayı bitirdi mi? Toplam biliniyorsa ona, yoksa sayının sabit kalmasına bak.
            count, stable = self.seen.get(jid, (0, 0))
            stable = stable + 1 if count == len(files) else 0
            self.seen[jid] = (len(files), stable)
            ready = (j["ok_total"] and len(files) >= j["ok_total"]) or stable >= 3
            if not ready:
                return
            db.insert_parts(jid, [(os.path.basename(f), _read(f)) for f in files])
            db.update(jid, osm_state="calisiyor", osm_done=0, osm_total=len(files))
            self.seen.pop(jid, None)
            return
        if state == "calisiyor":
            end = time.time() + OSM_BUDGET
            pending = db.pending_parts(jid)
            for p in pending:
                text = p["tr"] or ""
                db.save_part(jid, p["idx"], clients.osm_convert_paras(text) if text.strip() else "")
                if time.time() > end:
                    return
            db.update(jid, osm_state="bitti")


def _original_parts(j):
    try:
        notes = []
        if j["lang"] == "tr":
            paras, notes = textsrc.extract_full(db.source_path(j["id"], j["filename"]))
        else:
            return []  # Türkçe olmayan kitap işlenmez (Translate kaldırıldı)
        paras = duzelt.duzelt(paras)  # satır içi üst bilgiler, bölünmüş kelimeler, çöp işaretler, sayfa atıfları
        if sum(len(p) for p in paras) < 50:
            return []
        return textsrc.parts_with_notes(paras, notes)
    except Exception:
        traceback.print_exc()
        return []


Worker.original_parts = staticmethod(_original_parts)


def _baska_seslendirme_var(jid):
    """Kitap Okuma her yüklenen kitabı ayrı iş parçacığında hemen başlatır: aynı anda çok kitap sunucuyu boğar.
    Başka bir etkin işin seslendirmesi sürüyorsa (sırada/çalışıyor) bu iş bekler."""
    return any(o["id"] != jid and o["ok_state"] in ("sirada", "calisiyor") for o in db.active_jobs())


def _ocr_ile_dil(path):
    """Metin katmanı olmayan PDF'te kitabın içinden 3 sayfayı OCR'layıp dili algılar.
    Emin olunamazsa (yeterince tanıdık kelime yoksa) None döner."""
    try:
        import fitz
        from .detect import WORDS
        n = len(fitz.open(path))
        sayfalar = sorted({max(0, min(n - 1, k)) for k in (4, 9, 14)})
        text = ""
        for i in sayfalar:
            _, items = textsrc._ocr_page((path, i))
            text += " ".join(t for t, _ in items) + "\n"
        lang = detect_lang(text)
        kelimeler = re.findall(r"[^\W\d_]+", text.lower())
        if lang in WORDS and sum(1 for w in kelimeler if w in WORDS[lang]) >= 8:
            print(f"[dil] {os.path.basename(path)}: OCR ile '{lang}' algılandı", flush=True)
            return lang
    except Exception:
        traceback.print_exc()
    return None


DEDPLAY_DIR = os.environ.get("DEDPLAY_DIR", "/dedplay")
DUZELTME_BEKLEME = int(os.environ.get("DUZELTME_BEKLEME", "120"))   # saniye
DIL_KLASORU = {"tr": "Türkçe", "osm": "Osmanlıca", "iki": "Türkçe-Osmanlıca"}
BICIM_KLASORU = {"pdf": "PDF", "docx": "DOCX", "txt": "TXT", "html": "HTML"}   # EPUB'ları Kütüphane yazar


def save_outputs_yeni(j, parts, name):
    """Tur 3: /dedplay altında biçim/dil/kitap adı düzeni:
    PDF/Türkçe/Kitap.pdf, PDF/Osmanlıca/…, PDF/Türkçe-Osmanlıca/… (DOCX, TXT, HTML aynı); MP3/Kitap/Kitap - 001.mp3;
    M4B/Kitap.m4b (büyük kitapta Kitap - 1.m4b, - 2…). Kitap Okuma'nın kendi dosyaları yerinde kalır (düzeltmede yalnız
    değişen bölüm yeniden okunsun diye)."""
    from .export import build
    for fmt, bk in BICIM_KLASORU.items():
        for variant, dk in DIL_KLASORU.items():
            data, _, _ = build(j, parts, fmt, variant)
            d = os.path.join(DEDPLAY_DIR, bk, dk)
            os.makedirs(d, exist_ok=True)
            hedef = os.path.join(d, f"{name}.{fmt}")
            with open(hedef + ".tmp", "wb") as f:
                f.write(data)
            os.replace(hedef + ".tmp", hedef)
    kaynak = os.path.join(OUTPUT_DIR, j["book_name"] or name)
    mp3s = sorted(glob.glob(os.path.join(glob.escape(kaynak), "Parca_*.mp3")) +
                  glob.glob(os.path.join(glob.escape(kaynak), "Bolum_*.mp3")), key=_natural)
    if mp3s:
        mdir = os.path.join(DEDPLAY_DIR, "MP3", name)
        shutil.rmtree(mdir, ignore_errors=True)
        os.makedirs(mdir)
        width = max(3, len(str(len(mp3s))))
        for n, src in enumerate(mp3s, 1):
            dst = os.path.join(mdir, f"{name} - {n:0{width}d}.mp3")
            shutil.copy2(src, dst)
            _tag_mp3(dst, name, n, len(mp3s), width)
    m4bs = sorted(glob.glob(os.path.join(glob.escape(kaynak), "*.m4b")), key=_natural)
    if m4bs:
        md = os.path.join(DEDPLAY_DIR, "M4B")
        os.makedirs(md, exist_ok=True)
        for eski in glob.glob(os.path.join(glob.escape(md), glob.escape(name) + "*.m4b")):
            if os.path.basename(eski) == name + ".m4b" or re.fullmatch(re.escape(name) + r" - \d+\.m4b", os.path.basename(eski)):
                os.remove(eski)
        for i, src in enumerate(m4bs, 1):
            hedef = os.path.join(md, f"{name}.m4b" if len(m4bs) == 1 else f"{name} - {i}.m4b")
            shutil.copy2(src, hedef + ".tmp")
            os.replace(hedef + ".tmp", hedef)


def save_outputs(job_id):
    """Biten kitabın dosyalarını çıktı klasörüne kaydeder: M4B kitap klasörünün üstünde kalır,
    diğer dosyalar biçimlerine göre alt klasörlere (EPUB, PDF, Word, HTML, TXT) ayrılır."""
    if not os.path.isdir(OUTPUT_DIR):
        raise RuntimeError("Çıktı klasörü bağlı değil (docker-compose'da /cikti).")
    from .export import build
    j = db.get(job_id)
    if not j["osm_title"] and j["lang"] != "tr" and not j["auto_title"]:
        db.update(job_id, osm_title=j["title"])
        j = db.get(job_id)
    if not j["osm_title"]:
        try:
            db.update(job_id, osm_title=clients.osm_convert(j["title"]).strip())
            j = db.get(job_id)
        except Exception:
            pass
    parts = db.all_parts(job_id)
    if not parts:
        raise RuntimeError("Metin parçaları yok.")
    name = (j["book_name"] or j["title"]).replace("/", "-")
    if os.path.isdir(DEDPLAY_DIR):          # tur 3: yeni çıktı düzeni
        save_outputs_yeni(j, parts, name)
        db.update(job_id, saved=name, note=None)
        return name
    folder = os.path.join(OUTPUT_DIR, name)
    os.makedirs(folder, exist_ok=True)
    subdir = {"epub": "EPUB", "pdf": "PDF", "docx": "Word", "html": "HTML", "txt": "TXT"}
    # Eski sürümün klasörün üstüne bıraktığı dağınık dosyaları temizle (M4B ve MP3'e dokunma)
    for f in os.listdir(folder):
        fp = os.path.join(folder, f)
        if os.path.isfile(fp) and os.path.splitext(f)[1].lower().lstrip(".") in subdir:
            os.remove(fp)
    for fmt, sd in subdir.items():
        os.makedirs(os.path.join(folder, sd), exist_ok=True)
        for variant in ("tr", "osm", "iki"):
            data, _, fname = build(j, parts, fmt, variant)
            with open(os.path.join(folder, sd, fname.replace("/", "-")), "wb") as f:
                f.write(data)
    # MP3 parçaları: kitap adıyla, ek yer kaplamadan (aynı dosyaya ikinci ad = sabit bağlantı)
    mp3s = sorted(glob.glob(os.path.join(glob.escape(folder), "Parca_*.mp3")) +
                  glob.glob(os.path.join(glob.escape(folder), "Bolum_*.mp3")), key=_natural)
    if mp3s:
        mdir = os.path.join(folder, "MP3")
        shutil.rmtree(mdir, ignore_errors=True)
        os.makedirs(mdir)
        open(os.path.join(mdir, ".ignore"), "w").close()  # Audiobookshelf bu klasörü taramasın
        total = max(_natural(x) for x in mp3s)
        width = max(3, len(str(total)))
        for src in mp3s:
            n = _natural(src)
            dst = os.path.join(mdir, f"{name} - {n:0{width}d}.mp3")
            try:
                os.link(src, dst)
            except OSError:
                shutil.copy2(src, dst)
            _tag_mp3(dst, name, n, total, width)
        # MP3 klasöründeki kopyalar aynı dosyanın ikinci adı; üstteki Parca_ adları artık gereksiz.
        for src in mp3s:
            try:
                os.remove(src)
            except OSError:
                pass
    db.update(job_id, saved=name, note=None)
    return name


def _tag_mp3(path, book, n, total, width):
    """MP3'ün içine kitap bilgisini yazar (albüm = kitap adı, sıra numarası)."""
    try:
        from mutagen.easyid3 import EasyID3
        from mutagen.id3 import ID3NoHeaderError
        try:
            t = EasyID3(path)
        except ID3NoHeaderError:
            t = EasyID3()
        t["album"] = book
        t["title"] = f"{book} - {n:0{width}d}"
        t["tracknumber"] = f"{n}/{total}"
        t["artist"] = "Dedplay"
        t["genre"] = "Audiobook"
        t.save(path)
    except Exception:
        pass


def resume(job_id):
    """Hata veren ya da duran bir işi kaldığı yerden sürdürür."""
    j = db.get(job_id)
    if not j:
        return
    upd = {"status": "active", "error": None}
    if j["ok_state"] == "hata":
        upd["ok_state"] = "bekliyor"  # yeniden gönderilir; Kitap Okuma biten parçaları atlar
    if j["osm_state"] == "hata":
        upd["osm_state"] = "calisiyor"
    db.update(job_id, **upd)


worker = Worker()
