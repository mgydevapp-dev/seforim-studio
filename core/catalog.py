"""Reads the seforim catalog DB (index of the Sefaria export) and manages the
one-time download + import of texts into the local offline library."""
import json
import os
import shutil
import sqlite3
import threading
import time
import urllib.parse
import urllib.request

from .order import sort_key, he_name


class Catalog:
    def __init__(self, path):
        self.path = path
        self.db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        info = dict(self.q("SELECT key, value FROM export_info", raw=True))
        self.base_url = info.get("base_url", "https://storage.googleapis.com/sefaria-export")
        self.generated_at = info.get("generated_at", "")

    def q(self, sql, args=(), raw=False):
        with self.lock:
            rows = self.db.execute(sql, args).fetchall()
        return [tuple(r) for r in rows] if raw else [dict(r) for r in rows]

    def info(self):
        return {"path": self.path, "generated_at": self.generated_at,
                "works": self.q("SELECT COUNT(*) n FROM works")[0]["n"],
                "texts": self.q("SELECT COUNT(*) n FROM books")[0]["n"],
                "categories": self.q("SELECT COUNT(*) n FROM categories")[0]["n"]}

    def tree(self):
        """Nested category tree with works, sorted traditionally."""
        cats = self.q("SELECT id, name, parent_id, full_path FROM categories")
        works = self.q("""SELECT w.id, w.title, w.category_path,
                    SUM(b.is_merged=1 AND b.language='Hebrew') AS he, SUM(b.is_merged=1 AND b.language='English') AS en,
                    COUNT(b.id) AS versions
                    FROM works w LEFT JOIN books b ON b.work_id=w.id GROUP BY w.id""")
        nodes = {c["full_path"]: {"name": c["name"], "he": he_name(c["name"]), "path": c["full_path"],
                                  "children": [], "works": []} for c in cats}
        roots = []
        for c in cats:
            n = nodes[c["full_path"]]
            parent = c["full_path"].rsplit(" > ", 1)[0] if " > " in c["full_path"] else None
            (nodes[parent]["children"] if parent in nodes else roots).append(n)
        for i, w in enumerate(works):
            node = nodes.get(w["category_path"])
            item = {"id": w["id"], "title": w["title"], "he": he_name(w["title"]), "has_he": bool(w["he"]),
                    "has_en": bool(w["en"]), "versions": w["versions"]}
            if node:
                node["works"].append(item)
            else:
                roots.append({"name": w["category_path"] or "Other", "he": "", "path": w["category_path"], "children": [], "works": [item]})

        def srt(lst):
            lst.sort(key=lambda n: sort_key(n["name"]))
            for n in lst:
                n["works"].sort(key=lambda w: sort_key(w["title"]))
                srt(n["children"])
                n["count"] = len(n["works"]) + sum(ch["count"] for ch in n["children"])
        srt(roots)
        return roots

    def work(self, wid):
        r = self.q("SELECT * FROM works WHERE id=?", (wid,))
        return r[0] if r else None

    def works_in(self, category_paths):
        out = []
        for c in category_paths:
            out += self.q("SELECT id, title, category_path FROM works WHERE category_path=? OR category_path LIKE ?", (c, c + " > %"))
        return out

    def versions(self, wid):
        return self.q("SELECT id, language, version_title, is_merged, json_url FROM books WHERE work_id=? ORDER BY language, is_merged DESC", (wid,))

    def merged_urls(self, wid):
        rows = self.q("SELECT language, json_url, top_category FROM books WHERE work_id=? AND is_merged=1", (wid,))
        return {r["language"]: r["json_url"] for r in rows}, (rows[0]["top_category"] if rows else "")

    def local_path(self, data_dir, url):
        rel = urllib.parse.unquote(url[len(self.base_url):].lstrip("/"))
        return os.path.join(data_dir, "sefaria", *rel.split("/"))

    def schema_path(self, data_dir, title):
        return os.path.join(data_dir, "sefaria", "schemas", title.replace(" ", "_") + ".json")

    def special(self, folder):
        return self.q("SELECT path, url, size_bytes FROM special_files WHERE folder=?", (folder,))

    def search_titles(self, text, limit=50):
        try:
            return self.q("SELECT b.work_id AS id, b.title, b.category_path FROM books_fts f JOIN books b ON b.id=f.rowid "
                          "WHERE books_fts MATCH ? GROUP BY b.work_id LIMIT ?", ('"' + text.replace('"', '') + '"*', limit))
        except sqlite3.OperationalError:
            return self.q("SELECT id, title, category_path FROM works WHERE title LIKE ? LIMIT ?", ("%" + text + "%", limit))


