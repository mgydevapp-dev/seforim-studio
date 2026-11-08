"""Local offline server for the Seforim Studio window.  Listens on 127.0.0.1 only (plus an optional
LAN share listener that accepts nothing but incoming share packages with a pairing code)."""
import datetime as dt
import glob
import importlib.util
import json
import mimetypes
import os
import re
import secrets
import shutil
import threading
import time
import traceback
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import formats as F
from . import hcalendar as C
from . import hebrew as H
from . import tools as TL
from . import winproc
from .catalog import Catalog, Downloader
from .data_tables import PARSHIYOS, HOLIDAY_TEXTS, PLACES, ERAS
from .library import Library
from .share import ShareHub, local_ips, bluetooth_send, bluetooth_receive
from .userdata import UserData

APP_VERSION = "1.0.0"
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/ttf", ".ttf")
mimetypes.add_type("text/javascript", ".js")


class Jobs:
    def __init__(self):
        self.jobs = {}

    def start(self, fn, *args, **kw):
        jid = uuid.uuid4().hex[:8]
        job = {"id": jid, "done": False, "progress": 0, "total": 0, "label": "", "result": None, "error": None, "cancel": False}
        self.jobs[jid] = job

        def prog(i, n, label=""):
            job["progress"], job["total"], job["label"] = i, n, label

        def run():
            try:
                job["result"] = fn(*args, progress=prog, cancel=lambda: job["cancel"], **kw)
            except Exception as e:  # noqa
                job["error"] = str(e)
                traceback.print_exc()
            finally:
                job["done"] = True
        threading.Thread(target=run, daemon=True).start()
        return jid

    def status(self, jid):
        j = self.jobs.get(jid)
        return {k: v for k, v in j.items() if k != "cancel"} if j else {"error": "unknown job", "done": True}


