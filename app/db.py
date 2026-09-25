import os
import shutil
import sqlite3
import time

DATA_DIR = os.environ.get("DATA_DIR", "/data")
DB_PATH = os.path.join(DATA_DIR, "studyo.db")
WORK = os.path.join(DATA_DIR, "work")


def conn():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c


def q(sql, args=(), one=False):
    with conn() as c:
        rows = c.execute(sql, args).fetchall()
    return (rows[0] if rows else None) if one else rows


def x(sql, args=()):
    with conn() as c:
        return c.execute(sql, args).lastrowid


def init():
    os.makedirs(WORK, exist_ok=True)
    with conn() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              filename TEXT, title TEXT, lang TEXT,
              status TEXT, stage TEXT, error TEXT, note TEXT,
              tr_job INTEGER, tr_state TEXT, tr_done INTEGER DEFAULT 0, tr_total INTEGER DEFAULT 0,
              book_name TEXT, ok_state TEXT, ok_done INTEGER DEFAULT 0, ok_total INTEGER DEFAULT 0, audio TEXT,
              osm_state TEXT, osm_done INTEGER DEFAULT 0, osm_total INTEGER DEFAULT 0, osm_title TEXT,
              created REAL, finished REAL);
            CREATE TABLE IF NOT EXISTS parts(
              job_id INTEGER, idx INTEGER, name TEXT, tr TEXT, osm TEXT,
              PRIMARY KEY(job_id, idx));
            """
        )
        cols = [r[1] for r in c.execute("PRAGMA table_info(jobs)")]
        if "saved" not in cols:
            c.execute("ALTER TABLE jobs ADD COLUMN saved TEXT")


def job_dir(job_id):
    d = os.path.join(WORK, str(job_id))
    os.makedirs(d, exist_ok=True)
    return d


def source_path(job_id, filename):
    return os.path.join(job_dir(job_id), "kaynak" + os.path.splitext(filename)[1].lower())


def create_job(filename, lang):
    return x(
        "INSERT INTO jobs(filename,title,lang,status,stage,tr_state,ok_state,osm_state,created) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (filename, os.path.splitext(filename)[0], lang, "uploading", "detect",
         "bekliyor", "bekliyor", "bekliyor", time.time()),
    )


def get(job_id):
    return q("SELECT * FROM jobs WHERE id=?", (job_id,), one=True)


def update(job_id, **kw):
    if kw:
        sets = ", ".join(f"{k}=?" for k in kw)
        x(f"UPDATE jobs SET {sets} WHERE id=?", (*kw.values(), job_id))


def active_jobs():
    return q("SELECT * FROM jobs WHERE status='active' ORDER BY id")


def list_jobs():
    return q("SELECT * FROM jobs WHERE status!='uploading' ORDER BY id DESC")


def delete_job(job_id):
    with conn() as c:
        c.execute("DELETE FROM parts WHERE job_id=?", (job_id,))
        c.execute("DELETE FROM jobs WHERE id=?", (job_id,))
    shutil.rmtree(os.path.join(WORK, str(job_id)), ignore_errors=True)


# ---- Osmanlıca parçaları ----
def insert_parts(job_id, items):
    with conn() as c:
        c.execute("DELETE FROM parts WHERE job_id=?", (job_id,))
        c.executemany("INSERT INTO parts(job_id,idx,name,tr) VALUES(?,?,?,?)",
                      [(job_id, i, n, t) for i, (n, t) in enumerate(items)])


def pending_parts(job_id):
    return q("SELECT * FROM parts WHERE job_id=? AND osm IS NULL ORDER BY idx", (job_id,))


def all_parts(job_id):
    return q("SELECT * FROM parts WHERE job_id=? ORDER BY idx", (job_id,))


def save_part(job_id, idx, osm):
    with conn() as c:
        c.execute("UPDATE parts SET osm=? WHERE job_id=? AND idx=?", (osm, job_id, idx))
        c.execute("UPDATE jobs SET osm_done=osm_done+1 WHERE id=?", (job_id,))
