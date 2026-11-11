"""Local offline text library: import Sefaria JSON, full-text search (Hebrew/English,
boolean, phrase, wildcard, NEAR, prefixes, malei/chaser, root, fuzzy, regex, acronyms),
gematria, roshei/sofei teivos, ELS, cross-reference links, statistics."""
import csv
import json
import os
import re
import sqlite3
import threading
import time
from collections import Counter, defaultdict

from . import hebrew as H
from .data_tables import ABBREV_CLEAN
from .order import sort_key, he_name

PREFIXES = ["ו", "ה", "ב", "כ", "ל", "מ", "ש", "וה", "וב", "וכ", "ול", "ומ", "וש", "שה", "שב", "של", "שמ", "מה",
            "בה", "לה", "כה", "ושה", "ושב", "ושל", "כשה", "וכש", "כש", "מש", "ומש", "לכ", "ולכ"]


def skeleton(w):
    """Malei/chaser-insensitive form: drop vav and yud (except first letter)."""
    return w[:1] + "".join(c for c in w[1:] if c not in "וי") if w else w


def norm_ref(r):
    """'Genesis 1:1-3' -> 'Genesis 1:1'."""
    r = r.strip()
    m = re.match(r"^(.*?\d+[ab]?(?::\d+)*)(?:-[\d:ab]+)?$", r)
    return m.group(1) if m else r


def _fts_quote(t):
    return '"' + t.replace('"', '""') + '"'


