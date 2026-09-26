"""Diğer üç dedplay uygulamasıyla HTTP üzerinden konuşur."""
import os
import re
import time

import requests

HOST = "http://host.docker.internal"
TRANSLATE = os.environ.get("TRANSLATE_URL", f"{HOST}:8060").rstrip("/")
OKUMA = os.environ.get("OKUMA_URL", f"{HOST}:8020").rstrip("/")
OSMANLICA = os.environ.get("OSMANLICA_URL", f"{HOST}:8089").rstrip("/")
OSM_OLLAMA = os.environ.get("OSM_USE_OLLAMA", "false").lower() in ("1", "true", "yes", "evet")
T = 30


# ---------------- Translate ----------------
def tr_submit(path, filename, lang):
    with open(path, "rb") as f:
        r = requests.post(f"{TRANSLATE}/api/jobs", files={"file": (filename, f)},
                          data={"src_lang": lang if lang in ("ar", "en", "fr") else "auto"}, timeout=900)
    r.raise_for_status()
    return r.json()["id"]


def tr_job(tid):
    r = requests.get(f"{TRANSLATE}/api/jobs", timeout=T)
    r.raise_for_status()
    return next((j for j in r.json() if j["id"] == tid), None)


def tr_resume(tid):
    requests.post(f"{TRANSLATE}/api/jobs/{tid}/resume", timeout=T).raise_for_status()


def tr_download(tid, fmt, dest, bilingual=0):
    with requests.get(f"{TRANSLATE}/api/jobs/{tid}/download", params={"fmt": fmt, "bilingual": bilingual},
                      stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)


def tr_stream(tid, fmt, bilingual):
    r = requests.get(f"{TRANSLATE}/api/jobs/{tid}/download", params={"fmt": fmt, "bilingual": bilingual},
                     stream=True, timeout=600)
    r.raise_for_status()
    return r


# ---------------- Kitap Okuma ----------------
def ok_submit(path, filename):
    with open(path, "rb") as f:
        r = requests.post(f"{OKUMA}/upload", files={"file": (filename, f)}, timeout=900)
    r.raise_for_status()


def ok_status(book_name):
    """Kitap Okuma /status içinden bu kitabın kaydını döndürür: (durum, bitti, toplam)."""
    r = requests.get(f"{OKUMA}/status", timeout=T)
    r.raise_for_status()
    for key, val in r.json().items():
        if os.path.splitext(key)[0] == book_name:
            m = re.search(r"(\d+)\s*/\s*(\d+)", str(val.get("progress", "")))
            done, total = (int(m.group(1)), int(m.group(2))) if m else (None, None)
            return str(val.get("status", "")), done, total
    return None, None, None


def ok_clear(filename):
    """Kitap Okuma'nın durum listesinden bu kitabı kaldırır (hata olursa sessizce geçer)."""
    from urllib.parse import quote
    try:
        requests.delete(f"{OKUMA}/status/{quote(filename, safe='')}", timeout=T)
    except Exception:
        pass


def ok_library_entry(book_name):
    r = requests.get(f"{OKUMA}/library", timeout=T)
    r.raise_for_status()
    for b in r.json().get("books", []):
        if b.get("title") == book_name and (b.get("m4b") or b.get("parts")):
            return b
    return None


def ok_stream(path):
    r = requests.get(f"{OKUMA}{path}", stream=True, timeout=600)
    r.raise_for_status()
    return r


# ---------------- Osmanlıca çevirici ----------------
def osm_convert(text, timeout=900):
    r = requests.post(f"{OSMANLICA}/api/upload-text",
                      data={"text": text, "use_ollama": "true" if OSM_OLLAMA else "false"}, timeout=T)
    r.raise_for_status()
    jid = r.json()["job_id"]
    end = time.time() + timeout
    delay = 0.5
    while time.time() < end:
        s = requests.get(f"{OSMANLICA}/api/status/{jid}", timeout=T).json()
        if s.get("error"):
            raise RuntimeError(f"Osmanlıca çevirici hatası: {s['error']}")
        if s.get("ready"):
            d = requests.get(f"{OSMANLICA}/api/download/{jid}", timeout=T)
            d.raise_for_status()
            d.encoding = "utf-8"
            return d.text
        time.sleep(delay)
        delay = min(delay * 1.5, 5)
    raise TimeoutError("Osmanlıca çeviri zaman aşımına uğradı")
