"""Stüdyo iş akışı.

Her kitap şu aşamalardan geçer:
  detect    → dil belirlenir
  translate → (Türkçe değilse) Translate çevirir, bitince Türkçe EPUB alınır
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

from . import clients, db
from .detect import detect_lang, sample_text

TEXT_DIR = os.environ.get("OKUMA_TEXT_DIR", "/okuma-text")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/cikti")
TICK = 4
OSM_BUDGET = 20  # saniye: her turda Osmanlıcaya ayrılan en fazla süre


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
                if lang is None:
                    raise RuntimeError("Kitabın dili algılanamadı (taranmış bir kitap olabilir). "
                                       "Silip 'Kitap dili' seçeneğini elle belirleyerek yeniden ekleyin.")
            if lang == "tr":
                db.update(jid, lang="tr", tr_state="atlandi", stage="produce", book_name=j["title"])
            else:
                tid = clients.tr_submit(src, j["filename"], lang)
                db.update(jid, lang=lang, tr_job=tid, tr_state="sirada", stage="translate")
            return

        if stage == "translate":
            t = clients.tr_job(j["tr_job"])
            if t is None:
                raise RuntimeError("Translate'teki çeviri işi bulunamadı (orada silinmiş olabilir).")
            state = {"queued": "sirada", "running": "calisiyor", "paused": "duraklatildi",
                     "error": "hata", "done": "bitti"}.get(t["status"], t["status"])
            db.update(jid, tr_done=t["done"], tr_total=t["total"], tr_state=state,
                      error=f"Çeviri durdu: {t['error']}" if state == "hata" else None)
            if state == "bitti":
                name = f"{j['title']} - Türkçe"
                clients.tr_download(j["tr_job"], "epub", os.path.join(db.job_dir(jid), name + ".epub"))
                db.update(jid, stage="produce", book_name=name)
            return

        if stage == "produce":
            self.step_okuma(db.get(jid), src)
            self.step_osm(db.get(jid))
            j = db.get(jid)
            if j["ok_state"] == "bitti" and j["osm_state"] == "bitti":
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

    # ------------------------------------------------------------
    def step_okuma(self, j, src):
        jid, name, state = j["id"], j["book_name"], j["ok_state"]
        if state == "bitti":
            return
        if state == "bekliyor":
            if j["lang"] == "tr":
                path, filename = src, name + os.path.splitext(j["filename"])[1].lower()
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
        if entry:
            upd.update(ok_state="bitti", audio=json.dumps(entry, ensure_ascii=False))
            if upd.get("ok_total") or j["ok_total"]:
                upd["ok_done"] = upd.get("ok_total") or j["ok_total"]
        if upd:
            db.update(jid, **upd)

    def step_osm(self, j):
        jid, state = j["id"], j["osm_state"]
        if state == "bitti":
            return
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
                db.save_part(jid, p["idx"], clients.osm_convert(text) if text.strip() else "")
                if time.time() > end:
                    return
            db.update(jid, osm_state="bitti")


def save_outputs(job_id):
    """Biten kitabın bütün dosyalarını çıktı klasörüne, sesli kitabın yanına kaydeder."""
    if not os.path.isdir(OUTPUT_DIR):
        raise RuntimeError("Çıktı klasörü bağlı değil (docker-compose'da /cikti).")
    from .export import build
    j = db.get(job_id)
    parts = db.all_parts(job_id)
    if not parts:
        raise RuntimeError("Metin parçaları yok.")
    name = (j["book_name"] or j["title"]).replace("/", "-")
    folder = os.path.join(OUTPUT_DIR, name)
    os.makedirs(folder, exist_ok=True)
    for variant in ("tr", "osm", "iki"):
        for fmt in ("epub", "pdf", "docx"):
            data, _, fname = build(j, parts, fmt, variant)
            with open(os.path.join(folder, fname.replace("/", "-")), "wb") as f:
                f.write(data)
    if j["tr_job"]:
        for fmt in ("epub", "pdf"):
            clients.tr_download(j["tr_job"], fmt,
                                os.path.join(folder, f"{j['title']} - Çeviri ve aslı.{fmt}".replace("/", "-")), 1)
    db.update(job_id, saved=name, note=None)
    return name


def resume(job_id):
    """Hata veren ya da duran bir işi kaldığı yerden sürdürür."""
    j = db.get(job_id)
    if not j:
        return
    upd = {"status": "active", "error": None}
    if j["tr_state"] in ("hata", "duraklatildi") and j["tr_job"]:
        clients.tr_resume(j["tr_job"])
        upd["tr_state"] = "sirada"
    if j["ok_state"] == "hata":
        upd["ok_state"] = "bekliyor"  # yeniden gönderilir; Kitap Okuma biten parçaları atlar
    if j["osm_state"] == "hata":
        upd["osm_state"] = "calisiyor"
    db.update(job_id, **upd)


worker = Worker()