class Library:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.lock = threading.RLock()
        self._local = threading.local()
        self._readers = []
        self.db = sqlite3.connect(path, check_same_thread=False, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.create_function("regexp", 2, lambda p, s: 1 if s and re.search(p, s) else 0, deterministic=True)
        self._init()
        self._gem_cache = {}
        self.refresh_he_titles()

    def refresh_he_titles(self):
        from .he_names import load_overrides
        m = {r["title"]: r["he_title"] for r in self.q("SELECT title, he_title FROM he_titles")}
        m.update({r["title"]: r["he_title"] for r in self.q("SELECT title, he_title FROM works WHERE he_title != ''")})
        load_overrides(m)
        return len(m)

    def save_he_title(self, meta):
        authors = meta.get("authors") or []
        comp = meta.get("compDate") or ""
        if isinstance(comp, list):
            comp = "-".join(str(x) for x in comp)
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO he_titles VALUES(?,?,?,?,?,?,?)",
                            (meta.get("title", ""), meta.get("heTitle", ""),
                             ", ".join(a.get("en", "") for a in authors if isinstance(a, dict)),
                             ", ".join(a.get("he", "") for a in authors if isinstance(a, dict)),
                             str(comp), meta.get("era", ""), str(meta.get("compPlace", ""))))

    # ------------------------------------------------------------------ schema
    def _init(self):
        c = self.db
        c.executescript("""
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS works(id INTEGER PRIMARY KEY, title TEXT, he_title TEXT, category_path TEXT,
            top_category TEXT, sort_key TEXT, section_names TEXT, authors TEXT, he_authors TEXT, comp_date TEXT,
            era TEXT, comp_place TEXT, description TEXT, n_passages INT DEFAULT 0, n_words INT DEFAULT 0,
            imported_at TEXT, source TEXT);
        CREATE TABLE IF NOT EXISTS passages(id INTEGER PRIMARY KEY, work_id INT, seq INT, node TEXT, chapter TEXT,
            verse TEXT, ref TEXT, he TEXT, en TEXT, he_plain TEXT, initials TEXT, finals TEXT);
        CREATE INDEX IF NOT EXISTS ix_p_work ON passages(work_id, seq);
        CREATE INDEX IF NOT EXISTS ix_p_ref ON passages(ref);
        CREATE TABLE IF NOT EXISTS words(word TEXT PRIMARY KEY, freq INT, g_std INT, g_gadol INT, g_katan INT,
            g_ord INT, skel TEXT) WITHOUT ROWID;
        CREATE INDEX IF NOT EXISTS ix_w_std ON words(g_std);
        CREATE INDEX IF NOT EXISTS ix_w_gadol ON words(g_gadol);
        CREATE INDEX IF NOT EXISTS ix_w_katan ON words(g_katan);
        CREATE INDEX IF NOT EXISTS ix_w_ord ON words(g_ord);
        CREATE INDEX IF NOT EXISTS ix_w_skel ON words(skel);
        CREATE TABLE IF NOT EXISTS he_titles(title TEXT PRIMARY KEY, he_title TEXT, authors TEXT, he_authors TEXT,
            comp_date TEXT, era TEXT, comp_place TEXT) WITHOUT ROWID;
        CREATE TABLE IF NOT EXISTS links(ref1 TEXT, ref2 TEXT, type TEXT, cat1 TEXT, cat2 TEXT);
        CREATE INDEX IF NOT EXISTS ix_l1 ON links(ref1);
        CREATE INDEX IF NOT EXISTS ix_l2 ON links(ref2);
        """)
        # newer column: the literal ("basic") translation, where the source marks it
        if "en_basic" not in [r[1] for r in c.execute("PRAGMA table_info(passages)")]:
            try:
                c.execute("ALTER TABLE passages ADD COLUMN en_basic TEXT")
            except sqlite3.OperationalError:
                pass
        try:
            c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts_he USING fts5(he_plain, he_skel, content='', "
                      "contentless_delete=1, tokenize='unicode61 remove_diacritics 0')")
            c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts_en USING fts5(en, content='', contentless_delete=1, "
                      "tokenize='porter unicode61')")
            self.contentless = True
        except sqlite3.OperationalError:  # older SQLite: keep a copy of text inside FTS
            c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts_he USING fts5(he_plain, he_skel, "
                      "tokenize='unicode61 remove_diacritics 0')")
            c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts_en USING fts5(en, tokenize='porter unicode61')")
            self.contentless = False
        c.commit()

    def _reader(self):
        """Each server thread reads through its own connection, so a long search never blocks opening a sefer."""
        c = getattr(self._local, "db", None)
        if c is None:
            c = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA query_only=1")
            c.execute("PRAGMA cache_size=-65536")
            c.create_function("regexp", 2, lambda p, s: 1 if s and re.search(p, s) else 0, deterministic=True)
            self._local.db = c
            self._readers.append(c)
        return c

    def close(self):
        for c in self._readers + [self.db]:
            try:
                c.close()
            except Exception:
                pass
        self._readers.clear()

    def q(self, sql, args=()):
        head = sql.lstrip()[:6].upper()
        if head in ("SELECT", "WITH S") and not self.lock._is_owned():
            return [dict(r) for r in self._reader().execute(sql, args).fetchall()]
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def q1(self, sql, args=()):
        r = self.q(sql, args)
        return r[0] if r else None

    # ------------------------------------------------------------------ import
    @staticmethod
    def _label(i, atype):
        if atype == "Talmud":
            return f"{i // 2 + 1}{'ab'[i % 2]}"
        return str(i + 1)

    def _flatten(self, text, schema, node_path=()):
        """Yield (node_path tuple, labels tuple, string) from Sefaria 'text' structure."""
        if isinstance(text, dict):
            nodes = {}
            for n in (schema or {}).get("nodes", []) or []:
                key = n.get("title") or next((t.get("text") for t in n.get("titles", []) if t.get("primary") and t.get("lang") == "en"), "")
                nodes[key] = n
            for key, val in text.items():
                sub = nodes.get(key, {}) if key else (schema or {})
                yield from self._flatten(val, sub, node_path + ((key,) if key else ()))
            return
        atypes = (schema or {}).get("addressTypes") or []
        snames = (schema or {}).get("sectionNames") or []
        if not atypes and snames and snames[0] in ("Daf",):
            atypes = ["Talmud"]

        def rec(obj, labels, depth):
            if isinstance(obj, str):
                if obj.strip():
                    yield node_path, labels, obj
                return
            if isinstance(obj, list):
                at = atypes[depth] if depth < len(atypes) else "Integer"
                for i, el in enumerate(obj):
                    yield from rec(el, labels + (self._label(i, at),), depth + 1)
        yield from rec(text, (), 0)

    @staticmethod
    def make_ref(title, node_path, labels):
        base = title + ("".join(", " + n for n in node_path) if node_path else "")
        return base + (" " + ":".join(labels) if labels else "")

    def import_work(self, work, he_json=None, en_json=None, schema_json=None, source="sefaria"):
        """work: dict(id,title,category_path,top_category).  he/en_json: parsed merged.json dicts."""
        title = work["title"]
        schema = (he_json or en_json or {}).get("schema") or {}
        if not schema and (he_json or en_json):
            schema = {"sectionNames": (he_json or en_json).get("sectionNames", [])}
        rows = {}
        order = []
        for lang, js in (("he", he_json), ("en", en_json)):
            if not js:
                continue
            for node, labels, s in self._flatten(js.get("text", []), schema):
                key = (node, labels)
                if key not in rows:
                    rows[key] = {"he": "", "en": ""}
                    order.append(key)
                if lang == "en" and "<b>" in (s or ""):
                    # the literal translation is in bold (e.g. the William Davidson Talmud), the explanation is not:
                    # keep the literal part too, so the reader can choose a basic or an explanatory translation
                    rows[key]["en_basic"] = " ".join(H.strip_html(b).strip() for b in re.findall(r"<b>(.*?)</b>", s, flags=re.S))
                rows[key][lang] = H.strip_html(s).strip()
        he_title = (he_json or en_json or {}).get("heTitle") or (schema_json or {}).get("heTitle") or he_name(title)
        meta = schema_json or {}
        authors = meta.get("authors") or []
        a_en = ", ".join(a.get("en", "") if isinstance(a, dict) else str(a) for a in authors)
        a_he = ", ".join(a.get("he", "") for a in authors if isinstance(a, dict))
        comp = meta.get("compDate") or meta.get("pubDate") or ""
        if isinstance(comp, list):
            comp = "-".join(str(x) for x in comp)
        with self.lock:
            self.delete_work(work["id"], commit=False)
            self.db.execute("""INSERT OR REPLACE INTO works(id,title,he_title,category_path,top_category,sort_key,
                section_names,authors,he_authors,comp_date,era,comp_place,description,imported_at,source)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?)""",
                (work["id"], title, he_title, work.get("category_path", ""), work.get("top_category", ""),
                 json.dumps(sort_key(title)), json.dumps(schema.get("sectionNames") or []), a_en, a_he,
                 str(comp), meta.get("era", ""), str(meta.get("compPlace", "")), (meta.get("enDesc") or "")[:2000], source))
            wc = Counter()
            seq = 0
            for key in order:
                node, labels = key
                he, en = rows[key]["he"], rows[key]["en"]
                plain_list = H.plain_words(he)
                plain = " ".join(plain_list)
                skel = " ".join(skeleton(w) for w in plain_list)
                initials = "".join(H.normalize_finals(w[0]) for w in plain_list)
                finals = "".join(H.normalize_finals(w[-1]) for w in plain_list)
                chapter = labels[0] if len(labels) > 1 else ""
                verse = ":".join(labels[1:]) if len(labels) > 1 else (labels[0] if labels else "")
                ref = self.make_ref(title, node, labels)
                seq += 1
                cur = self.db.execute("""INSERT INTO passages(work_id,seq,node,chapter,verse,ref,he,en,he_plain,initials,finals,en_basic)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (work["id"], seq, ", ".join(node), chapter, verse, ref, he, en,
                                                       plain, initials, finals, rows[key].get("en_basic") or None))
                pid = cur.lastrowid
                if plain:
                    self.db.execute("INSERT INTO fts_he(rowid,he_plain,he_skel) VALUES(?,?,?)", (pid, plain, skel))
                if en:
                    self.db.execute("INSERT INTO fts_en(rowid,en) VALUES(?,?)", (pid, en))
                wc.update(plain_list)
            self._add_words(wc)
            self.db.execute("UPDATE works SET n_passages=?, n_words=? WHERE id=?", (seq, sum(wc.values()), work["id"]))
            self.db.commit()
        return seq

    def import_rows(self, work, rows, source="otzaria", commit=True):
        """Import a sefer given as ready rows: [{"node", "chapter", "verse", "he", "en", "en_basic"}] (the Otzaria format:
        headings become node / chapter, every line of text a passage). Returns the passage ids in order."""
        title = work["title"]
        ids = []
        with self.lock:
            self.delete_work(work["id"], commit=False)
            self.db.execute("""INSERT OR REPLACE INTO works(id,title,he_title,category_path,top_category,sort_key,
                section_names,authors,he_authors,comp_date,era,comp_place,description,imported_at,source)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?)""",
                (work["id"], title, work.get("he_title") or title, work.get("category_path", ""), work.get("top_category", ""),
                 json.dumps(work.get("sort_key") or sort_key(title)), json.dumps(work.get("section_names") or []),
                 work.get("authors", ""), work.get("he_authors", ""), "", "", "", work.get("description", ""), source))
            wc = Counter()
            for seq, r in enumerate(rows, 1):
                he, en = r.get("he") or "", r.get("en") or ""
                plain_list = H.plain_words(he)
                plain = " ".join(plain_list)
                node, chapter, verse = r.get("node") or "", r.get("chapter") or "", str(r.get("verse") or seq)
                ref = title + (", " + node if node else "") + (" " + chapter + ":" + verse if chapter else " " + verse)
                cur = self.db.execute("""INSERT INTO passages(work_id,seq,node,chapter,verse,ref,he,en,he_plain,initials,finals,en_basic)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (work["id"], seq, node, chapter, verse, ref, he, en, plain,
                                                       "".join(H.normalize_finals(w[0]) for w in plain_list),
                                                       "".join(H.normalize_finals(w[-1]) for w in plain_list), r.get("en_basic") or None))
                pid = cur.lastrowid
                ids.append(pid)
                if plain:
                    self.db.execute("INSERT INTO fts_he(rowid,he_plain,he_skel) VALUES(?,?,?)",
                                    (pid, plain, " ".join(skeleton(w) for w in plain_list)))
                if en:
                    self.db.execute("INSERT INTO fts_en(rowid,en) VALUES(?,?)", (pid, en))
                wc.update(plain_list)
            self._add_words(wc)
            self.db.execute("UPDATE works SET n_passages=?, n_words=? WHERE id=?", (len(rows), sum(wc.values()), work["id"]))
            if commit:
                self.db.commit()
        return ids

    def _add_words(self, wc, sign=1):
        for w, n in wc.items():
            self.db.execute("""INSERT INTO words(word,freq,g_std,g_gadol,g_katan,g_ord,skel) VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(word) DO UPDATE SET freq=freq+excluded.freq""",
                            (w, n * sign, H.g_standard(w), H.g_gadol(w), H.g_katan(w), H.g_ordinal(w), skeleton(w)))

    def delete_work(self, work_id, commit=True):
        with self.lock:
            rows = self.db.execute("SELECT id, he_plain, en FROM passages WHERE work_id=?", (work_id,)).fetchall()
            if not rows:
                self.db.execute("DELETE FROM works WHERE id=?", (work_id,))
                return
            wc = Counter()
            for r in rows:
                if r["he_plain"]:
                    if self.contentless:
                        self.db.execute("DELETE FROM fts_he WHERE rowid=?", (r["id"],))
                    else:
                        self.db.execute("DELETE FROM fts_he WHERE rowid=?", (r["id"],))
                    wc.update(r["he_plain"].split())
                if r["en"]:
                    self.db.execute("DELETE FROM fts_en WHERE rowid=?", (r["id"],))
            for w, n in wc.items():
                self.db.execute("UPDATE words SET freq=freq-? WHERE word=?", (n, w))
            self.db.execute("DELETE FROM words WHERE freq<=0")
            self.db.execute("DELETE FROM passages WHERE work_id=?", (work_id,))
            self.db.execute("DELETE FROM works WHERE id=?", (work_id,))
            if commit:
                self.db.commit()

    def import_plain_document(self, work_id, title, text, category="Personal Library", he_title=""):
        """Import a user document (txt/docx/pdf text) as a sefer. Paragraphs = passages.
        Lines like '# Heading' or 'סימן א' / 'פרק ב' start a new chapter."""
        chapters, cur_ch, cur = [], "1", []
        n_ch = 1
        for line in text.splitlines():
            s = line.strip()
            if not s:
                continue
            m = re.match(r"^(#+\s*|(?:סימן|פרק|חלק|Chapter|Siman|Perek)\s+)(.+)$", s)
            if m and len(s) < 80:
                if cur:
                    chapters.append((cur_ch, cur))
                n_ch += 1 if cur or chapters else 0
                cur_ch, cur = m.group(2).strip()[:40], []
                continue
            cur.append(s)
        if cur:
            chapters.append((cur_ch, cur))
        text_struct = {}
        js = {"title": title, "heTitle": he_title or title, "schema": {"nodes": []}, "text": {}}
        # build simple structure: node per chapter so labels stay numeric
        js["text"] = {"": [[p for p in paras] for _, paras in chapters]}
        js["schema"] = {"sectionNames": ["Chapter", "Paragraph"]}
        heb = {"text": js["text"][""], "heTitle": js["heTitle"], "schema": js["schema"]}
        # split into he/en by script of each paragraph
        he_t = [[p if H.has_hebrew(p) else "" for p in ch] for ch in heb["text"]]
        en_t = [["" if H.has_hebrew(p) else p for p in ch] for ch in heb["text"]]
        n = self.import_work({"id": work_id, "title": title, "category_path": category, "top_category": category},
                             {"text": he_t, "heTitle": heb["heTitle"], "schema": heb["schema"]},
                             {"text": en_t, "schema": heb["schema"]}, source="user")
        # store chapter names
        with self.lock:
            for i, (name, _) in enumerate(chapters):
                self.db.execute("UPDATE passages SET chapter=? WHERE work_id=? AND chapter=?", (name, work_id, str(i + 1)))
            self.db.commit()
        return n

    # ------------------------------------------------------------------ browsing
    def works(self):
        rows = self.q("SELECT id,title,he_title,category_path,top_category,sort_key,n_passages,n_words,authors,"
                      "he_authors,comp_date,era,source FROM works")
        rows.sort(key=lambda r: (tuple(json.loads(r["sort_key"] or '[9,0,""]')), r["title"]))
        return rows

    def work(self, work_id):
        return self.q1("SELECT * FROM works WHERE id=?", (work_id,))

    def toc(self, work_id):
        return self.q("SELECT node, chapter, MIN(seq) AS first_seq, COUNT(*) AS n FROM passages WHERE work_id=? "
                      "GROUP BY node, chapter ORDER BY first_seq", (work_id,))

    def chapter(self, work_id, node, chapter):
        return self.q("SELECT id,seq,node,chapter,verse,ref,he,en,en_basic FROM passages WHERE work_id=? AND node=? AND chapter=? "
                      "ORDER BY seq", (work_id, node, chapter))

    def passages_range(self, work_id, seq_from, count=200):
        return self.q("SELECT id,seq,node,chapter,verse,ref,he,en,en_basic FROM passages WHERE work_id=? AND seq>=? ORDER BY seq LIMIT ?",
                      (work_id, seq_from, count))

    def passage(self, pid):
        return self.q1("SELECT p.*, w.title, w.he_title, w.category_path FROM passages p JOIN works w ON w.id=p.work_id WHERE p.id=?", (pid,))

    def find_ref(self, ref):
        """Resolve a ref like 'Genesis 1:1', 'Berakhot 2a', 'Rashi on Genesis 1:1' -> first passage."""
        ref = norm_ref(ref)
        r = self.q1("SELECT p.id, p.work_id, p.node, p.chapter, p.ref FROM passages p WHERE ref=? LIMIT 1", (ref,))
        if r:
            return r
        # (a range instead of LIKE 'ref:%' - LIKE cannot use the index and scans all 3.5 million passages)
        r = self.q1("SELECT p.id, p.work_id, p.node, p.chapter, p.ref FROM passages p WHERE ref>=? AND ref<? ORDER BY ref LIMIT 1",
                    (ref + ":", ref + ";"))
        if r:
            return r
        # by Hebrew title / title only
        m = re.match(r"^(.*?)\s+([\dab:]+)$", ref)
        title = m.group(1) if m else ref
        w = self.q1("SELECT id FROM works WHERE title=? OR he_title=?", (title, title))
        if w:
            return self.q1("SELECT id, work_id, node, chapter, ref FROM passages WHERE work_id=? ORDER BY seq LIMIT 1", (w["id"],))
        return None

    # ------------------------------------------------------------------ search
    def _scope_sql(self, scope):
        """scope: {'categories':[...], 'works':[ids], 'exclude_works':[ids], 'era':[...]}"""
        where, args = [], []
        if not scope:
            return "", []
        cats = scope.get("categories") or []
        if cats:
            where.append("(" + " OR ".join("w.category_path LIKE ?" for _ in cats) + ")")
            args += [c + "%" for c in cats]
        if scope.get("works"):
            where.append("p.work_id IN (%s)" % ",".join("?" * len(scope["works"])))
            args += list(scope["works"])
        if scope.get("exclude_works"):
            where.append("p.work_id NOT IN (%s)" % ",".join("?" * len(scope["exclude_works"])))
            args += list(scope["exclude_works"])
        if scope.get("era"):
            where.append("w.era IN (%s)" % ",".join("?" * len(scope["era"])))
            args += list(scope["era"])
        if scope.get("author"):
            where.append("(w.authors LIKE ? OR w.he_authors LIKE ?)")
            args += ["%" + scope["author"] + "%"] * 2
        return (" AND " + " AND ".join(where)) if where else "", args

    def expand_term(self, term, opts):
        """Return set of plain Hebrew words a single query term should match."""
        t = H.letters_only(term)
        out = {t} if t else set()
        if not t:
            return out
        if opts.get("fuzzy"):
            out |= self.fuzzy_words(t)
        if opts.get("prefixes"):
            base = set(out)
            for b in base:
                out |= {p + b for p in PREFIXES}
        return out

    def fuzzy_words(self, w, limit=40):
        """Existing words within edit distance 1 (substitution, deletion, insertion, transposition)."""
        cands = set()
        letters = H.LETTERS + "ךםןףץ"
        for i in range(len(w) + 1):
            for c in letters:
                cands.add(w[:i] + c + w[i:])
            if i < len(w):
                cands.add(w[:i] + w[i + 1:])
                for c in letters:
                    cands.add(w[:i] + c + w[i + 1:])
            if i < len(w) - 1:
                cands.add(w[:i] + w[i + 1] + w[i] + w[i + 2:])
        cands.discard(w)
        found = set()
        cl = list(cands)
        with self.lock:
            for i in range(0, len(cl), 500):
                chunk = cl[i:i + 500]
                for r in self.db.execute("SELECT word FROM words WHERE word IN (%s) ORDER BY freq DESC" % ",".join("?" * len(chunk)), chunk):
                    found.add(r[0])
        return set(list(found)[:limit])

    def wildcard_words(self, pattern, limit=300):
        """Hebrew wildcard: * = any letters, ? = one letter."""
        glob = pattern.replace("?", "?")
        rows = self.q("SELECT word FROM words WHERE word GLOB ? ORDER BY freq DESC LIMIT ?", (glob, limit))
        return {r["word"] for r in rows}

    def root_words(self, root, limit=400):
        """Shoresh search: words built from the root letters (with prefixes, vav/yud/he insertions, suffixes)."""
        r = H.normalize_finals(H.letters_only(root))
        if len(r) < 2:
            return set()
        fin = lambda c: "[" + c + H.TO_FINAL.get(c, "") + "]"
        mid = "[ויהת]{0,2}"
        pat = "^(?:[והבכלמשאתינ]{0,3})" + mid.join(fin(c) for c in r) + "(?:[והיםןתךכנ]{0,3})$"
        rx = re.compile(pat)
        out = []
        like = "%" + "%".join(r) + "%"
        with self.lock:
            for row in self.db.execute("SELECT word FROM words WHERE word LIKE ? ORDER BY freq DESC", (like,)):
                w = H.normalize_finals(row[0])
                if rx.match(w) or rx.match(row[0]):
                    out.append(row[0])
                    if len(out) >= limit:
                        break
        return set(out)

    def parse_query(self, query):
        """Tokenize query into items: ('phrase',[words]) ('term',w) ('or',) ('not',) ('near',n) ('root',w)."""
        toks = []
        for m in re.finditer(r'"([^"]+)"|״([^״]+)״|(NEAR/\d+|NEAR)|(\S+)', query):
            if m.group(1) or m.group(2):
                toks.append(("phrase", (m.group(1) or m.group(2)).split()))
            elif m.group(3):
                n = int(m.group(3).split("/")[1]) if "/" in m.group(3) else 10
                toks.append(("near", n))
            else:
                w = m.group(4)
                if w.upper() in ("OR", "|", "או"):
                    toks.append(("or",))
                elif w.upper() in ("AND", "&", "וגם"):
                    continue
                elif w.upper() in ("NOT", "בלי") :
                    toks.append(("not",))
                elif w.startswith("-") and len(w) > 1:
                    toks.append(("not",)); toks.append(("term", w[1:]))
                elif w.lower().startswith("root:") or w.startswith("שורש:"):
                    toks.append(("root", w.split(":", 1)[1]))
                else:
                    toks.append(("term", w))
        return toks

    def build_match(self, query, lang, opts):
        """Return (fts_expression, set_of_highlight_words)."""
        toks = self.parse_query(query)
        hl = set()
        parts = []
        col_he = "he_skel" if opts.get("malei_chaser") else "he_plain"
        pending_op = None
        i = 0
        while i < len(toks):
            t = toks[i]
            expr = None
            if t[0] in ("or", "not"):
                pending_op = t[0].upper(); i += 1; continue
            if t[0] == "near" and parts and i + 1 < len(toks):
                prev = parts.pop()
                nxt = toks[i + 1]
                bw = nxt[1] if nxt[0] == "term" else " ".join(nxt[1]) if nxt[0] == "phrase" else ""
                b = self._phrase_text(bw, lang, opts)
                a = self._phrase_text(prev[2], lang, opts)
                hl |= set(b.split()) if lang == "he" else {bw}
                if lang == "he" and " " not in a and " " not in b:
                    xa = sorted(self.expand_term(a, opts))[:10]
                    xb = sorted(self.expand_term(b, opts))[:10]
                    hl |= set(xa) | set(xb)
                    if opts.get("malei_chaser"):
                        xa, xb = [skeleton(x) for x in xa], [skeleton(x) for x in xb]
                    expr = "(" + " OR ".join(f"NEAR({_fts_quote(x)} {_fts_quote(y)}, {t[1]})" for x in xa for y in xb) + ")"
                else:
                    expr = f"NEAR({_fts_quote(a)} {_fts_quote(b)}, {t[1]})"
                parts.append((prev[0], expr, a)); i += 2; continue
            if t[0] == "phrase":
                words = t[1]
                ptxt = self._phrase_text(" ".join(words), lang, opts)
                hl |= set(ptxt.split()) if lang == "he" else set(words)
                expr = _fts_quote(ptxt)
                if lang == "he" and opts.get("acronyms"):
                    ab = self.abbrev_for_phrase(ptxt)
                    if ab:
                        expr = f"({expr} OR {_fts_quote(ab)})"; hl.add(ab)
            elif t[0] == "root":
                ws = self.root_words(t[1]) or {H.letters_only(t[1])}
                hl |= ws
                expr = "(" + " OR ".join(_fts_quote(w) for w in sorted(ws)) + ")"
            elif t[0] == "term":
                w = t[1]
                if lang == "en":
                    hl.add(w.strip("*"))
                    expr = (_fts_quote(w[:-1]) + "*") if w.endswith("*") else _fts_quote(w)
                else:
                    if "*" in w or "?" in w:
                        ws = self.wildcard_words("".join(c for c in w if c in "*?" or "א" <= c <= "ת"))
                    else:
                        ws = self.expand_term(w, opts)
                    if opts.get("acronyms"):
                        lw = H.normalize_finals(H.letters_only(w))
                        if lw in ABBREV_CLEAN:
                            ws = set(ws)
                            hl |= set(ABBREV_CLEAN[lw].split())
                            exp_phrase = _fts_quote(ABBREV_CLEAN[lw])
                        else:
                            exp_phrase = None
                    else:
                        exp_phrase = None
                    if not ws:
                        ws = {"אאאאא"}
                    hl |= ws
                    if opts.get("malei_chaser"):
                        ws = {skeleton(x) for x in ws}
                    expr = "(" + " OR ".join(_fts_quote(x) for x in sorted(ws)[:400]) + (" OR " + exp_phrase if exp_phrase else "") + ")"
            if expr is None:
                i += 1; continue
            raw = t[1] if t[0] in ("term", "root") else " ".join(t[1]) if t[0] == "phrase" else ""
            parts.append((pending_op or "AND", expr, raw))
            pending_op = None
            i += 1
        if not parts:
            return None, hl
        out = parts[0][1]
        for op, e, _ in parts[1:]:
            out = f"({out}) {op} {e}" if op != "AND" else f"{out} AND {e}"
        if lang == "he":
            out = "{%s} : (%s)" % (col_he, out)
        return out, hl

    def _phrase_text(self, s, lang, opts):
        if lang == "en":
            return s
        ws = H.plain_words(s)
        if opts.get("malei_chaser"):
            ws = [skeleton(w) for w in ws]
        return " ".join(ws)

    def abbrev_for_phrase(self, phrase):
        for k, v in ABBREV_CLEAN.items():
            if H.he_plain(v) == phrase:
                return H.fix_final_letters(k)
        return None

    def search(self, query, lang="auto", opts=None, scope=None, offset=0, limit=50, sort="book"):
        opts = opts or {}
        query = query.strip()
        if not query:
            return {"total": 0, "results": [], "lang": lang}
        if lang == "auto":
            lang = H.detect_lang(re.sub(r"\b(root|NEAR|AND|OR|NOT)\b[:/\d]*", "", query))
        if opts.get("regex"):
            return self.regex_search(query, lang, scope, offset, limit)
        if lang == "en" and opts.get("cross_lingual"):
            pass  # handled by caller: also searches Hebrew results of English translations (default behaviour)
        match, hl = self.build_match(query, lang, opts)
        if not match:
            return {"total": 0, "results": [], "lang": lang}
        table = "fts_he" if lang == "he" else "fts_en"
        ssql, sargs = self._scope_sql(scope)
        base = f"FROM {table} f JOIN passages p ON p.id=f.rowid JOIN works w ON w.id=p.work_id WHERE {table} MATCH ? {ssql}"
        t0 = time.time()
        try:
            total = self.q1(f"SELECT COUNT(*) AS n {base}", [match] + sargs)["n"]
            order = "ORDER BY rank" if sort == "relevance" else "ORDER BY w.sort_key, w.title, p.seq"
            rows = self.q(f"SELECT p.id, p.ref, p.he, p.en, p.work_id, p.node, p.chapter, p.verse, w.title, w.he_title, "
                          f"w.category_path {base} {order} LIMIT ? OFFSET ?", [match] + sargs + [limit, offset])
        except sqlite3.OperationalError as e:
            return {"total": 0, "results": [], "lang": lang, "error": f"Query error: {e}"}
        for r in rows:
            r["he_html"] = self.highlight_he(r["he"], hl, opts.get("malei_chaser"))
            r["en_html"] = self.highlight_en(r["en"], hl if lang == "en" else set())
        return {"total": total, "results": rows, "lang": lang, "terms": sorted(hl)[:50],
                "ms": int((time.time() - t0) * 1000), "match": match}

    def regex_search(self, pattern, lang, scope, offset, limit):
        try:
            re.compile(pattern)
        except re.error as e:
            return {"total": 0, "results": [], "error": f"Bad regex: {e}"}
        col = "p.he_plain" if lang == "he" else "p.en"
        ssql, sargs = self._scope_sql(scope)
        rows = self.q(f"SELECT p.id,p.ref,p.he,p.en,p.work_id,p.node,p.chapter,p.verse,w.title,w.he_title,w.category_path "
                      f"FROM passages p JOIN works w ON w.id=p.work_id WHERE {col} REGEXP ? {ssql} "
                      f"ORDER BY w.sort_key, p.seq LIMIT ? OFFSET ?", [pattern] + sargs + [limit + 1, offset])
        more = len(rows) > limit
        rows = rows[:limit]
        rx = re.compile(pattern)
        for r in rows:
            if lang == "he":
                hits = set()
                for m in rx.finditer(" ".join(H.plain_words(r["he"]))):
                    hits |= set(m.group(0).split())
                r["he_html"] = self.highlight_he(r["he"], hits)
                r["en_html"] = _esc(r["en"])
            else:
                r["he_html"] = _esc(r["he"])
                r["en_html"] = rx.sub(lambda m: "<mark>" + m.group(0) + "</mark>", _esc(r["en"]))
        return {"total": offset + len(rows) + (1 if more else 0), "results": rows, "lang": lang, "approx": True}

    def cross_line_phrase(self, phrase, scope=None, limit=100):
        """Find a phrase that is split between the end of one passage and the start of the next."""
        words = H.plain_words(phrase)
        out = []
        if len(words) < 2:
            return out
        ssql, sargs = self._scope_sql(scope)
        for k in range(1, len(words)):
            head, tail = words[:k], words[k:]
            m = "{he_plain} : " + _fts_quote(" ".join(head))
            rows = self.q(f"SELECT p.id,p.work_id,p.seq,p.he_plain,p.ref FROM fts_he f JOIN passages p ON p.id=f.rowid "
                          f"JOIN works w ON w.id=p.work_id WHERE fts_he MATCH ? {ssql} LIMIT 3000", [m] + sargs)
            for r in rows:
                if r["he_plain"].split()[-k:] == head:
                    nxt = self.q1("SELECT id,ref,he_plain FROM passages WHERE work_id=? AND seq=?", (r["work_id"], r["seq"] + 1))
                    if nxt and nxt["he_plain"].split()[:len(tail)] == tail:
                        out.append({"from": r["ref"], "to": nxt["ref"], "id": r["id"], "next_id": nxt["id"]})
                        if len(out) >= limit:
                            return out
        return out

    def search_compare(self, query, scope_a, scope_b, lang="auto", opts=None):
        a = self.search(query, lang, opts, scope_a, limit=20)
        b = self.search(query, lang, opts, scope_b, limit=20)
        return {"a": a, "b": b}

    # ------------------------------------------------------------------ highlighting
    def highlight_he(self, text, words, skel=False, idx_ranges=None, cls="hl"):
        """Wrap matching Hebrew words (by plain form) or word-index ranges in <mark>."""
        if not text:
            return ""
        words = {H.normalize_finals(w) for w in (words or set())}
        out, last, idx = [], 0, 0
        for s, e, p in H.word_units(text):
            out.append(_esc(text[last:s]))
            seg = _esc(text[s:e])
            np = H.normalize_finals(p)
            hit = (np in words) or (skel and H.normalize_finals(skeleton(p)) in words)
            if idx_ranges:
                hit = any(a <= idx <= b for a, b in idx_ranges)
            out.append(f"<mark class='{cls}'>{seg}</mark>" if hit else seg)
            last, idx = e, idx + 1
        out.append(_esc(text[last:]))
        return "".join(out)

    @staticmethod
    def highlight_en(text, terms):
        t = _esc(text or "")
        terms = [x for x in terms if x and re.match(r"[A-Za-z]", x)]
        if not terms:
            return t
        stems = sorted({re.escape(x.lower().rstrip("*")[:max(3, len(x) - 2)] if len(x) > 4 else x.lower().rstrip("*")) for x in terms}, key=len, reverse=True)
        return re.sub(r"\b(" + "|".join(stems) + r")\w*", lambda m: "<mark class='hl'>" + m.group(0) + "</mark>", t, flags=re.I)

    # ------------------------------------------------------------------ gematria
    def gematria_words(self, value, method="Standard (Mispar Hechrachi)", limit=500):
        col = H.INDEXED_METHODS.get(method)
        if col:
            return self.q(f"SELECT word, freq FROM words WHERE {col}=? ORDER BY freq DESC LIMIT ?", (value, limit))
        fn = H.GEMATRIA_METHODS[method]
        out = []
        with self.lock:
            for w, f in self.db.execute("SELECT word, freq FROM words"):
                if fn(w) == value:
                    out.append({"word": w, "freq": f})
        out.sort(key=lambda r: -r["freq"])
        return out[:limit]

    def passages_with_words(self, words, scope=None, offset=0, limit=50):
        if not words:
            return {"total": 0, "results": []}
        words = list(words)[:300]
        match = "{he_plain} : (" + " OR ".join(_fts_quote(w) for w in words) + ")"
        ssql, sargs = self._scope_sql(scope)
        base = f"FROM fts_he f JOIN passages p ON p.id=f.rowid JOIN works w ON w.id=p.work_id WHERE fts_he MATCH ? {ssql}"
        total = self.q1(f"SELECT COUNT(*) n {base}", [match] + sargs)["n"]
        rows = self.q(f"SELECT p.id,p.ref,p.he,p.en,w.title,w.he_title,p.work_id {base} ORDER BY w.sort_key, p.seq LIMIT ? OFFSET ?",
                      [match] + sargs + [limit, offset])
        ws = set(words)
        for r in rows:
            r["he_html"] = self.highlight_he(r["he"], ws)
            r["en_html"] = _esc(r["en"])
        return {"total": total, "results": rows}

    def _work_ids(self, scope):
        """Works in library order (Tanach first …), limited to the scope."""
        ssql, sargs = self._scope_sql(scope)
        ssql = ssql.replace("p.work_id", "w.id")
        return [r["id"] for r in self.q(f"SELECT w.id FROM works w WHERE w.n_passages>0 {ssql} ORDER BY w.sort_key", sargs)]

    def _stream(self, cols, scope, where="", args=()):
        """Go through the passages work by work (using the index), so we can stop as soon as we have enough
        instead of loading 3.5 million passages into memory."""
        ids = self._work_ids(scope)
        db = self._reader()
        titles = {r["id"]: r for r in self.q("SELECT id, title, he_title FROM works")}
        for n, wid in enumerate(ids):
            for r in db.execute(f"SELECT {cols} FROM passages p WHERE p.work_id=? {where} ORDER BY p.seq", (wid, *args)):
                yield n, len(ids), titles.get(wid, {}), r

    def gematria_phrases(self, value, method, min_words=2, max_words=4, scope=None, limit=300, progress=None, cancel=None):
        """Scan for consecutive word sequences whose value equals `value` (verses or phrases)."""
        fn = H.GEMATRIA_METHODS[method]
        out = []
        cache = self._gem_cache.setdefault(method, {})
        if len(cache) > 400000:
            cache.clear()
        last = -1
        for n, total, w, r in self._stream("p.id, p.ref, p.he_plain", scope):
            if n != last:
                last = n
                if cancel and cancel():
                    break
                if progress:
                    progress(n, total)
            ws = (r["he_plain"] or "").split()
            vals = []
            for x in ws:
                v = cache.get(x)
                if v is None:
                    v = cache[x] = fn(x)
                vals.append(v)
            hits = []
            if sum(vals) == value and len(ws) > max_words:
                hits.append(None)
            for i in range(len(vals)):
                t = 0
                for j in range(i, min(i + max_words, len(vals))):
                    t += vals[j]
                    if t > value and method != "Katan Mispari (digital root)":
                        break
                    if t == value and j - i + 1 >= min_words:
                        hits.append((i, j))
            if hits:
                he = self.q1("SELECT he FROM passages WHERE id=?", (r["id"],))["he"]
                for h in hits:
                    if h is None:
                        out.append({"id": r["id"], "ref": r["ref"], "phrase": "(entire passage)", "he_html": _esc(he), "title": w.get("title")})
                    else:
                        out.append({"id": r["id"], "ref": r["ref"], "phrase": " ".join(ws[h[0]:h[1] + 1]), "title": w.get("title"),
                                    "he_html": self.highlight_he(he, set(), idx_ranges=[h])})
            if len(out) >= limit:
                break
        if progress:
            progress(1, 1)
        return out[:limit]

    # ------------------------------------------------------------------ roshei / sofei teivos
    def roshei_teivos(self, letters, mode="roshei", scope=None, limit=200, offset=0, skip_words=0):
        target = H.normalize_finals(H.letters_only(letters))
        if not target:
            return {"total": 0, "results": [], "expansions": []}
        col = "initials" if mode == "roshei" else "finals"
        ssql, sargs = self._scope_sql(scope)
        rows, seen = [], 0
        t0 = time.time()
        more = False
        for n, total, w, r in self._stream(f"p.id, p.ref, p.he, p.en, p.work_id, p.{col} AS key", scope, f"AND instr(p.{col}, ?) > 0", (target,)):
            seen += 1
            if seen <= offset:
                continue
            if len(rows) >= limit or time.time() - t0 > 20:
                more = True
                break
            rows.append({**dict(r), "title": w.get("title"), "he_title": w.get("he_title")})
        total = offset + len(rows) + (1 if more else 0)
        for r in rows:
            ranges, start = [], 0
            while True:
                k = r["key"].find(target, start)
                if k < 0:
                    break
                ranges.append((k, k + len(target) - 1))
                start = k + 1
            r["he_html"] = self.highlight_he(r["he"], set(), idx_ranges=ranges, cls="rt")
            words = H.plain_words(r["he"])
            r["phrases"] = [" ".join(words[a:b + 1]) for a, b in ranges]
            r["en_html"] = _esc(r["en"])
            del r["key"]
        exp = []
        if target in ABBREV_CLEAN:
            exp.append(ABBREV_CLEAN[target])
        return {"total": total, "results": rows, "expansions": exp, "approx": more}

    # ------------------------------------------------------------------ ELS (dilugim)
    def els(self, word, work_id, min_skip=2, max_skip=500, limit=100, cancel=None):
        target = H.normalize_finals(H.letters_only(word))
        rows = self.q("SELECT id, ref, he_plain FROM passages WHERE work_id=? ORDER BY seq", (work_id,))
        letters, owners = [], []
        for r in rows:
            for c in (r["he_plain"] or "").replace(" ", ""):
                letters.append(H.normalize_finals(c)); owners.append(r["ref"])
        s = "".join(letters)
        out = []
        n, L = len(s), len(target)
        for skip in range(min_skip, max_skip + 1):
            for sign in (1, -1):
                st = skip * sign
                for start in range(n):
                    end = start + st * (L - 1)
                    if end < 0 or end >= n:
                        continue
                    if s[start] == target[0] and all(s[start + st * k] == target[k] for k in range(1, L)):
                        out.append({"skip": st, "start_ref": owners[start], "end_ref": owners[end], "position": start})
                        if len(out) >= limit:
                            return out
                if cancel and cancel():
                    return out
        return out

    # ------------------------------------------------------------------ links
    def import_links_csv(self, path, only_known=True, progress=None):
        titles = {r["title"] for r in self.q("SELECT title FROM works")}
        n = 0
        with open(path, encoding="utf-8", newline="") as f, self.lock:
            rd = csv.reader(f)
            next(rd, None)
            batch = []
            for row in rd:
                if len(row) < 5:
                    continue
                r1, r2, typ, t1, t2 = row[:5]
                c1 = row[5] if len(row) > 5 else ""
                c2 = row[6] if len(row) > 6 else ""
                if only_known and t1 not in titles and t2 not in titles:
                    continue
                batch.append((norm_ref(r1), norm_ref(r2), typ, c1, c2))
                if len(batch) >= 5000:
                    self.db.executemany("INSERT INTO links VALUES(?,?,?,?,?)", batch); n += len(batch); batch = []
                    if progress:
                        progress(n)
            if batch:
                self.db.executemany("INSERT INTO links VALUES(?,?,?,?,?)", batch); n += len(batch)
            self.db.commit()
        return n

    def connections(self, ref, limit=400):
        """Commentaries/links for a passage ref, grouped by work, with text if available locally."""
        refs = [ref]
        parts = ref.rsplit(":", 1)
        if len(parts) == 2:
            refs.append(parts[0])  # section-level links
        rows = []
        for r in refs:
            rows += self.q("SELECT ref2 AS other, type, cat2 AS cat FROM links WHERE ref1=? LIMIT ?", (r, limit))
            rows += self.q("SELECT ref1 AS other, type, cat1 AS cat FROM links WHERE ref2=? LIMIT ?", (r, limit))
        # links written for a range that includes this passage (e.g. a commentary on Genesis 1:1-3 when reading 1:2)
        if len(parts) == 2 and parts[1].isdigit():
            n = int(parts[1])
            for side, oth, cat in (("ref1", "ref2", "cat2"), ("ref2", "ref1", "cat1")):
                for l in self.q(f"SELECT {side} AS me, {oth} AS other, type, {cat} AS cat FROM links WHERE {side}>=? AND {side}<? "
                                f"AND instr({side}, '-')>0 LIMIT 2000", (parts[0] + ":", parts[0] + ";")):
                    m = re.fullmatch(r"(\d+)-(\d+)", l["me"][len(parts[0]) + 1:])
                    if m and int(m.group(1)) <= n <= int(m.group(2)):
                        rows.append({"other": l["other"], "type": l["type"], "cat": l["cat"]})
        seen, groups = set(), defaultdict(list)
        for l in rows:
            if l["other"] in seen:
                continue
            seen.add(l["other"])
            o = l["other"]
            if "-" in o.rsplit(" ", 1)[-1]:
                texts = self._range_texts(o)
                title = texts[0]["title"] if texts else re.sub(r"\s[\d:ab\-]+$", "", o)
                groups[title].append({"ref": o, "type": l["type"], "cat": l["cat"], "texts": texts})
                continue
            texts = self.q("SELECT * FROM (SELECT p.id, p.seq, p.ref, p.he, p.en, w.title, w.he_title FROM passages p JOIN works w ON w.id=p.work_id "
                           "WHERE p.ref=? UNION ALL SELECT p.id, p.seq, p.ref, p.he, p.en, w.title, w.he_title FROM passages p "
                           "JOIN works w ON w.id=p.work_id WHERE p.ref>=? AND p.ref<?) ORDER BY seq LIMIT 30", (o, o + ":", o + ";"))
            title = texts[0]["title"] if texts else re.sub(r"\s[\d:ab]+$", "", l["other"])
            groups[title].append({"ref": l["other"], "type": l["type"], "cat": l["cat"], "texts": texts})
        from .order import he_name
        return [{"title": k, "he_title": he_name(k), "items": v, "local": any(i["texts"] for i in v)} for k, v in
                sorted(groups.items(), key=lambda kv: (not any(i["texts"] for i in kv[1]), kv[0]))]

    def _range_texts(self, o):
        """Text of a range like 'Ramban on Genesis 1:1:1-4', 'Berakhot 2a:3-2b:4'."""
        head, tail = o.rsplit("-", 1)
        base, last = head.rsplit(" ", 1)
        a_parts, t_parts = last.split(":"), tail.split(":")
        end = base + " " + ":".join(a_parts[:len(a_parts) - len(t_parts)] + t_parts)
        first = lambda r: self.q1("SELECT p.work_id, p.seq FROM passages p WHERE p.ref=? OR (p.ref>=? AND p.ref<?) ORDER BY p.seq LIMIT 1",
                                  (r, r + ":", r + ";"))
        last_ = lambda r: self.q1("SELECT p.work_id, p.seq FROM passages p WHERE p.ref=? OR (p.ref>=? AND p.ref<?) ORDER BY p.seq DESC LIMIT 1",
                                  (r, r + ":", r + ";"))
        a, b = first(head), last_(end)
        if not a:
            return []
        hi = b["seq"] if b and b["work_id"] == a["work_id"] else a["seq"]
        return self.q("SELECT p.id, p.seq, p.ref, p.he, p.en, w.title, w.he_title FROM passages p JOIN works w ON w.id=p.work_id "
                      "WHERE p.work_id=? AND p.seq BETWEEN ? AND ? ORDER BY p.seq LIMIT 30", (a["work_id"], a["seq"], max(hi, a["seq"])))

    def user_link_targets(self, refs):
        return [self.find_ref(r) for r in refs]

    # ------------------------------------------------------------------ statistics & analysis
    def work_stats(self, work_id):
        rows = self.q("SELECT he_plain, en FROM passages WHERE work_id=?", (work_id,))
        words, letters, en_words = Counter(), Counter(), 0
        for r in rows:
            ws = (r["he_plain"] or "").split()
            words.update(ws)
            for w in ws:
                letters.update(H.normalize_finals(w))
            en_words += len((r["en"] or "").split())
        total = sum(words.values())
        return {"passages": len(rows), "hebrew_words": total, "unique_words": len(words), "english_words": en_words,
                "letters": sum(letters.values()), "avg_word_len": round(sum(letters.values()) / total, 2) if total else 0,
                "lexical_density": round(len(words) / total, 3) if total else 0,
                "top_words": words.most_common(60), "letter_freq": sorted(letters.items(), key=lambda x: H.LETTERS.index(x[0]))}

    def cooccurrence(self, a, b, scope=None, unit="chapter"):
        """How often two words appear in the same passage and in the same chapter."""
        ssql, sargs = self._scope_sql(scope)
        m = "{he_plain} : (%s AND %s)" % (_fts_quote(H.letters_only(a)), _fts_quote(H.letters_only(b)))
        same_passage = self.q1(f"SELECT COUNT(*) n FROM fts_he f JOIN passages p ON p.id=f.rowid JOIN works w ON w.id=p.work_id "
                               f"WHERE fts_he MATCH ? {ssql}", [m] + sargs)["n"]

        def chapters(word):
            mm = "{he_plain} : " + _fts_quote(H.letters_only(word))
            return {(r["work_id"], r["node"], r["chapter"]) for r in self.q(
                f"SELECT p.work_id,p.node,p.chapter FROM fts_he f JOIN passages p ON p.id=f.rowid JOIN works w ON w.id=p.work_id "
                f"WHERE fts_he MATCH ? {ssql}", [mm] + sargs)}
        ca, cb = chapters(a), chapters(b)
        both = ca & cb
        by_work = Counter(k[0] for k in both)
        names = {r["id"]: r["title"] for r in self.q("SELECT id,title FROM works")}
        return {"same_passage": same_passage, "chapters_a": len(ca), "chapters_b": len(cb), "same_chapter": len(both),
                "jaccard": round(len(both) / len(ca | cb), 3) if ca | cb else 0,
                "by_work": [(names.get(k, k), v) for k, v in by_work.most_common(20)]}

    def word_cloud(self, query, lang="he", scope=None, opts=None, top=60):
        """Most frequent neighbouring words around search hits."""
        res = self.search(query, lang, opts or {}, scope, limit=1000)
        stop = {"את", "של", "על", "אל", "כי", "לא", "אשר", "הוא", "היא", "זה", "אם", "כל", "גם", "או", "עם", "מן", "יהוה",
                "the", "and", "of", "to", "a", "in", "that", "is", "he", "his", "for", "it", "with", "as", "was", "i", "you", "they", "be", "not", "him", "said", "unto"}
        c = Counter()
        terms = set(res.get("terms", []))
        for r in res["results"]:
            ws = H.plain_words(r["he"]) if res["lang"] == "he" else re.findall(r"[a-zA-Z']+", (r["en"] or "").lower())
            c.update(w for w in ws if w not in stop and w not in terms and len(w) > 1)
        return c.most_common(top)

    def citation_network(self, limit=40):
        """Which works link to which (counts), from the links table (worked out once, then remembered)."""
        key = ("net", limit, self.q1("SELECT COALESCE(MAX(rowid),0) n FROM links")["n"])
        if getattr(self, "_net", (None,))[0] == key:
            return self._net[1]
        rows = self.q("SELECT ref1, ref2 FROM links LIMIT 400000")
        c = Counter()
        strip = lambda r: re.sub(r"\s[\d:ab]+$", "", r).split(",")[0]
        for r in rows:
            a, b = strip(r["ref1"]), strip(r["ref2"])
            if a != b:
                c[(a, b)] += 1
        res = [{"a": a, "b": b, "n": n} for (a, b), n in c.most_common(limit)]
        self._net = (key, res)
        return res

    def category_histogram(self, query, lang="auto", opts=None):
        res_lang = H.detect_lang(query) if lang == "auto" else lang
        match, _ = self.build_match(query, res_lang, opts or {})
        if not match:
            return []
        table = "fts_he" if res_lang == "he" else "fts_en"
        return self.q(f"SELECT w.top_category AS cat, COUNT(*) n FROM {table} f JOIN passages p ON p.id=f.rowid "
                      f"JOIN works w ON w.id=p.work_id WHERE {table} MATCH ? GROUP BY 1 ORDER BY 2 DESC", (match,))

    def era_histogram(self, query, lang="auto", opts=None):
        res_lang = H.detect_lang(query) if lang == "auto" else lang
        match, _ = self.build_match(query, res_lang, opts or {})
        if not match:
            return []
        table = "fts_he" if res_lang == "he" else "fts_en"
        return self.q(f"SELECT COALESCE(NULLIF(w.era,''),'Unknown') AS era, COUNT(*) n FROM {table} f JOIN passages p ON p.id=f.rowid "
                      f"JOIN works w ON w.id=p.work_id WHERE {table} MATCH ? GROUP BY 1 ORDER BY 2 DESC", (match,))

    def compare_versions(self, ref_list):
        return [self.q1("SELECT p.ref, p.he, p.en, w.title FROM passages p JOIN works w ON w.id=p.work_id WHERE p.ref=?", (r,))
                for r in ref_list]

    def stats(self):
        # fast counts (COUNT(*) over millions of rows takes seconds on a big library)
        return {"works": self.q1("SELECT COUNT(*) n FROM works")["n"],
                "passages": self.q1("SELECT COALESCE(SUM(n_passages),0) n FROM works")["n"],
                "words": self._words_count(),
                "links": self.q1("SELECT COALESCE(MAX(rowid),0) n FROM links")["n"],
                "size_mb": round(os.path.getsize(self.path) / 1e6, 1) if os.path.exists(self.path) else 0}

    def _words_count(self):
        n = self.q1("SELECT COALESCE(SUM(n_passages),0) n FROM works")["n"]
        if getattr(self, "_wc", (None,))[0] != n:
            self._wc = (n, self.q1("SELECT COUNT(*) n FROM words")["n"])
        return self._wc[1]

    def compact(self):
        with self.lock:
            self.db.execute("INSERT INTO fts_he(fts_he) VALUES('optimize')")
            self.db.execute("INSERT INTO fts_en(fts_en) VALUES('optimize')")
            self.db.commit()
            self.db.execute("VACUUM")
        return self.stats()


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- citation parser
BOOK_ALIASES = None


def detect_citations(text, titles):
    """Find references like 'Genesis 1:1', 'Berakhot 2a', 'בראשית א:א' in free text."""
    global BOOK_ALIASES
    out = []
    names = sorted(titles, key=len, reverse=True)
    if not names:
        return out
    rx = re.compile(r"(?<![\wא-ת])(" + "|".join(re.escape(n) for n in names[:3000]) +
                    r")\s+((?:\d+[ab]?|[א-ת]{1,3}[\"׳״']?[א-ת]?)(?:[:,.]\s?(?:\d+|[א-ת]{1,3}[\"׳״']?[א-ת]?)){0,2})")
    for m in rx.finditer(text):
        loc = m.group(2)
        parts = re.split(r"[:,.]\s?", loc)
        conv = []
        for p in parts:
            if re.match(r"^\d+[ab]?$", p):
                conv.append(p)
            else:
                pl = H.letters_only(p)
                conv.append(str(H.g_standard(pl)) if pl else p)
        out.append({"text": m.group(0), "title": m.group(1), "ref": m.group(1) + " " + ":".join(conv),
                    "start": m.start(), "end": m.end()})
    return out
