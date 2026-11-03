"""Per-profile personal data: bookmarks (folders), notes bound to passages, highlights, tags,
user links, history, search history, favorites, hidden titles, desk templates, reading goals,
documents (chiddushim / notes editor), source sheets, covers, clipboard catcher, settings."""
import datetime as dt
import hashlib
import json
import os
import shutil
import sqlite3
import threading
import zipfile

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS bookmarks(id INTEGER PRIMARY KEY, folder TEXT DEFAULT 'General', ref TEXT, passage_id INT,
    work_id INT, title TEXT, note TEXT, created TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY, passage_id INT, ref TEXT, text TEXT, color TEXT DEFAULT '#fff3a0',
    tags TEXT DEFAULT '', private INT DEFAULT 0, shared_with TEXT DEFAULT '',
    created TEXT DEFAULT (datetime('now','localtime')), updated TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS highlights(id INTEGER PRIMARY KEY, passage_id INT, ref TEXT, color TEXT, w_from INT DEFAULT -1, w_to INT DEFAULT -1);
CREATE TABLE IF NOT EXISTS user_links(id INTEGER PRIMARY KEY, ref_a TEXT, ref_b TEXT, label TEXT,
    created TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS tags(passage_id INT, ref TEXT, tag TEXT, PRIMARY KEY(passage_id, tag));
CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, work_id INT, title TEXT, ref TEXT, ts TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS search_history(id INTEGER PRIMARY KEY, kind TEXT, query TEXT, opts TEXT, hits INT,
    ts TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS favorites(work_id INTEGER PRIMARY KEY, title TEXT);
CREATE TABLE IF NOT EXISTS hidden(work_id INTEGER PRIMARY KEY, title TEXT);
CREATE TABLE IF NOT EXISTS desks(name TEXT PRIMARY KEY, layout TEXT, updated TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS goals(id INTEGER PRIMARY KEY, work_id INT, title TEXT, start_date TEXT, end_date TEXT,
    total INT, done INT DEFAULT 0, log TEXT DEFAULT '[]');
CREATE TABLE IF NOT EXISTS docs(id INTEGER PRIMARY KEY, title TEXT, html TEXT, kind TEXT DEFAULT 'note', folder TEXT DEFAULT 'My Notes',
    tags TEXT DEFAULT '', private INT DEFAULT 0, created TEXT DEFAULT (datetime('now','localtime')),
    updated TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS sheets(id INTEGER PRIMARY KEY, title TEXT, items TEXT DEFAULT '[]', tags TEXT DEFAULT '',
    updated TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS covers(id INTEGER PRIMARY KEY, title TEXT, data TEXT, updated TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS clips(id INTEGER PRIMARY KEY, text TEXT, ref TEXT, ts TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS macros(name TEXT PRIMARY KEY, refs TEXT);
CREATE TABLE IF NOT EXISTS reading_log(id INTEGER PRIMARY KEY, work_id INT, passages INT, seconds INT, day TEXT);
CREATE TABLE IF NOT EXISTS transcriptions(id INTEGER PRIMARY KEY, title TEXT, image_paths TEXT, html TEXT,
    updated TEXT DEFAULT (datetime('now','localtime')));
"""

TABLES = ["bookmarks", "notes", "highlights", "user_links", "tags", "history", "search_history", "favorites", "hidden",
          "desks", "goals", "docs", "sheets", "covers", "clips", "macros", "reading_log", "transcriptions", "settings"]


class UserData:
    def __init__(self, profiles_dir, profile="Default"):
        self.dir = profiles_dir
        os.makedirs(profiles_dir, exist_ok=True)
        self.lock = threading.RLock()
        self.open(profile)

    def open(self, profile):
        self.profile = profile
        self.path = os.path.join(self.dir, f"{profile}.sqlite")
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()

    def profiles(self):
        return sorted(f[:-7] for f in os.listdir(self.dir) if f.endswith(".sqlite"))

    # ---------------------------------------------------------------- generic helpers
    def q(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def x(self, sql, args=()):
        with self.lock:
            cur = self.db.execute(sql, args)
            self.db.commit()
            return cur.lastrowid

    def list(self, table, where="", args=(), order="rowid DESC", limit=1000):
        assert table in TABLES
        return self.q(f"SELECT rowid AS _rowid, * FROM {table} {('WHERE ' + where) if where else ''} ORDER BY {order} LIMIT {int(limit)}", args)

    def save(self, table, row):
        """Insert or update a row (dict). Uses 'id' (or primary key) when present."""
        assert table in TABLES
        row = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v) for k, v in row.items() if not k.startswith("_")}
        cols = [r["name"] for r in self.q(f"PRAGMA table_info({table})")]
        row = {k: v for k, v in row.items() if k in cols}
        if "updated" in cols:
            row["updated"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        keys = list(row)
        sql = f"INSERT OR REPLACE INTO {table}({','.join(keys)}) VALUES({','.join('?' * len(keys))})"
        if "id" in cols and row.get("id"):
            sets = ",".join(f"{k}=?" for k in keys if k != "id")
            with self.lock:
                cur = self.db.execute(f"UPDATE {table} SET {sets} WHERE id=?", [row[k] for k in keys if k != "id"] + [row["id"]])
                self.db.commit()
                if cur.rowcount:
                    return row["id"]
        return self.x(sql, [row[k] for k in keys])

    def delete(self, table, key, value):
        assert table in TABLES and key.isidentifier()
        self.x(f"DELETE FROM {table} WHERE {key}=?", (value,))

    def get_setting(self, key, default=None):
        r = self.q("SELECT value FROM settings WHERE key=?", (key,))
        if not r:
            return default
        try:
            return json.loads(r[0]["value"])
        except Exception:
            return r[0]["value"]

    def set_setting(self, key, value):
        self.x("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, json.dumps(value, ensure_ascii=False)))

    def all_settings(self):
        out = {}
        for r in self.q("SELECT key, value FROM settings"):
            try:
                out[r["key"]] = json.loads(r["value"])
            except Exception:
                out[r["key"]] = r["value"]
        return out

    # ---------------------------------------------------------------- privacy PIN (masking private notes)
    def set_pin(self, pin):
        self.set_setting("pin_hash", hashlib.sha256(("ss-" + pin).encode()).hexdigest() if pin else "")

    def check_pin(self, pin):
        h = self.get_setting("pin_hash", "")
        return not h or hashlib.sha256(("ss-" + (pin or "")).encode()).hexdigest() == h

    # ---------------------------------------------------------------- passage annotations
    def annotations_for(self, passage_ids, unlocked=False):
        if not passage_ids:
            return {}
        ph = ",".join("?" * len(passage_ids))
        out = {pid: {"notes": [], "highlights": [], "tags": [], "bookmarked": False} for pid in passage_ids}
        for n in self.q(f"SELECT * FROM notes WHERE passage_id IN ({ph})", passage_ids):
            if n["private"] and not unlocked:
                n["text"] = "🔒 private note"
            out[n["passage_id"]]["notes"].append(n)
        for h in self.q(f"SELECT * FROM highlights WHERE passage_id IN ({ph})", passage_ids):
            out[h["passage_id"]]["highlights"].append(h)
        for t in self.q(f"SELECT * FROM tags WHERE passage_id IN ({ph})", passage_ids):
            out[t["passage_id"]]["tags"].append(t["tag"])
        for b in self.q(f"SELECT passage_id FROM bookmarks WHERE passage_id IN ({ph})", passage_ids):
            out[b["passage_id"]]["bookmarked"] = True
        return out

    def search_notes(self, text, unlocked=False, limit=100):
        like = f"%{text}%"
        notes = self.q("SELECT 'note' AS kind, id, ref, passage_id, text, tags, private FROM notes WHERE text LIKE ? OR tags LIKE ? LIMIT ?",
                       (like, like, limit))
        docs = self.q("SELECT 'doc' AS kind, id, title AS ref, html AS text, tags, private FROM docs WHERE html LIKE ? OR title LIKE ? OR tags LIKE ? LIMIT ?",
                      (like, like, like, limit))
        sheets = self.q("SELECT 'sheet' AS kind, id, title AS ref, items AS text, tags, 0 AS private FROM sheets WHERE items LIKE ? OR title LIKE ? LIMIT ?",
                        (like, like, limit))
        out = []
        for r in notes + docs + sheets:
            if r["private"] and not unlocked:
                continue
            out.append(r)
        return out

    def log_history(self, work_id, title, ref):
        last = self.q("SELECT ref FROM history ORDER BY id DESC LIMIT 1")
        if not last or last[0]["ref"] != ref:
            self.x("INSERT INTO history(work_id,title,ref) VALUES(?,?,?)", (work_id, title, ref))

    def log_search(self, kind, query, opts, hits):
        self.x("INSERT INTO search_history(kind,query,opts,hits) VALUES(?,?,?,?)", (kind, query, json.dumps(opts), hits))

    def log_reading(self, work_id, passages, seconds):
        self.x("INSERT INTO reading_log(work_id,passages,seconds,day) VALUES(?,?,?,date('now','localtime'))", (work_id, passages, seconds))

    def reading_pace(self):
        r = self.q("SELECT SUM(passages) p, SUM(seconds) s, COUNT(DISTINCT day) d FROM reading_log")[0]
        if not r["s"]:
            return {"passages_per_hour": 0, "days": 0, "passages_per_day": 0}
        return {"passages_per_hour": round(r["p"] / (r["s"] / 3600), 1), "days": r["d"],
                "passages_per_day": round(r["p"] / max(1, r["d"]), 1), "total_hours": round(r["s"] / 3600, 1)}

    # ---------------------------------------------------------------- backup / export
    def backup(self, dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        path = os.path.join(dest_dir, f"SeforimStudio-backup-{self.profile}-{stamp}.zip")
        with self.lock:
            self.db.commit()
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
                for f in os.listdir(self.dir):
                    z.write(os.path.join(self.dir, f), "profiles/" + f)
        return path

    def restore(self, zip_path):
        with zipfile.ZipFile(zip_path) as z:
            for name in z.namelist():
                if name.startswith("profiles/") and name.endswith(".sqlite") and "/" not in name[9:] and ".." not in name:
                    target = os.path.join(self.dir, os.path.basename(name))
                    if os.path.exists(target):
                        shutil.copy2(target, target + ".before-restore")
                    with z.open(name) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        self.open(self.profile)
        return True

    def export_all(self):
        return {t: self.q(f"SELECT * FROM {t}") for t in TABLES if t != "settings"}

    def import_all(self, data, merge=True):
        n = 0
        for t, rows in data.items():
            if t not in TABLES or t == "settings":
                continue
            for r in rows:
                if merge and "id" in r:
                    r = dict(r); r.pop("id")
                self.save(t, r); n += 1
        return n
