"""Reads the seforim catalog DB (index of the Sefaria export) and manages the
one-time download + import of texts into the local offline library."""
import json
import os
import shutil
import sqlite3
import threading
import time
import urllib.error
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


def long_path(p):
    """Windows normally refuses paths over 260 characters; the long-path prefix lifts that limit."""
    p = os.path.abspath(p)
    if os.name == "nt" and len(p) > 240 and not p.startswith("\\\\?\\"):
        return "\\\\?\\" + p
    return p


class Downloader:
    """Downloads texts straight into the library (in memory - no long file paths on disk).
    Only this module touches the internet."""

    def __init__(self, catalog, library, data_dir):
        self.cat, self.lib, self.data_dir = catalog, library, data_dir
        self.state = {"running": False, "done": 0, "total": 0, "current": "", "errors": [], "log": [], "bytes": 0}
        self._stop = False
        self.thread = None
        self._schema_urls = None

    # ---------------------------------------------------------------- network
    def _get(self, url, retries=4):
        last = None
        for attempt in range(retries):
            if self._stop:
                raise InterruptedError("stopped")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "SeforimStudio/1.0 (offline library setup)"})
                with urllib.request.urlopen(req, timeout=90) as r:
                    data = r.read()
                self.state["bytes"] += len(data)
                return data
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    raise RuntimeError("not found on the server")
                last = e
            except Exception as e:  # noqa
                last = e
            time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"download failed ({last})")

    def _get_json(self, url):
        return json.loads(self._get(url).decode("utf-8"))

    def schema_url(self, title):
        if self._schema_urls is None:
            self._schema_urls = {s["path"].split("/", 1)[1][:-5]: s["url"] for s in self.cat.special("schemas")}
        return self._schema_urls.get(title.replace(" ", "_"))

    # ---------------------------------------------------------------- one work
    def fetch_work(self, wid, include_english=True, include_schema=True):
        """Network part (runs in worker threads): returns parsed JSON for one work."""
        w = self.cat.work(wid)
        urls, top = self.cat.merged_urls(wid)
        js = {}
        problems = []
        for lang, url in urls.items():
            if lang == "English" and not include_english:
                continue
            try:
                js[lang] = self._get_json(url)
            except InterruptedError:
                raise
            except Exception as e:  # noqa - one missing language must not lose the other
                problems.append(f"{lang}: {e}")
        if not js:
            raise RuntimeError("; ".join(problems) or "no text available")
        schema = None
        if include_schema:
            su = self.schema_url(w["title"])
            if su:
                try:
                    schema = self._get_json(su)
                except Exception:
                    schema = None
        return w, top, js, schema

    def store_work(self, wid, w, top, js, schema):
        """Database part (single thread)."""
        if not js:
            return 0
        if schema:
            self.lib.save_he_title(schema)
        return self.lib.import_work({"id": wid, "title": w["title"], "category_path": w["category_path"],
                                     "top_category": top or w["category_path"].split(" > ")[0]},
                                    js.get("Hebrew"), js.get("English"), schema)

    def import_from_disk(self, wid, root=None):
        """Import one work from a Sefaria export folder on disk (e.g. copied from a USB drive)."""
        root = root or os.path.join(self.data_dir, "sefaria")
        w = self.cat.work(wid)
        urls, top = self.cat.merged_urls(wid)
        js = {}
        for lang, url in urls.items():
            rel = urllib.parse.unquote(url[len(self.cat.base_url):].lstrip("/"))
            p = long_path(os.path.join(root, *rel.split("/")))
            if os.path.exists(p):
                with open(p, encoding="utf-8") as f:
                    js[lang] = json.load(f)
        schema = None
        sp = long_path(os.path.join(root, "schemas", w["title"].replace(" ", "_") + ".json"))
        if os.path.exists(sp):
            try:
                with open(sp, encoding="utf-8") as f:
                    schema = json.load(f)
            except Exception:
                schema = None
        return self.store_work(wid, w, top, js, schema)

    # ---------------------------------------------------------------- batch
    def run_all(self, work_ids, include_english=True, include_links=False, include_titles=False, workers=8, progress=None):
        """Synchronous download + import (used by the background thread and by the pre-build script)."""
        import concurrent.futures as cf
        self.state.update(done=0, total=len(work_ids), errors=[], log=[], bytes=0)
        if include_titles:
            self._titles(workers, progress)
        ids = list(work_ids)
        with cf.ThreadPoolExecutor(workers) as ex:
            pending = {}
            it = iter(ids)
            def submit():
                try:
                    wid = next(it)
                except StopIteration:
                    return False
                pending[ex.submit(self.fetch_work, wid, include_english)] = wid
                return True
            for _ in range(workers * 2):
                if not submit():
                    break
            while pending and not self._stop:
                done, _ = cf.wait(list(pending), return_when=cf.FIRST_COMPLETED)
                for fut in done:
                    wid = pending.pop(fut)
                    try:
                        w, top, js, schema = fut.result()
                        self.state["current"] = w["title"]
                        n = self.store_work(wid, w, top, js, schema)
                        self.state["log"].append(f"{w['title']}: {n}")
                    except InterruptedError:
                        pass
                    except Exception as e:  # noqa
                        t = (self.cat.work(wid) or {}).get("title", wid)
                        self.state["errors"].append(f"{t}: {e}")
                    self.state["done"] += 1
                    if progress:
                        progress(self.state)
                    submit()
        self.lib.refresh_he_titles()
        if include_links and not self._stop:
            self._links(progress)
        return self.state

    def _titles(self, workers=8, progress=None):
        import concurrent.futures as cf
        files = self.cat.special("schemas")
        self.state["current"] = "Hebrew titles"
        def one(sf):
            if self._stop:
                return None
            try:
                return self._get_json(sf["url"])
            except Exception as e:  # noqa
                self.state["errors"].append(f"{sf['path']}: {e}")
                return None
        n = 0
        with cf.ThreadPoolExecutor(workers) as ex:
            for meta in ex.map(one, files):
                if meta:
                    self.lib.save_he_title(meta)
                    n += 1
                    if n % 500 == 0 and progress:
                        self.state["current"] = f"Hebrew titles {n}/{len(files)}"
                        progress(self.state)
        self.lib.db.commit()
        self.lib.refresh_he_titles()
        self.state["log"].append(f"{n} Hebrew titles")
        return n

    def _links(self, progress=None):
        import tempfile
        for s in self.cat.special("links"):
            if self._stop:
                break
            self.state["current"] = "cross-references " + s["path"]
            if progress:
                progress(self.state)
            try:
                data = self._get(s["url"])
                fd, tmp = tempfile.mkstemp(suffix=".csv")
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
                del data
                self.lib.import_links_csv(tmp)
                os.remove(tmp)
            except Exception as e:  # noqa
                self.state["errors"].append(f"{s['path']}: {e}")

    def _thread(self, fn, *args, **kw):
        if self.state["running"]:
            return False
        self._stop = False
        self.state.update(running=True, done=0, total=0, errors=[], log=[], bytes=0, current="starting")

        def run():
            try:
                fn(*args, **kw)
            except Exception as e:  # noqa
                self.state["errors"].append(str(e))
            finally:
                self.state["running"] = False
                self.state["current"] = "stopped" if self._stop else "finished"
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        return True

    def start(self, work_ids, include_english=True, include_schemas=True, include_links=False):
        return self._thread(self.run_all, work_ids, include_english, include_links, False)

    def fetch_titles(self):
        def go():
            self.state["total"] = len(self.cat.special("schemas"))
            self._titles()
            self.state["done"] = self.state["total"]
        return self._thread(go)

    def import_folder(self, folder):
        """Import from a Sefaria export folder the user already has (copied from a USB drive etc.)."""
        ids = [r["id"] for r in self.cat.q("SELECT id FROM works")]
        n_done = 0
        self.state.update(running=True, total=len(ids), done=0, errors=[], log=[])
        try:
            for wid in ids:
                try:
                    if self.import_from_disk(wid, folder):
                        n_done += 1
                except Exception as e:  # noqa
                    self.state["errors"].append(f"{wid}: {e}")
                self.state["done"] += 1
            sd = os.path.join(folder, "schemas")
            if os.path.isdir(sd):
                for fn in os.listdir(sd):
                    try:
                        with open(long_path(os.path.join(sd, fn)), encoding="utf-8") as f:
                            self.lib.save_he_title(json.load(f))
                    except Exception:
                        pass
                self.lib.db.commit()
            self.lib.refresh_he_titles()
            links_dir = os.path.join(folder, "links")
            if os.path.isdir(links_dir):
                for fn in sorted(os.listdir(links_dir)):
                    if fn.endswith(".csv"):
                        self.lib.import_links_csv(long_path(os.path.join(links_dir, fn)))
        finally:
            self.state["running"] = False
        return n_done

    def stop(self):
        self._stop = True