class Downloader:
    """Background one-time downloader + importer.  Only this module touches the internet."""

    def __init__(self, catalog, library, data_dir):
        self.cat, self.lib, self.data_dir = catalog, library, data_dir
        self.state = {"running": False, "done": 0, "total": 0, "current": "", "errors": [], "log": [], "bytes": 0}
        self._stop = False
        self.thread = None

    def _fetch(self, url, dest, retries=3):
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            return dest
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = dest + ".part"
        last = None
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "SeforimStudio/1.0 (offline library setup)"})
                with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
                    while True:
                        chunk = r.read(1 << 16)
                        if not chunk:
                            break
                        f.write(chunk)
                        self.state["bytes"] += len(chunk)
                        if self._stop:
                            raise InterruptedError("stopped")
                os.replace(tmp, dest)
                return dest
            except InterruptedError:
                raise
            except Exception as e:  # noqa
                last = e
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"{url}: {last}")

    def import_from_disk(self, wid):
        """Import one work from files already on disk (downloaded or copied from a Sefaria export)."""
        w = self.cat.work(wid)
        urls, top = self.cat.merged_urls(wid)
        js = {}
        for lang in ("Hebrew", "English"):
            if lang in urls:
                p = self.cat.local_path(self.data_dir, urls[lang])
                if os.path.exists(p):
                    with open(p, encoding="utf-8") as f:
                        js[lang] = json.load(f)
        if not js:
            return 0
        schema = None
        sp = self.cat.schema_path(self.data_dir, w["title"])
        if os.path.exists(sp):
            try:
                with open(sp, encoding="utf-8") as f:
                    schema = json.load(f)
            except Exception:
                schema = None
        if schema:
            self.lib.save_he_title(schema)
        n = self.lib.import_work({"id": wid, "title": w["title"], "category_path": w["category_path"],
                                     "top_category": top or w["category_path"].split(" > ")[0]},
                                    js.get("Hebrew"), js.get("English"), schema)
        self.lib.refresh_he_titles()
        return n

    def start(self, work_ids, include_english=True, include_schemas=True, include_links=False):
        if self.state["running"]:
            return False
        self._stop = False
        self.state.update(running=True, done=0, total=len(work_ids), errors=[], log=[], bytes=0, current="")

        def run():
            try:
                if include_schemas:
                    self.state["current"] = "author/date info"
                    want = {self.cat.work(w)["title"].replace(" ", "_") + ".json" for w in work_ids if self.cat.work(w)}
                    for s in self.cat.special("schemas"):
                        if s["path"].split("/", 1)[1] in want:
                            try:
                                self._fetch(s["url"], os.path.join(self.data_dir, "sefaria", *s["path"].split("/")))
                            except Exception as e:
                                self.state["errors"].append(str(e))
                for wid in work_ids:
                    if self._stop:
                        break
                    w = self.cat.work(wid)
                    self.state["current"] = w["title"]
                    urls, _ = self.cat.merged_urls(wid)
                    try:
                        for lang, url in urls.items():
                            if lang == "English" and not include_english:
                                continue
                            self._fetch(url, self.cat.local_path(self.data_dir, url))
                        n = self.import_from_disk(wid)
                        self.state["log"].append(f"{w['title']}: {n} passages")
                    except InterruptedError:
                        break
                    except Exception as e:
                        self.state["errors"].append(f"{w['title']}: {e}")
                    self.state["done"] += 1
                if include_links and not self._stop:
                    for s in self.cat.special("links"):
                        self.state["current"] = "cross-references " + s["path"]
                        try:
                            p = self._fetch(s["url"], os.path.join(self.data_dir, "sefaria", *s["path"].split("/")))
                            self.lib.import_links_csv(p)
                        except Exception as e:
                            self.state["errors"].append(str(e))
            finally:
                self.state["running"] = False
                self.state["current"] = "finished" if not self._stop else "stopped"

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        return True

    def fetch_titles(self):
        """One-time: download the small schema file of every sefer to get its exact Hebrew title, author and date."""
        if self.state["running"]:
            return False
        self._stop = False
        files = self.cat.special("schemas")
        self.state.update(running=True, done=0, total=len(files), errors=[], log=[], bytes=0, current="Hebrew titles")

        def run():
            import concurrent.futures as cf
            try:
                def one(sf):
                    if self._stop:
                        return
                    dest = os.path.join(self.data_dir, "sefaria", *sf["path"].split("/"))
                    try:
                        self._fetch(sf["url"], dest)
                        with open(dest, encoding="utf-8") as f:
                            self.lib.save_he_title(json.load(f))
                    except Exception as e:  # noqa
                        self.state["errors"].append(f"{sf['path']}: {e}")
                    self.state["done"] += 1
                with cf.ThreadPoolExecutor(8) as ex:
                    list(ex.map(one, files))
                self.lib.db.commit()
                n = self.lib.refresh_he_titles()
                self.state["log"].append(f"{n} Hebrew titles")
            finally:
                self.state["running"] = False
                self.state["current"] = "finished"
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        return True

    def titles_from_disk(self):
        d = os.path.join(self.data_dir, "sefaria", "schemas")
        n = 0
        if os.path.isdir(d):
            for fn in os.listdir(d):
                try:
                    with open(os.path.join(d, fn), encoding="utf-8") as f:
                        self.lib.save_he_title(json.load(f)); n += 1
                except Exception:
                    pass
            self.lib.db.commit()
            self.lib.refresh_he_titles()
        return n

    def import_folder(self, folder):
        """Import from a Sefaria export folder the user already has (copied from a USB drive etc.)."""
        if os.path.abspath(folder) != os.path.abspath(os.path.join(self.data_dir, "sefaria")):
            for sub in ("json", "schemas", "links"):
                src = os.path.join(folder, sub)
                if os.path.isdir(src):
                    shutil.copytree(src, os.path.join(self.data_dir, "sefaria", sub), dirs_exist_ok=True)
        ids = [r["id"] for r in self.cat.q("SELECT id FROM works")]
        n_done = 0
        self.state.update(running=True, total=len(ids), done=0, errors=[], log=[])
        try:
            for wid in ids:
                try:
                    if self.import_from_disk(wid):
                        n_done += 1
                except Exception as e:
                    self.state["errors"].append(f"{wid}: {e}")
                self.state["done"] += 1
            self.titles_from_disk()
            links_dir = os.path.join(self.data_dir, "sefaria", "links")
            if os.path.isdir(links_dir):
                for fn in sorted(os.listdir(links_dir)):
                    if fn.endswith(".csv"):
                        self.lib.import_links_csv(os.path.join(links_dir, fn))
        finally:
            self.state["running"] = False
        return n_done

    def stop(self):
        self._stop = True