class App:
    def __init__(self, base_dir, data_dir=None):
        self.base = base_dir
        self.data = data_dir or os.path.join(base_dir, "data")
        self.web = os.path.join(base_dir, "web")
        for d in ("exports", "scans", "uploads", "profiles", "inbox", "fonts", "backups", "plugins"):
            os.makedirs(os.path.join(self.data, d), exist_ok=True)
        self.token = secrets.token_urlsafe(16)
        self.jobs = Jobs()
        self.lib = Library(os.path.join(self.data, "library.sqlite"))
        self.user = UserData(os.path.join(self.data, "profiles"), self._last_profile())
        self.catalog = None
        # Prefer the catalog inside the data folder, so the portable folder can be moved to another computer.
        for cat_path in (os.path.join(self.data, "seforim_catalog.db"), self.user.get_setting("catalog_path") or ""):
            if cat_path and os.path.exists(cat_path):
                try:
                    self.load_catalog(cat_path)
                    break
                except Exception as e:  # noqa
                    print("catalog problem:", e)
        self.share = ShareHub(os.path.join(self.data, "inbox"))
        self.share_server = None
        self.last_ping = time.time()
        self._load_plugins()
        self.install = {"state": "idle", "progress": 0, "message": ""}
        self.ai = {"state": "idle", "progress": 0, "message": ""}
        self.ollama_proc = None
        self.check_library_install()
        self.check_ai_install()
        self.start_bundled_ollama()

    # ------------------------------------------------------------------ bundled AI reader (Ollama + model)
    def ai_dir(self):
        return os.path.join(self.data, "ai")

    def bundled_ollama(self):
        for name in ("ollama.exe", "ollama"):
            p = os.path.join(self.ai_dir(), "ollama", name)
            if os.path.exists(p):
                return p
        return None

    def start_bundled_ollama(self):
        """Start the AI reader that ships with the app (only if no Ollama is already running)."""
        exe = self.bundled_ollama()
        if not exe:
            return False
        from scanner.engines import OllamaEngine
        if OllamaEngine().models() is not None:
            return True  # an Ollama is already running (bundled or the user's own)
        env = dict(os.environ)
        env["OLLAMA_MODELS"] = os.path.join(self.ai_dir(), "models")
        env["OLLAMA_HOST"] = "127.0.0.1:11434"
        env.setdefault("OLLAMA_KEEP_ALIVE", "15m")
        try:
            self.ollama_proc = winproc.popen([exe, "serve"], hidden=True, env=env, cwd=os.path.dirname(exe))
            for _ in range(40):
                time.sleep(0.5)
                if OllamaEngine().models() is not None:
                    print("Bundled AI reader started")
                    return True
        except Exception as e:  # noqa
            print("Could not start the bundled AI reader:", e)
        return False

    def check_ai_install(self, extra_dir=None):
        from . import installer
        found = installer.scan(installer.search_dirs(os.path.dirname(self.data), self.data, extra_dir), installer.PACKS["ai"])
        parts = found["parts"]
        if not parts:
            if found["problem"]:
                self.ai.update(state="incomplete", message=found["problem"])
            return self.ai
        need, free = installer.free_space(parts, self.data, ratio=1.05)
        if free < need and not installer.already_installed(self.data, parts, "ai"):
            self.ai.update(state="error", message=f"Not enough free disk space for the AI pack: needs about {need / 1e9:.0f} GB, "
                           f"the drive has {free / 1e9:.1f} GB.")
            return self.ai
        if installer.already_installed(self.data, parts, "ai") or self.ai["state"] == "running":
            return self.ai
        self.ai.update(state="running", progress=0, message="Installing the AI handwriting reader (one time)…")

        def run():
            try:
                tmp = self.ai_dir() + ".installing"
                if os.path.isdir(tmp):
                    shutil.rmtree(tmp, ignore_errors=True)
                installer.extract_tar(parts, tmp, lambda x: self.ai.update(progress=round(x * 98, 1)))
                src = os.path.join(tmp, "ai") if os.path.isdir(os.path.join(tmp, "ai")) else tmp
                if self.ollama_proc:
                    self.ollama_proc.terminate()
                if os.path.isdir(self.ai_dir()):
                    shutil.rmtree(self.ai_dir(), ignore_errors=True)
                shutil.move(src, self.ai_dir())
                shutil.rmtree(tmp, ignore_errors=True)
                installer.mark_installed(self.data, parts, "ai")
                self._cleanup_parts(parts)
                started = self.start_bundled_ollama()
                self.ai.update(state="done", progress=100,
                               message="AI handwriting reader installed" + (" and running" if started else " (it starts with the app)"))
            except Exception as e:  # noqa
                traceback.print_exc()
                self.ai.update(state="error", message=f"Could not install the AI reader: {e}")
        threading.Thread(target=run, daemon=True).start()
        return self.ai

    def api_ai_status(self, a):
        return {**self.ai, "bundled": bool(self.bundled_ollama()), "running": self.ollama_proc is not None and self.ollama_proc.poll() is None}

    def api_ai_check(self, a):
        r = self.check_ai_install(a.get("folder"))
        if r["state"] != "running" and self.bundled_ollama():
            self.start_bundled_ollama()
        return r

    # ------------------------------------------------------------------ pre-built library install
    def check_library_install(self, extra_dir=None):
        from . import installer
        app_dir = os.path.dirname(self.data)
        if self.install["state"] == "running":
            return self.install
        if extra_dir:
            self._extra_dir = extra_dir  # remember the folder the user typed
        dirs = installer.search_dirs(app_dir, self.data, extra_dir or getattr(self, "_extra_dir", None))
        found = installer.scan(dirs)
        parts = found["parts"]
        if not parts:
            if found["problem"]:
                self.install.update(state="incomplete", message=found["problem"])
            elif self.install["state"] != "done":
                self.install.update(state="missing", message="The library files (SeforimLibrary.sqlite.xz.part1of2 and part2of2) "
                                    "were not found. Looked in: " + "; ".join(dirs[:8]))
            return self.install
        if installer.already_installed(self.data, parts) and self._library_complete():
            return self.install
        need, free = installer.free_space(parts, self.data)
        if free < need:
            self.install.update(state="error", message=f"Not enough free disk space to unpack the library: it needs about "
                                f"{need / 1e9:.0f} GB free, and the drive with {self.data} has {free / 1e9:.1f} GB. "
                                f"Free up space (or move the whole SeforimStudio folder to a bigger drive) and press Install again.")
            return self.install
        self.install.update(state="running", progress=0, message="Installing the seforim library (one time)…",
                            files=[os.path.basename(p) for p in parts])

        def run():
            path = os.path.join(self.data, "library.sqlite")
            tmp = path + ".installing"
            try:
                for f in (tmp, tmp + "-wal", tmp + "-shm"):
                    if os.path.exists(f):
                        os.remove(f)
                n = installer.decompress(parts, tmp, lambda x: self.install.update(progress=round(x * 95, 1)))
                self.install.update(progress=96, message="Keeping the seforim you added yourself…")
                new_lib = Library(tmp)
                kept = installer.copy_user_works(path, new_lib)
                new_lib.db.close()
                with self.lib.lock:
                    self.lib.db.close()
                    for f in (path + "-wal", path + "-shm"):
                        if os.path.exists(f):
                            os.remove(f)
                    os.replace(tmp, path)
                    for f in (tmp + "-wal", tmp + "-shm"):
                        if os.path.exists(f):
                            os.remove(f)
                    self.lib = Library(path)
                    if self.catalog:
                        self.dl.lib = self.lib
                installer.mark_installed(self.data, parts)
                self._cleanup_parts(parts)
                self.install.update(state="done", progress=100, message=f"Library installed: {n:,} seforim" + (f" (kept {kept} of your own)" if kept else ""))
            except Exception as e:  # noqa
                traceback.print_exc()
                self.install.update(state="error", message=f"Could not install the library: {e}")
        threading.Thread(target=run, daemon=True).start()
        return self.install

    def _library_complete(self):
        """True when (almost) every sefer of the catalog has its text in the library."""
        if not self.catalog:
            return True
        have = self.lib.q1("SELECT COUNT(*) n FROM works WHERE n_passages>0")["n"]
        return have >= 0.95 * self.catalog.info()["works"]

    def api_library_health(self, a):
        """Per section of the library: how many seforim the catalog has and how many are installed with text."""
        if not self.catalog:
            return {"rows": [], "total": 0, "have": 0, "install": self.install}
        cat = {r["top"]: r["n"] for r in self.catalog.q(
            "SELECT CASE WHEN instr(category_path,' > ')>0 THEN substr(category_path,1,instr(category_path,' > ')-1) "
            "ELSE category_path END AS top, COUNT(*) n FROM works GROUP BY top")}
        ids = {r["id"]: r for r in self.catalog.q("SELECT id, category_path FROM works")}
        have = {}
        for r in self.lib.q("SELECT id FROM works WHERE n_passages>0"):
            c = ids.get(r["id"])
            if c:
                top = c["category_path"].split(" > ")[0]
                have[top] = have.get(top, 0) + 1
        from .order import he_name
        rows = [{"name": k, "he": he_name(k), "total": v, "have": have.get(k, 0)} for k, v in cat.items()]
        rows.sort(key=lambda r: -r["total"])
        if self.install["state"] in ("idle", "missing", "incomplete", "error"):
            self.check_library_install()
        return {"rows": rows, "total": sum(cat.values()), "have": sum(have.values()), "install": self.install,
                "online_download": self.dl.state.get("running", False) if self.dl else False}

    def _cleanup_parts(self, parts):
        """Remove part files that Setup copied INTO the app folder (never touches the user's Downloads)."""
        app_dir = os.path.abspath(os.path.dirname(self.data))
        for p in parts:
            if os.path.dirname(os.path.abspath(p)) in (app_dir, os.path.abspath(self.data)):
                try:
                    os.remove(p)
                except OSError:
                    pass

    def api_install_status(self, a):
        return self.install

    def api_install_check(self, a):
        return self.check_library_install(a.get("folder"))

    def _last_profile(self):
        p = os.path.join(self.data, "profiles", "_last.txt")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return f.read().strip() or "Default"
        return "Default"

    def load_catalog(self, path):
        self.catalog = Catalog(path)
        self.dl = Downloader(self.catalog, self.lib, self.data)
        self.user.set_setting("catalog_path", path)

    def _load_plugins(self):
        """Plugins: any .py file in data/plugins can register extra tools with core.tools.tool(...)."""
        self.plugins = []
        for p in glob.glob(os.path.join(self.data, "plugins", "*.py")):
            try:
                spec = importlib.util.spec_from_file_location("plugin_" + os.path.basename(p)[:-3], p)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                self.plugins.append(os.path.basename(p))
            except Exception as e:  # noqa
                self.plugins.append(f"{os.path.basename(p)} (error: {e})")

    # ------------------------------------------------------------------ helpers
    def export_path(self, name):
        safe = re.sub(r'[\\/:*?"<>|]+', "_", name).strip() or "export"
        return os.path.join(self.data, "exports", safe)

    def file_url(self, path):
        rel = os.path.relpath(path, self.data).replace(os.sep, "/")
        return "/files/" + urllib.parse.quote(rel)

    def scope_with_hidden(self, scope):
        scope = dict(scope or {})
        hidden = [r["work_id"] for r in self.user.list("hidden")]
        if hidden:
            scope["exclude_works"] = list(set((scope.get("exclude_works") or []) + hidden))
        return scope

    # ------------------------------------------------------------------ API methods (name -> api_<name>)
    def api_ping(self, a):
        self.last_ping = time.time()
        return {"ok": True}

    def api_status(self, a):
        s = {"version": APP_VERSION, "library": self.lib.stats(), "profile": self.user.profile,
             "profiles": self.user.profiles(), "settings": self.user.all_settings(), "tools": len(TL.TOOLS),
             "catalog": self.catalog.info() if self.catalog else None, "plugins": self.plugins,
             "share": {"enabled": self.share.enabled, "code": self.share.code, "ips": local_ips(),
                       "port": self.share_server.server_address[1] if self.share_server else None, "name": self.share.name},
             "data_dir": self.data, "pin_set": bool(self.user.get_setting("pin_hash")), "install": self.install, "ai": self.ai}
        s["settings"].pop("pin_hash", None)
        return s

    # ---- catalog / library browsing
    def api_catalog_tree(self, a):
        if not self.catalog:
            return {"tree": [], "imported": []}
        return {"tree": self.catalog.tree(), "imported": [w["id"] for w in self.lib.q("SELECT id FROM works")],
                "favorites": [r["work_id"] for r in self.user.list("favorites")],
                "hidden": [r["work_id"] for r in self.user.list("hidden")]}

    def api_catalog_search(self, a):
        return self.catalog.search_titles(a.get("text", "")) if self.catalog else []

    def api_lib_works(self, a):
        return self.lib.works()

    def api_lib_toc(self, a):
        w = self.lib.work(a["work_id"])
        return {"work": w, "toc": self.lib.toc(a["work_id"])}

    def api_lib_chapter(self, a):
        rows = self.lib.chapter(a["work_id"], a.get("node", ""), a.get("chapter", ""))
        if a.get("all"):
            rows = self.lib.passages_range(a["work_id"], a.get("from_seq", 1), a.get("count", 400))
        ann = self.user.annotations_for([r["id"] for r in rows], a.get("unlocked", False))
        w = self.lib.work(a["work_id"])
        if rows and w:
            self.user.log_history(w["id"], w["title"], rows[0]["ref"])
        links = {}
        for r in rows[:300]:
            n = self.lib.q1("SELECT COUNT(*) n FROM links WHERE ref1=? OR ref2=?", (r["ref"], r["ref"]))["n"]
            if n:
                links[r["id"]] = n
        return {"passages": rows, "annotations": {str(k): v for k, v in ann.items()}, "links": {str(k): v for k, v in links.items()}}

    def api_find_ref(self, a):
        return self.lib.find_ref(a["ref"])

    def api_passage(self, a):
        return self.lib.passage(a["id"])

    def api_connections(self, a):
        out = self.lib.connections(a["ref"])
        for ul in self.user.q("SELECT * FROM user_links WHERE ref_a=? OR ref_b=?", (a["ref"], a["ref"])):
            other = ul["ref_b"] if ul["ref_a"] == a["ref"] else ul["ref_a"]
            hit = self.lib.find_ref(other)
            texts = [self.lib.passage(hit["id"])] if hit else []
            out.insert(0, {"title": "My links", "local": bool(texts), "items": [{"ref": other, "type": ul["label"] or "my link", "texts": texts}]})
        return out

    def api_reading_log(self, a):
        self.user.log_reading(a.get("work_id"), a.get("passages", 0), a.get("seconds", 0))
        return {"ok": True}

    # ---- search
    def api_search(self, a):
        opts = a.get("opts") or {}
        scope = self.scope_with_hidden(a.get("scope"))
        res = self.lib.search(a.get("q", ""), a.get("lang", "auto"), opts, scope, a.get("offset", 0), a.get("limit", 50), a.get("sort", "book"))
        if opts.get("notes") and not a.get("offset"):
            res["notes"] = self.user.search_notes(H.letters_only(a.get("q", "")) or a.get("q", ""), a.get("unlocked", False))
        if opts.get("cross_line") and not a.get("offset") and H.detect_lang(a.get("q", "")) == "he":
            res["cross_line"] = self.lib.cross_line_phrase(a.get("q", "").strip('"'), scope)
        if not a.get("offset"):
            self.user.log_search("search", a.get("q", ""), {"opts": opts, "scope": a.get("scope"), "lang": a.get("lang")}, res.get("total", 0))
        return res

    def api_cross_lingual(self, a):
        """English term -> the Hebrew words that most often stand behind it in translated passages
        (prefix forms grouped: האור, לאור → אור; words common everywhere are down-weighted)."""
        import math
        from collections import Counter
        res = self.lib.search(a["q"], "en", {}, self.scope_with_hidden(a.get("scope")), 0, 1500)
        n = len(res["results"])
        if not n:
            return []
        known = lambda w: self.lib.q1("SELECT 1 AS x FROM words WHERE word=?", (w,)) is not None
        cache = {}

        def base(w):
            if w in cache:
                return cache[w]
            out = w
            for k in (3, 2, 1):
                if len(w) - k >= 2 and all(c in "והבכלמש" for c in w[:k]) and known(w[k:]):
                    out = w[k:]
                    break
            cache[w] = out
            return out
        allw = {w for r in res["results"] for w in H.plain_words(r["he"])}
        support = Counter()
        for w in allw:
            for k in (1, 2, 3):
                if len(w) - k >= 2 and all(ch in "והבכלמש" for ch in w[:k]):
                    support[w[k:]] += 1
        for w in allw:  # a stem seen with 2+ different prefixes counts as the base word
            for k in (3, 2, 1):
                if w not in cache and len(w) - k >= 2 and all(ch in "והבכלמש" for ch in w[:k]) and support[w[k:]] >= 2:
                    cache[w] = w[k:]
        c = Counter()
        for r in res["results"]:
            c.update({base(w) for w in H.plain_words(r["he"])})
        total = self.lib.q1("SELECT COUNT(*) n FROM passages WHERE he_plain != ''")["n"] or 1
        scored = []
        for w, k in c.most_common(80):
            if len(w) < 2 or k < max(1, n * 0.05):
                continue
            df = self.lib.q1("SELECT COUNT(*) n FROM fts_he WHERE fts_he MATCH ?", ("{he_plain} : " + " OR ".join(
                '"%s"' % x for x in [w] + [p + w for p in ("ה", "ו", "ב", "ל", "מ", "וה", "וב", "ול", "כ", "ש")]),))["n"]
            scored.append((w, k, (k / n) * math.log(1 + total / max(1, df))))
        scored.sort(key=lambda x: -x[2])
        return [[w, k] for w, k, _ in scored[:15]]

    def api_search_compare(self, a):
        return self.lib.search_compare(a["q"], a.get("scope_a"), a.get("scope_b"), a.get("lang", "auto"), a.get("opts"))

    def api_search_history(self, a):
        return self.user.list("search_history", limit=200)

    # ---- gematria & letters
    def api_gematria_value(self, a):
        t = a.get("text", "")
        return {"methods": {m: f(t) for m, f in H.GEMATRIA_METHODS.items()}, "words": [[w, H.g_standard(w)] for w in H.plain_words(t)]}

    def api_gematria_words(self, a):
        v = a.get("value")
        m = a.get("method") or "Standard (Mispar Hechrachi)"
        if v in (None, ""):
            v = H.GEMATRIA_METHODS[m](a.get("text", ""))
        v = int(v)
        words = self.lib.gematria_words(v, m, a.get("limit", 500))
        return {"value": v, "words": words}

    def api_gematria_passages(self, a):
        return self.lib.passages_with_words(a.get("words", []), self.scope_with_hidden(a.get("scope")), a.get("offset", 0), a.get("limit", 50))

    def api_gematria_phrases(self, a):
        v = int(a["value"]) if str(a.get("value", "")).strip() else H.GEMATRIA_METHODS[a.get("method") or "Standard (Mispar Hechrachi)"](a.get("text", ""))
        return {"job": self.jobs.start(self.lib.gematria_phrases, v, a.get("method") or "Standard (Mispar Hechrachi)",
                                       int(a.get("min_words", 2)), int(a.get("max_words", 4)), self.scope_with_hidden(a.get("scope")), 500)}

    def api_roshei(self, a):
        res = self.lib.roshei_teivos(a.get("letters", ""), a.get("mode", "roshei"), self.scope_with_hidden(a.get("scope")),
                                     a.get("limit", 100), a.get("offset", 0))
        self.user.log_search("roshei", a.get("letters", ""), {"mode": a.get("mode")}, res["total"])
        return res

    def api_els(self, a):
        def run(progress=None, cancel=None):
            return self.lib.els(a["word"], int(a["work_id"]), int(a.get("min", 2)), int(a.get("max", 300)), 200, cancel)
        return {"job": self.jobs.start(run)}

    def api_job(self, a):
        return self.jobs.status(a["id"])

    def api_job_cancel(self, a):
        j = self.jobs.jobs.get(a["id"])
        if j:
            j["cancel"] = True
        return {"ok": True}

    # ---- analysis
    def api_work_stats(self, a): return self.lib.work_stats(a["work_id"])
    def api_cooccurrence(self, a): return self.lib.cooccurrence(a["a"], a["b"], self.scope_with_hidden(a.get("scope")))
    def api_word_cloud(self, a): return self.lib.word_cloud(a["q"], a.get("lang", "auto") if a.get("lang") != "auto" else H.detect_lang(a["q"]), self.scope_with_hidden(a.get("scope")), a.get("opts"))
    def api_histogram(self, a):
        return {"categories": self.lib.category_histogram(a["q"], a.get("lang", "auto"), a.get("opts")),
                "eras": self.lib.era_histogram(a["q"], a.get("lang", "auto"), a.get("opts"))}
    def api_network(self, a): return self.lib.citation_network(a.get("limit", 40))
    def api_compare_refs(self, a): return self.lib.compare_versions(a.get("refs", []))

    def api_timeline(self, a):
        rows = self.lib.q("SELECT id, title, he_title, authors, he_authors, comp_date, era, comp_place, category_path FROM works WHERE comp_date != ''")
        out = []
        for r in rows:
            m = re.match(r"^(-?\d+)", str(r["comp_date"]))
            if m:
                r["year"] = int(m.group(1)); out.append(r)
        return {"works": sorted(out, key=lambda r: r["year"]), "eras": ERAS, "places": PLACES}

    def api_abbrevs(self, a):
        from .data_tables import ABBREV_CLEAN
        return ABBREV_CLEAN

    def api_reference_data(self, a):
        return {"parshiyos": PARSHIYOS, "holiday_texts": HOLIDAY_TEXTS, "places": PLACES, "eras": ERAS}

    # ---- tools & calendar
    def api_tools(self, a): return TL.tool_list()

    def api_tool_run(self, a):
        r = TL.run_tool(a["id"], a.get("args"), {"library": self.lib, "user": self.user})
        return {"result": r}

    def api_dashboard(self, a):
        d = dt.date.fromisoformat(a["date"]) if a.get("date") else dt.date.today()
        s = self.user.all_settings()
        lat, lon, tz = float(s.get("lat", 40.744)), float(s.get("lon", -73.482)), float(s.get("tz", -5))
        y, m, dd = C.greg_to_heb(d)
        z = C.zmanim(d, lat, lon, tz, int(s.get("candle_minutes", 18)))
        nxt = []
        for g, en, he in C.holidays(y) + C.holidays(y + 1):
            if g >= d and len(nxt) < 8:
                nxt.append({"date": g.isoformat(), "en": en, "he": he, "days": (g - d).days,
                            "texts": next((v for k, v in HOLIDAY_TEXTS.items() if en.startswith(k)), [])})
        daf = C.daf_yomi(d)
        goals = self.user.list("goals")
        pace = self.user.reading_pace()
        for g in goals:
            try:
                end = dt.date.fromisoformat(g["end_date"]); days_left = max(1, (end - d).days)
                g["per_day"] = round(max(0, (g["total"] or 0) - (g["done"] or 0)) / days_left, 1)
                g["days_left"] = days_left
                g["eta_days"] = round(((g["total"] or 0) - (g["done"] or 0)) / pace["passages_per_day"], 1) if pace.get("passages_per_day") else None
            except Exception:
                pass
        return {"date": d.isoformat(), "hebrew": C.format_hebrew(y, m, dd), "hebrew_en": C.format_hebrew(y, m, dd, False),
                "weekday": C.DAYS_EN[C.weekday_index(d)], "parasha": C.parasha(d, bool(s.get("israel"))),
                "parasha_he": C.parasha(d, bool(s.get("israel")), True),
                "daf": {"masechta": daf[0], "daf": daf[1], "he": daf[2], "ref": f"{daf[0]} {daf[1]}a"},
                "omer": C.omer_text(C.omer_day(d)), "today_holidays": C.holiday_on(d, bool(s.get("israel"))),
                "upcoming": nxt, "zmanim": {k: (v.strftime("%I:%M %p").lstrip("0") if isinstance(v, dt.datetime) else str(v)) for k, v in z.items()},
                "sunrise": z.get("Netz / Sunrise").isoformat() if isinstance(z.get("Netz / Sunrise"), dt.datetime) else None,
                "sunset": z.get("Shkia / Sunset").isoformat() if isinstance(z.get("Shkia / Sunset"), dt.datetime) else None,
                "goals": goals, "pace": pace, "location": {"lat": lat, "lon": lon, "tz": tz, "name": s.get("location_name", "Bethpage, NY")},
                "history": self.user.list("history", limit=8), "year": C.year_info(y) | {"rosh_hashana": str(C.year_info(y)["rosh_hashana"])}}

    def api_month(self, a):
        d = dt.date.fromisoformat(a.get("date") or dt.date.today().isoformat()).replace(day=1)
        start = d - dt.timedelta(days=C.weekday_index(d))
        days = []
        cur = start
        while len(days) < 42:
            y, m, dd = C.greg_to_heb(cur)
            days.append({"date": cur.isoformat(), "day": cur.day, "in_month": cur.month == d.month, "heb_day": H.int_to_hebrew(dd),
                         "heb_month": C.month_name(m, y, True), "heb_first": dd == 1, "holidays": C.holiday_on(cur, bool(self.user.get_setting("israel"))),
                         "parasha": C.parasha(cur) if C.weekday_index(cur) == 6 else "", "daf": C.daf_yomi(cur)[2]})
            cur += dt.timedelta(days=1)
        y, m, _ = C.greg_to_heb(d)
        return {"title": d.strftime("%B %Y"), "heb_title": f"{C.month_name(m, y, True)} {H.int_to_hebrew(y)}", "days": days}

    # ---- user data
    def api_ud_list(self, a):
        t = a["table"]
        where, args = "", ()
        if a.get("where") in ("folder", "kind", "work_id", "passage_id", "ref"):
            where, args = f"{a['where']}=?", (a.get("value"),)
        rows = self.user.list(t, where, args, a.get("order", "rowid DESC"), a.get("limit", 1000))
        if t in ("notes", "docs") and not a.get("unlocked"):
            for r in rows:
                if r.get("private"):
                    r["text"] = r.get("text") and "🔒 private"
                    r["html"] = r.get("html") and "<p>🔒 This is private. Unlock with your PIN.</p>"
        return rows

    def api_ud_get(self, a):
        rows = self.user.q(f"SELECT * FROM {a['table']} WHERE id=?", (a["id"],)) if a["table"] in ("docs", "sheets", "covers", "notes", "goals", "transcriptions") else []
        r = rows[0] if rows else None
        if r and r.get("private") and not self.user.check_pin(a.get("pin")):
            return {"locked": True, "id": r["id"], "title": r.get("title")}
        return r

    def api_ud_save(self, a):
        return {"id": self.user.save(a["table"], a["row"])}

    def api_ud_delete(self, a):
        self.user.delete(a["table"], a.get("key", "id"), a["value"])
        return {"ok": True}

    def api_setting(self, a):
        if "value" in a:
            self.user.set_setting(a["key"], a["value"])
        return {"value": self.user.get_setting(a["key"])}

    def api_pin(self, a):
        if a.get("action") == "set":
            if not self.user.check_pin(a.get("old", "")):
                return {"ok": False, "error": "Old PIN is wrong"}
            self.user.set_pin(a.get("pin", ""))
            return {"ok": True}
        return {"ok": self.user.check_pin(a.get("pin", ""))}

    def api_profile(self, a):
        name = re.sub(r"[^\w \-א-ת]", "", a.get("name", "")).strip() or "Default"
        self.user.open(name)
        with open(os.path.join(self.data, "profiles", "_last.txt"), "w", encoding="utf-8") as f:
            f.write(name)
        return {"profile": name, "profiles": self.user.profiles()}

    def api_backup(self, a):
        p = self.user.backup(a.get("dir") or os.path.join(self.data, "backups"))
        return {"path": p, "url": self.file_url(p) if p.startswith(self.data) else None}

    def api_restore(self, a):
        return {"ok": self.user.restore(self._upload_path(a["upload"]))}

    def api_make_bundle(self, a):
        """Make ONE zip with everything (app + library + AI reader + fonts + notes) to copy to an offline computer."""
        import zipfile
        app_dir = os.path.dirname(os.path.abspath(self.data))
        dest = a.get("dest") or os.path.join(os.path.expanduser("~"), "Desktop", "SeforimStudio-Complete.zip")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        skip_dirs = {os.path.join(self.data, d) for d in ("window_profile", "uploads", "scans", "exports", "inbox", "backups")}

        def run(progress=None, cancel=None):
            files = []
            for root, dirs, fs in os.walk(app_dir):
                if any(root == d or root.startswith(d + os.sep) for d in skip_dirs) or root.endswith(".installing"):
                    dirs[:] = []
                    continue
                for f in fs:
                    p = os.path.join(root, f)
                    if os.path.abspath(p) == os.path.abspath(dest) or f.endswith((".part", "-wal", "-shm")) or f == "app_log.txt" \
                            or f.startswith(("SeforimLibrary.sqlite.xz", "SeforimAI.tar")):
                        continue
                    files.append(p)
            total = sum(os.path.getsize(p) for p in files) or 1
            done = 0
            with self.lib.lock:  # flush everything into the main library file first
                self.lib.db.commit()
                try:
                    self.lib.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except Exception:
                    pass
            if True:
                with zipfile.ZipFile(dest + ".part", "w", zipfile.ZIP_DEFLATED, allowZip64=True, compresslevel=1) as z:
                    for p in files:
                        if cancel and cancel():
                            break
                        rel = os.path.join("SeforimStudio", os.path.relpath(p, app_dir))
                        # already-compressed data (AI model, pictures, fonts) is stored as-is: much faster
                        packed = p.lower().endswith((".gguf", ".zip", ".png", ".jpg", ".woff2", ".ttf", ".dll", ".exe", ".pyd")) or os.sep + "blobs" + os.sep in p
                        z.write(p, rel, compress_type=zipfile.ZIP_STORED if packed else zipfile.ZIP_DEFLATED)
                        done += os.path.getsize(p)
                        if progress:
                            progress(done, total, os.path.basename(p))
            if cancel and cancel():
                os.remove(dest + ".part")
                return {"cancelled": True}
            os.replace(dest + ".part", dest)
            return {"path": dest, "size_gb": round(os.path.getsize(dest) / 1e9, 2), "files": len(files)}
        return {"job": self.jobs.start(run), "dest": dest}

    def api_export_user(self, a):
        p = self.export_path(f"my-data-{self.user.profile}-{dt.date.today()}.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.user.export_all(), f, ensure_ascii=False, indent=1)
        return {"url": self.file_url(p), "path": p}

    def api_import_user(self, a):
        with open(self._upload_path(a["upload"]), encoding="utf-8") as f:
            return {"imported": self.user.import_all(json.load(f))}

    # ---- documents: export / import
    def api_export_doc(self, a):
        fmt, title = a.get("format", "docx"), a.get("title") or "document"
        html_body = a.get("html", "")
        p = self.export_path(f"{title}.{fmt}")
        if fmt == "docx":
            F.html_to_docx(html_body, p, title if a.get("title_in_doc") else "", a.get("font") or "David", float(a.get("size") or 14))
        elif fmt == "txt":
            with open(p, "w", encoding="utf-8") as f: f.write(F.html_to_text(html_body))
        elif fmt == "md":
            with open(p, "w", encoding="utf-8") as f: f.write(F.html_to_markdown(html_body))
        elif fmt == "html":
            with open(p, "w", encoding="utf-8") as f: f.write(F.full_html(html_body, title))
        elif fmt == "json":
            with open(p, "w", encoding="utf-8") as f: json.dump({"title": title, "html": html_body, "app": "Seforim Studio"}, f, ensure_ascii=False)
        elif fmt == "epub":
            parts = re.split(r"(?=<h[12][^>]*>)", html_body)
            chapters = [(re.sub(r"<[^>]+>", "", re.search(r"<h[12][^>]*>(.*?)</h[12]>", c, re.S).group(1)) if re.search(r"<h[12]", c) else title, c) for c in parts if c.strip()]
            F.to_epub(chapters or [(title, html_body)], p, title, a.get("author", ""))
        elif fmt == "tei":
            p = self.export_path(f"{title}.xml")
            paras = [{"ref": f"{title} {i + 1}", "he": F.html_to_text(x)} for i, x in enumerate(re.findall(r"<(?:p|h\d|li)[^>]*>(.*?)</(?:p|h\d|li)>", html_body, re.S)) if F.html_to_text(x)]
            with open(p, "w", encoding="utf-8") as f: f.write(F.to_tei(paras, title, a.get("author", "")))
        else:
            raise ValueError("Unknown format")
        return {"url": self.file_url(p), "path": p, "name": os.path.basename(p)}

    def api_export_passages(self, a):
        """Export a work / chapter range / result list in many formats (mass section export)."""
        fmt = a.get("format", "docx")
        if a.get("ids"):
            ph = ",".join("?" * len(a["ids"]))
            rows = self.lib.q(f"SELECT ref, he, en FROM passages WHERE id IN ({ph}) ORDER BY work_id, seq", a["ids"])
        else:
            q = "SELECT ref, he, en, node, chapter FROM passages WHERE work_id=?"
            args = [a["work_id"]]
            if a.get("chapter") is not None and not a.get("whole"):
                q += " AND node=? AND chapter=?"; args += [a.get("node", ""), a["chapter"]]
            rows = self.lib.q(q + " ORDER BY seq", args)
        title = a.get("title") or "export"
        show_en = a.get("english", True)
        p = self.export_path(f"{title}.{ 'xml' if fmt == 'tei' else fmt}")
        if fmt == "docx":
            h = "".join(f"<p><span style='color:#8a6d3b;font-size:10pt'>{F.html.escape(r['ref'])}</span><br>{F.html.escape(r['he'] or '')}</p>" +
                        (f"<p dir='ltr'>{F.html.escape(r['en'])}</p>" if show_en and r.get("en") else "") for r in rows)
            F.html_to_docx(h, p, title, a.get("font") or "David", float(a.get("size") or 14))
        elif fmt == "txt":
            with open(p, "w", encoding="utf-8") as f:
                f.write("\n\n".join(f"{r['ref']}\n{r['he']}" + (f"\n{r['en']}" if show_en and r.get("en") else "") for r in rows))
        elif fmt == "html":
            with open(p, "w", encoding="utf-8") as f: f.write(F.passages_to_html(rows, title, show_en))
        elif fmt == "json":
            with open(p, "w", encoding="utf-8") as f: json.dump({"title": title, "passages": rows}, f, ensure_ascii=False, indent=1)
        elif fmt == "csv":
            with open(p, "w", encoding="utf-8", newline="") as f: f.write(F.to_csv(rows, ["ref", "he", "en"]))
        elif fmt == "tei":
            with open(p, "w", encoding="utf-8") as f: f.write(F.to_tei(rows, title))
        elif fmt == "epub":
            chapters = {}
            for r in rows:
                key = (r.get("node") or "") + " " + (r.get("chapter") or "")
                chapters.setdefault(key.strip() or title, []).append(f"<p>{F.html.escape(r['he'] or '')}</p>")
            F.to_epub([(k, "".join(v)) for k, v in chapters.items()], p, title)
        elif fmt == "md":
            with open(p, "w", encoding="utf-8") as f: f.write("\n\n".join(f"**{r['ref']}**  \n{r['he']}" + (f"  \n*{r['en']}*" if show_en and r.get("en") else "") for r in rows))
        elif fmt == "sqlite":
            import sqlite3
            p = self.export_path(f"{title}.sqlite")
            if os.path.exists(p): os.remove(p)
            c = sqlite3.connect(p); c.execute("CREATE TABLE passages(ref TEXT, he TEXT, en TEXT)")
            c.executemany("INSERT INTO passages VALUES(?,?,?)", [(r["ref"], r["he"], r["en"]) for r in rows]); c.commit(); c.close()
        return {"url": self.file_url(p), "path": p, "name": os.path.basename(p), "count": len(rows)}

    def _upload_path(self, name):
        p = os.path.join(self.data, "uploads", os.path.basename(name))
        if not os.path.exists(p):
            raise FileNotFoundError(name)
        return p

    def api_import_file(self, a):
        p = self._upload_path(a["upload"])
        title, h, text = F.import_file(p)
        return {"title": title, "html": h, "text": text}

    def api_import_as_sefer(self, a):
        """Add a document to the Personal Library as a searchable sefer."""
        text = a.get("text")
        title = a.get("title") or "My sefer"
        if not text and a.get("upload"):
            title2, h, text = F.import_file(self._upload_path(a["upload"]))
            title = a.get("title") or title2
        if not text and a.get("html"):
            text = F.html_to_text(a["html"])
        wid = a.get("work_id") or (9_000_000 + int(time.time()) % 1_000_000)
        n = self.lib.import_plain_document(wid, title, text or "", a.get("category") or "Personal Library", a.get("he_title", ""))
        return {"work_id": wid, "passages": n}

    def api_delete_work(self, a):
        self.lib.delete_work(int(a["work_id"]))
        return {"ok": True}

    # ---- downloads (one-time setup)
    def api_dl_start(self, a):
        if not self.catalog:
            return {"error": "Load the catalog DB first"}
        ids = list(a.get("work_ids") or [])
        if a.get("categories"):
            ids += [w["id"] for w in self.catalog.works_in(a["categories"])]
        ids = sorted(set(ids))
        if a.get("missing_only"):
            have = {r["id"] for r in self.lib.q("SELECT id FROM works WHERE n_passages>0")}
            ids = [i for i in ids if i not in have]
        ok = self.dl.start(ids, a.get("english", True), True, a.get("links", False))
        return {"started": ok, "count": len(ids)}

    def api_dl_titles(self, a):
        if not self.catalog:
            return {"error": "Load the catalog DB first"}
        return {"started": self.dl.fetch_titles()}

    def api_he_coverage(self, a):
        from .order import he_name
        if not self.catalog:
            return {}
        ws = self.catalog.q("SELECT title FROM works")
        return {"works": len(ws), "with_hebrew": sum(1 for w in ws if he_name(w["title"])),
                "official": self.lib.q1("SELECT COUNT(*) n FROM he_titles")["n"]}

    def api_dl_status(self, a):
        return self.dl.state if self.catalog else {"running": False}

    def api_dl_stop(self, a):
        self.dl.stop(); return {"ok": True}

    def api_import_folder(self, a):
        if not os.path.isdir(a.get("path", "")):
            return {"error": "Folder not found"}
        return {"job": self.jobs.start(lambda progress=None, cancel=None: self.dl.import_folder(a["path"]))}

    def api_load_catalog(self, a):
        p = a.get("path") or self._upload_path(a["upload"])
        if a.get("upload"):
            dest = os.path.join(self.data, "seforim_catalog.db")
            shutil.copy2(p, dest); p = dest
        self.load_catalog(p)
        return self.catalog.info()

    def api_compact(self, a):
        return self.lib.compact()

    # ---- fonts
    def api_fonts(self, a):
        out = []
        for p in sorted(glob.glob(os.path.join(self.data, "fonts", "*", "*.woff2")) + glob.glob(os.path.join(self.data, "fonts", "*", "*.ttf"))):
            fam = os.path.basename(os.path.dirname(p))
            out.append({"family": fam, "url": self.file_url(p), "file": os.path.basename(p)})
        return out

    def api_fonts_download(self, a):
        from .fonts import download_font_pack
        return {"job": self.jobs.start(download_font_pack, os.path.join(self.data, "fonts"), a.get("families"))}

    def api_fonts_install_windows(self, a):
        from .fonts import install_windows
        return install_windows(os.path.join(self.data, "fonts"))

    def api_fonts_import(self, a):
        p = self._upload_path(a["upload"])
        fam = re.sub(r"[^\w \-]", "", a.get("family") or os.path.splitext(os.path.basename(p))[0]).strip() or "Custom"
        d = os.path.join(self.data, "fonts", fam); os.makedirs(d, exist_ok=True)
        shutil.copy2(p, os.path.join(d, os.path.basename(p)))
        return {"ok": True, "family": fam}

    # ---- scanner (Step 1 + document text)
    def api_scan_start(self, a):
        from scanner import cleanup
        files = [self._upload_path(u) for u in a.get("uploads", [])]
        out = os.path.join(self.data, "scans", dt.datetime.now().strftime("%Y%m%d-%H%M%S"))

        def run(progress=None, cancel=None):
            res = cleanup.process_files(files, out, a.get("opts"), progress)
            for r in res:
                r["urls"] = {k: self.file_url(v) for k, v in r["files"].items()}
            return {"pages": res, "folder": out}
        return {"job": self.jobs.start(run)}

    def api_scan_redo(self, a):
        """Re-clean one page with extra rotation / other options."""
        from scanner import cleanup
        import cv2
        orig = os.path.join(self.data, urllib.parse.unquote(a["original"]).replace("/files/", "", 1))
        img = cv2.imdecode(__import__("numpy").fromfile(orig, "uint8"), cv2.IMREAD_COLOR)
        r = cleanup.clean_page(img, a.get("opts"))
        base = orig.replace("_original.jpg", "")
        for k in ("color", "gray", "bw"):
            cleanup.imwrite(f"{base}_{k}.png", r[k])
        stamp = int(time.time())
        return {"info": r["info"], "urls": {k: self.file_url(f"{base}_{k}.png") + f"?v={stamp}" for k in ("color", "gray", "bw")}}

    def _engine_kw(self):
        st = self.user.all_settings()
        return {"models_dir": os.path.join(self.data, "models"), "ollama_model": st.get("ollama_model") or None,
                "kraken_model": st.get("kraken_model") or None}

    def api_scan_engines(self, a):
        from scanner import engines
        return engines.status(**self._engine_kw())

    def api_scan_ocr(self, a):
        """Read pages with engine A/B/C (auto = best installed). pages: list of {files:{color,gray,bw}}."""
        from scanner import engines
        eng = engines.pick(a.get("engine", "auto"), **self._engine_kw())
        pages = a.get("pages", [])
        strips = a.get("strips")

        def run(progress=None, cancel=None):
            out = []
            for i, p in enumerate(pages):
                if cancel and cancel():
                    break
                path = engines.best_input(p["files"], eng.key)
                sub = (lambda j, n, label, i=i: progress(i, len(pages), f"Page {i + 1}/{len(pages)} — {label}")) if progress else None
                if progress:
                    progress(i, len(pages), f"Page {i + 1}/{len(pages)} — {eng.name}")
                try:
                    out.append(eng.read_image(engines.imread(path), int(strips) if strips else None, sub, cancel))
                except Exception as e:  # noqa
                    out.append(f"[page {i + 1}: {e}]")
            if progress:
                progress(len(pages), len(pages), "done")
            return {"engine": eng.name, "pages": out}
        return {"job": self.jobs.start(run), "engine": eng.name}

    def api_scan_train(self, a):
        """Save line images + corrected text as Kraken training pairs (to fine-tune on one person's handwriting)."""
        from scanner import engines
        out = os.path.join(self.data, "training", re.sub(r"[^\w\-]+", "_", a.get("writer") or "writer"))
        res = []
        for i, (p, t) in enumerate(zip(a.get("pages", []), a.get("texts", []))):
            res.append(engines.save_training_pairs(p["files"]["bw"], t, out, f"{int(time.time())}_{i + 1}"))
        n = sum(1 for _ in glob.glob(os.path.join(out, "*.gt.txt")))
        return {"pages": res, "folder": out, "total_lines": n}

    def api_scan_text(self, a):
        """Extract text straight from documents (PDF text layer, Word, text) — editable, no OCR."""
        from scanner.cleanup import extract_document_text
        pages = []
        for u in a.get("uploads", []):
            p = self._upload_path(u)
            ext = os.path.splitext(p)[1].lower()
            if ext == ".pdf":
                pages += F.pdf_text_pages(p, a.get("order", "auto"))
            elif ext in (".docx", ".txt", ".md", ".html", ".htm", ".epub"):
                pages += extract_document_text(p)
            else:
                pages.append("")
        return {"pages": pages, "needs_ocr": [i for i, t in enumerate(pages) if not t.strip()]}

    def api_scan_save(self, a):
        fmt = a.get("format", "docx")
        title = a.get("title") or "scanned-notes"
        pages = a.get("pages") or [a.get("text", "")]
        if fmt == "docx":
            p = self.export_path(f"{title}.docx")
            F.text_to_docx("", p, "", a.get("font") or "David", float(a.get("size") or 14), pages=pages)
        else:
            p = self.export_path(f"{title}.txt")
            with open(p, "w", encoding="utf-8") as f:
                f.write("\n\n\f".join(pages))
        return {"url": self.file_url(p), "path": p, "name": os.path.basename(p)}

    # ---- sharing
    def _package_items(self, kind, ids):
        if kind in ("docs", "sheets", "covers", "notes", "bookmarks", "transcriptions"):
            items = []
            for i in ids:
                rows = self.user.q(f"SELECT * FROM {kind} WHERE id=?", (i,))
                items += [r for r in rows if not r.get("private")]
            return items
        if kind == "works":
            out = []
            for wid in ids:
                w = self.lib.work(wid)
                if w:
                    w["passages"] = self.lib.q("SELECT node,chapter,verse,ref,he,en FROM passages WHERE work_id=? ORDER BY seq", (wid,))
                    out.append(w)
            return out
        raise ValueError(kind)

    def api_package_export(self, a):
        items = self._package_items(a["kind"], a.get("ids", []))
        p = self.export_path(f"{a.get('name') or a['kind']}-{dt.datetime.now():%Y%m%d-%H%M}.seforim")
        F.make_package(p, a["kind"], items, {"from": self.share.name, "profile": self.user.profile})
        return {"url": self.file_url(p), "path": p, "name": os.path.basename(p), "count": len(items)}

    def import_package(self, path):
        man, items = F.read_package(path)
        kind = man["kind"]
        n = 0
        if kind == "works":
            for w in items:
                wid = 8_000_000 + (abs(hash(w["title"])) % 900_000)
                he = {}
                text = {}
                # rebuild as simple chapter/paragraph structure preserving refs where possible
                lines = [p.get("he") or p.get("en") or "" for p in w["passages"]]
                n += self.lib.import_plain_document(wid, w["title"], "\n".join(lines), w.get("category_path") or "Shared with me", w.get("he_title", ""))
        else:
            for it in items:
                it = dict(it); it.pop("id", None)
                if kind == "docs":
                    it["folder"] = "Shared with me"
                self.user.save(kind, it); n += 1
        return {"kind": kind, "count": n, "from": man.get("meta", {}).get("from")}

    def api_package_import(self, a):
        return self.import_package(self._upload_path(a["upload"]) if a.get("upload") else os.path.join(self.data, "inbox", os.path.basename(a["inbox"])))

    def api_share_enable(self, a):
        if a.get("on"):
            if not self.share_server:
                self.share_server = start_share_server(self, int(a.get("port") or 0))
            self.share.name = a.get("name") or self.share.name
            self.share.start(self.share_server.server_address[1])
        else:
            self.share.stop()
            if self.share_server:
                self.share_server.shutdown(); self.share_server.server_close(); self.share_server = None
        return self.api_status({})["share"]

    def api_share_peers(self, a):
        if a.get("add_ip"):
            self.share.add_manual_peer(a["add_ip"], a.get("port") or 47480)
        return self.share.peer_list()

    def api_share_send(self, a):
        pkg = self.api_package_export(a)
        return self.share.send(a["peer"], pkg["path"], a["code"], a.get("sender"))

    def api_share_inbox(self, a):
        if a.get("delete"):
            self.share.remove(a["delete"])
        return self.share.inbox()

    def api_bluetooth(self, a):
        if a.get("receive"):
            return {"message": bluetooth_receive()}
        pkg = self.api_package_export(a)
        return {"message": bluetooth_send(pkg["path"]), "path": pkg["path"]}

    def api_open_folder(self, a):
        p = a.get("path") or self.data
        if not os.path.exists(p):
            return {"ok": False}
        if os.name == "nt":
            os.startfile(p if os.path.isdir(p) else os.path.dirname(p))  # noqa
        elif shutil.which("open"):
            winproc.popen(["open", p])
        elif shutil.which("xdg-open"):
            winproc.popen(["xdg-open", os.path.dirname(p) if os.path.isfile(p) else p])
        return {"ok": True}

    def api_quit(self, a):
        if self.ollama_proc:
            try:
                self.ollama_proc.terminate()
            except Exception:
                pass
        threading.Timer(0.5, lambda: os._exit(0)).start()
        return {"ok": True}


# ====================================================================== HTTP
def make_handler(app):
    class H_(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
            if isinstance(body, (dict, list)) or body is None:
                body = json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _local_only(self):
            return self.client_address[0] in ("127.0.0.1", "::1")

        def _serve_file(self, root, rel, download=False):
            path = os.path.normpath(os.path.join(root, urllib.parse.unquote(rel)))
            if not path.startswith(os.path.normpath(root)) or not os.path.isfile(path):
                return self._send(404, {"error": "not found"})
            ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
            with open(path, "rb") as f:
                data = f.read()
            extra = {}
            if download:
                extra["Content-Disposition"] = "attachment; filename*=UTF-8''" + urllib.parse.quote(os.path.basename(path))
            self._send(200, data, ctype, extra)

        def do_GET(self):
            if not self._local_only():
                return self._send(403, {"error": "forbidden"})
            u = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(u.query)
            if u.path == "/":
                with open(os.path.join(app.web, "index.html"), encoding="utf-8") as f:
                    html = f.read().replace("__TOKEN__", app.token)
                return self._send(200, html, "text/html; charset=utf-8")
            if u.path.startswith("/files/"):
                if qs.get("t", [""])[0] != app.token and not u.path.startswith("/files/fonts/"):
                    return self._send(403, {"error": "token"})
                return self._serve_file(app.data, u.path[7:], download=qs.get("dl", ["0"])[0] == "1")
            if u.path == "/favicon.ico":
                return self._serve_file(app.web, "icon.svg")
            if u.path.startswith("/web/"):
                return self._serve_file(app.web, u.path[5:])
            return self._send(404, {"error": "not found"})

        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n) if n else b""
            if u.path == "/share/inbox":  # only path reachable from the LAN listener too
                code, res = app.share.receive(body, self.headers.get("X-Pair-Code", ""),
                                              bytes.fromhex(self.headers.get("X-Sender", "")).decode("utf-8", "replace"),
                                              bytes.fromhex(self.headers.get("X-Filename", "")).decode("utf-8", "replace"))
                return self._send(code, res)
            if not self._local_only() or self.headers.get("X-Token") != app.token:
                return self._send(403, {"error": "forbidden"})
            if u.path == "/upload":
                name = urllib.parse.unquote(self.headers.get("X-Filename", "upload.bin"))
                safe = re.sub(r'[\\/:*?"<>|]+', "_", os.path.basename(name))
                fn = f"{uuid.uuid4().hex[:6]}-{safe}"
                with open(os.path.join(app.data, "uploads", fn), "wb") as f:
                    f.write(body)
                return self._send(200, {"upload": fn, "name": name, "size": len(body)})
            if u.path.startswith("/api/"):
                name = u.path[5:]
                fn = getattr(app, "api_" + name, None)
                if not fn:
                    return self._send(404, {"error": f"unknown api {name}"})
                try:
                    args = json.loads(body or b"{}")
                    return self._send(200, fn(args))
                except Exception as e:  # noqa
                    traceback.print_exc()
                    return self._send(500, {"error": f"{type(e).__name__}: {e}"})
            return self._send(404, {"error": "not found"})

    return H_


def start_share_server(app, port=0):
    """LAN listener: only accepts POST /share/inbox (with pairing code)."""
    class ShareOnly(make_handler(app)):
        def do_GET(self):
            return self._send(200, {"app": "Seforim Studio", "name": app.share.name})

        def do_POST(self):
            if urllib.parse.urlparse(self.path).path != "/share/inbox":
                return self._send(403, {"error": "forbidden"})
            return super().do_POST()
    srv = ThreadingHTTPServer(("0.0.0.0", port or 47480), ShareOnly)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def serve(app, port=0):
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
