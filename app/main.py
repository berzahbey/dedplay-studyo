import json
import os
import shutil
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import clients, db
from .export import FORMATS, build
from .worker import resume, save_outputs, worker

app = FastAPI(title="Dedplay Studio")
STATIC = os.path.join(os.path.dirname(__file__), "static")
KAYNAK = os.environ.get("KAYNAK_DIR", "/kaynak")
ALLOWED = {".epub", ".pdf", ".docx", ".txt"}
LANGS = {"auto", "tr", "ar", "en", "fr"}
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.on_event("startup")
def startup():
    db.init()
    worker.start()


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


@app.get("/favicon.ico")
def favicon():
    return FileResponse(os.path.join(STATIC, "icon-32.png"))


def _disp(name):
    return {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"}


# ---------------- işler ----------------
@app.get("/api/jobs")
def jobs():
    out = []
    for j in db.list_jobs():
        d = dict(j)
        d["audio"] = json.loads(d["audio"]) if d["audio"] else None
        out.append(d)
    return out


def _new_job(name, lang):
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED:
        raise HTTPException(400, "Stüdyo EPUB, PDF, DOCX ve TXT dosyalarını kabul eder.")
    return db.create_job(name, lang if lang in LANGS else "auto")


@app.post("/api/jobs")
def create_job(file: UploadFile = File(...), lang: str = Form("auto")):
    name = os.path.basename(file.filename or "kitap")
    jid = _new_job(name, lang)
    with open(db.source_path(jid, name), "wb") as f:
        shutil.copyfileobj(file.file, f)
    db.update(jid, status="active")
    return {"id": jid}


def _safe(rel):
    base = os.path.realpath(KAYNAK)
    p = os.path.realpath(os.path.join(base, (rel or "").lstrip("/")))
    if p != base and not p.startswith(base + os.sep):
        raise HTTPException(400, "Geçersiz yol")
    return p


@app.get("/api/browse")
def browse(path: str = ""):
    if not os.path.isdir(KAYNAK):
        return {"available": False, "path": "", "dirs": [], "files": []}
    p = _safe(path)
    if not os.path.isdir(p):
        raise HTTPException(404, "Klasör bulunamadı")
    dirs, files = [], []
    for e in sorted(os.scandir(p), key=lambda e: e.name.lower()):
        if e.name.startswith("."):
            continue
        try:
            if e.is_dir():
                dirs.append(e.name)
            elif os.path.splitext(e.name)[1].lower() in ALLOWED:
                files.append({"name": e.name, "size": e.stat().st_size})
        except OSError:
            continue
    rel = os.path.relpath(p, os.path.realpath(KAYNAK))
    return {"available": True, "path": "" if rel == "." else rel, "dirs": dirs, "files": files}


class ServerFile(BaseModel):
    path: str
    lang: str = "auto"


@app.post("/api/jobs/from-server")
def job_from_server(f: ServerFile):
    p = _safe(f.path)
    if not os.path.isfile(p):
        raise HTTPException(404, "Dosya bulunamadı")
    name = os.path.basename(p)
    jid = _new_job(name, f.lang)
    shutil.copyfile(p, db.source_path(jid, name))
    db.update(jid, status="active")
    return {"id": jid}


@app.post("/api/jobs/{job_id}/resume")
def resume_job(job_id: int):
    resume(job_id)
    return {"ok": True}


@app.post("/api/jobs/{job_id}/save")
def save_job(job_id: int):
    j = db.get(job_id)
    if not j or j["status"] != "done":
        raise HTTPException(409, "Kitap henüz tamamlanmadı.")
    try:
        return {"saved": save_outputs(job_id)}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int):
    db.delete_job(job_id)
    return {"ok": True}


# ---------------- indirmeler ----------------
@app.get("/api/jobs/{job_id}/download")
def download(job_id: int, fmt: str = "epub", variant: str = "tr"):
    job = db.get(job_id)
    if not job:
        raise HTTPException(404, "İş bulunamadı")
    if fmt not in FORMATS or variant not in ("tr", "osm", "iki"):
        raise HTTPException(400, "Geçersiz biçim")
    parts = db.all_parts(job_id)
    if not parts:
        raise HTTPException(409, "Metin parçaları henüz hazır değil.")
    data, media, name = build(job, parts, fmt, variant)
    return Response(data, media_type=media, headers=_disp(name))


@app.get("/api/jobs/{job_id}/audio")
def audio(job_id: int, part: int = 0):
    job = db.get(job_id)
    if not job or not job["audio"]:
        raise HTTPException(404, "Sesli kitap henüz hazır değil.")
    a = json.loads(job["audio"])
    paths = [a["m4b"]] if a.get("m4b") else [p if isinstance(p, str) else p.get("m4b") or p.get("url") for p in a.get("parts") or []]
    if part >= len(paths) or not paths[part]:
        raise HTTPException(404, "Ses dosyası bulunamadı.")
    r = clients.ok_stream(paths[part])
    headers = _disp(os.path.basename(paths[part]))
    if r.headers.get("content-length"):
        headers["Content-Length"] = r.headers["content-length"]
    return StreamingResponse(r.iter_content(1 << 16), media_type="application/octet-stream", headers=headers)


@app.get("/api/jobs/{job_id}/translation")
def translation(job_id: int, fmt: str = "epub", bilingual: int = 0):
    """Translate'in kendi çıktıları (aslıyla birlikte iki dilli dahil)."""
    job = db.get(job_id)
    if not job or not job["tr_job"]:
        raise HTTPException(404, "Bu kitap çevrilmedi.")
    r = clients.tr_stream(job["tr_job"], fmt, bilingual)
    cd = r.headers.get("content-disposition") or _disp(f"{job['title']}.{fmt}")["Content-Disposition"]
    return StreamingResponse(r.iter_content(1 << 16), media_type=r.headers.get("content-type"),
                             headers={"Content-Disposition": cd})


@app.get("/api/services")
def services():
    """Diğer uygulamalara ulaşılabiliyor mu?"""
    out = {}
    for name, url in (("translate", clients.TRANSLATE + "/api/jobs"), ("okuma", clients.OKUMA + "/status"),
                      ("osmanlica", clients.OSMANLICA + "/docs")):
        try:
            out[name] = clients.requests.get(url, timeout=4).status_code < 500
        except Exception:
            out[name] = False
    return out
