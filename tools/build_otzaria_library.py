"""Build the complete library from the Otzaria library (github.com/Sivan22/otzaria-library):
every sefer in Otzaria's format (headings + lines), Otzaria's own links (commentaries, mefarshim, targum),
Hebrew names and categories as in Otzaria - and the English translation attached wherever an earlier library
(--english library.sqlite) had one for the same sefer.

    python tools/build_otzaria_library.py <otzaria>/אוצריא --links <otzaria>/links --english old.sqlite --out library.sqlite
"""
import argparse, glob, html, json, os, re, sqlite3, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.library import Library  # noqa: E402
from core import hebrew as H  # noqa: E402
from core.order import sort_key  # noqa: E402

TAG = re.compile(r"<[^>]+>")
HEAD = re.compile(r"^\s*<h([1-6])[^>]*>(.*?)</h\1>\s*$", re.I)
NUM = r"([א-ת][א-ת\"'׳״]{0,4})"
TOP_EN = {"תנך": "Tanakh", "תנ\"ך": "Tanakh", "תורה שבכתב": "Tanakh", "משנה": "Mishnah", "תלמוד בבלי": "Talmud", "תלמוד ירושלמי": "Talmud",
          "תלמוד": "Talmud", "הלכה": "Halakhah", "מדרש": "Midrash", "קבלה": "Kabbalah", "חסידות": "Chasidut", "מוסר": "Musar",
          "מחשבת ישראל": "Jewish Thought", "שות": "Responsa", "שו\"ת": "Responsa", "ספרות עזר": "Reference", "סידור": "Liturgy",
          "תפילה": "Liturgy", "ראשונים": "Rishonim", "אחרונים": "Acharonim", "תוספתא": "Tosefta"}


def norm(t):
    t = re.sub(r"[֑-ׇ\"'״׳.,\-–()\[\]]", "", t or "")
    return re.sub(r"\s+", " ", t).strip()


def num(s):
    return H.g_standard(re.sub(r"[^א-ת]", "", s or ""))


def label(h, daf=True):
    """Otzaria headings -> the labels references use: 'דף ב.' -> '2a', 'דף ב:' -> '2b', 'פרק ג' / 'סימן ג' -> '3'."""
    t = html.unescape(TAG.sub("", h)).strip()
    m = daf and re.match(rf"^(?:דף\s+)?{NUM}\s*(?:(\.|:|׃)|,?\s*(?:עמוד|ע\"?)?\s*([אב])['׳]?)\s*$", t) or (daf and re.match(rf"^דף\s+{NUM}\s*()()$", t))
    if m:
        n = num(m.group(1))
        b = m.group(2) in (":", "׃") or m.group(3) == "ב"
        return f"{n}{'b' if b else 'a'}" if n else t
    m = re.match(rf"^(?:פרק|סימן|מזמור|הלכה|סעיף|משנה|פסוק|אות|פרשה|שער|מאמר)\s+{NUM}\s*$", t)
    if m and num(m.group(1)):
        return str(num(m.group(1)))
    return t[:80]


def parse(path, daf=False):
    """-> (title, rows [{node, chapter, verse, he, line}])   line = 1-based line number in the file (Otzaria's links use it)."""
    try:
        text = open(path, encoding="utf-8").read()
    except UnicodeDecodeError:
        text = open(path, encoding="cp1255", errors="replace").read()
    title = os.path.splitext(os.path.basename(path))[0]
    heads, rows, counter = {}, [], {}
    for ln, line in enumerate(text.splitlines(), 1):
        m = HEAD.match(line)
        if m:
            lvl = int(m.group(1))
            if lvl == 1:
                title = html.unescape(TAG.sub("", m.group(2))).strip() or title
                continue
            heads[lvl] = label(m.group(2), daf)
            for k in [k for k in heads if k > lvl]:
                del heads[k]
            continue
        s = html.unescape(TAG.sub("", line)).strip()
        if not s:
            continue
        lv = sorted(heads)
        chapter = heads[lv[-1]] if lv else ""
        node = ", ".join(heads[k] for k in lv[:-1])[:150]
        counter[(node, chapter)] = counter.get((node, chapter), 0) + 1
        rows.append({"node": node, "chapter": chapter, "verse": counter[(node, chapter)], "he": s, "line": ln})
    return title, rows


def english_map(eng_db):
    """Hebrew title -> (English title, category, {(node, chapter): [(verse, en, en_basic)]}) from the earlier library."""
    if not eng_db or not os.path.exists(eng_db):
        return {}, None
    db = sqlite3.connect(eng_db)
    db.row_factory = sqlite3.Row
    titles = {}
    for w in db.execute("SELECT id, title, he_title, category_path, top_category FROM works"):
        if w["he_title"]:
            titles.setdefault(norm(w["he_title"]), dict(w))
    return titles, db


def attach_english(rows, src_db, wid):
    """Put the English of the same sefer on the Otzaria lines: chapter by chapter; when the two divide a chapter
    differently (e.g. a daf), the English is spread over the lines in proportion to the Hebrew length."""
    by_ch = {}
    for r in src_db.execute("SELECT chapter, verse, he_plain, en, en_basic FROM passages WHERE work_id=? AND en != '' ORDER BY seq", (wid,)):
        by_ch.setdefault(r["chapter"], []).append(r)
    if not by_ch:
        return 0
    mine = {}
    for i, r in enumerate(rows):
        mine.setdefault(r["chapter"], []).append(i)
    n = 0
    for ch, idx in mine.items():
        src = by_ch.get(ch)
        if not src:
            continue
        if len(src) == len(idx):
            for i, s in zip(idx, src):
                rows[i]["en"], rows[i]["en_basic"] = s["en"], s["en_basic"]
                n += 1
            continue
        # proportional spread by Hebrew length
        tot_a = sum(len(rows[i]["he"]) for i in idx) or 1
        tot_b = sum(len(s["he_plain"] or "") for s in src) or 1
        pos_a, cum = [], 0
        for i in idx:
            cum += len(rows[i]["he"])
            pos_a.append(cum / tot_a)
        cum, buckets = 0, {i: [] for i in idx}
        for s in src:
            mid = (cum + len(s["he_plain"] or "") / 2) / tot_b
            cum += len(s["he_plain"] or "")
            k = next((j for j, p in enumerate(pos_a) if mid <= p), len(idx) - 1)
            buckets[idx[k]].append(s)
        for i, ss in buckets.items():
            if ss:
                rows[i]["en"] = " ".join(x["en"] for x in ss)
                rows[i]["en_basic"] = " ".join(x["en_basic"] for x in ss if x["en_basic"]) or None
                n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--links")
    ap.add_argument("--english")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    lib = Library(a.out)
    titles, src = english_map(a.english)
    files = sorted(glob.glob(os.path.join(a.root, "**", "*.txt"), recursive=True))[: a.limit or None]
    print(len(files), "seforim;", len(titles), "known English titles", flush=True)
    line_ref = {}      # (file stem, line) -> ref
    stems = {}         # file stem -> (work id, title, top)
    t0, wid, n_en = time.time(), 1, 0
    for i, f in enumerate(files):
        rel = os.path.relpath(f, a.root).split(os.sep)
        try:
            he_title, rows = parse(f, any(x in "/".join(rel) for x in ("תלמוד", "בבלי", "ירושלמי", "גמרא")))
        except Exception as e:  # noqa
            print("skip", f, e)
            continue
        if not rows:
            continue
        stem = os.path.splitext(os.path.basename(f))[0]
        known = titles.get(norm(he_title)) or titles.get(norm(stem))
        title = known["title"] if known else he_title
        cats = rel[:-1]
        top = TOP_EN.get(cats[0], cats[0]) if cats else "Other"
        # references like the printed seforim: "Berakhot 2a:3" (no perek in a daf ref), "Genesis 1:1" (no parasha)
        for r in rows:
            if r["node"] and (re.fullmatch(r"\d+[ab]", r["chapter"]) or top == "Tanakh"):
                r["node"] = ""
        seen = {}
        for r in rows:
            k = (r["node"], r["chapter"])
            seen[k] = seen.get(k, 0) + 1
            r["verse"] = seen[k]
        if known and src is not None:
            n_en += attach_english(rows, src, known["id"]) > 0
        work = {"id": wid, "title": title, "he_title": he_title, "top_category": top,
                "category_path": " > ".join([top] + cats[1:]) if cats else top,
                "sort_key": sort_key(title) if known else [9, cats, he_title]}
        ids = lib.import_rows(work, rows, commit=(i % 50 == 0))
        for r, pid in zip(rows, ids):
            line_ref[(stem, r["line"])] = pid
        stems[stem] = (wid, title, top)
        wid += 1
        if i % 200 == 0:
            print(f"{i}/{len(files)} · {int(time.time() - t0)} s · with English: {n_en}", flush=True)
    lib.db.commit()
    # ---- Otzaria's links -> the links table (refs on both sides)
    refs = {}
    if a.links and os.path.isdir(a.links):
        pid_ref = {r[0]: r[1] for r in lib.db.execute("SELECT id, ref FROM passages")}
        cat_of = {s: v[2] for s, v in stems.items()}
        lines_of = {}
        for (stem, ln), pid in line_ref.items():
            lines_of.setdefault(stem, []).append((ln, pid))
        for v in lines_of.values():
            v.sort()

        def ref_at(stem, ln):
            """The passage on that line, or the last passage before it (a heading line points at its section)."""
            arr = lines_of.get(stem)
            if not arr:
                return None
            import bisect
            k = bisect.bisect_right(arr, (ln, 1 << 60)) - 1
            return pid_ref.get(arr[max(k, 0)][1])
        n_links = 0
        batch = []
        for lf in glob.glob(os.path.join(a.links, "*_links.json")):
            stem1 = os.path.basename(lf)[:-len("_links.json")]
            if stem1 not in lines_of:
                continue
            try:
                items = json.load(open(lf, encoding="utf-8"))
            except Exception:
                continue
            for it in items if isinstance(items, list) else []:
                stem2 = os.path.splitext(os.path.basename(str(it.get("path_2") or "")))[0]
                r1 = ref_at(stem1, int(float(it.get("line_index_1") or 0)))
                r2 = ref_at(stem2, int(float(it.get("line_index_2") or 0)))
                if not r1 or not r2:
                    continue
                typ = (it.get("Conection Type") or it.get("connection_type") or "commentary").strip() or "commentary"
                batch.append((r1, r2, typ, cat_of.get(stem1, ""), cat_of.get(stem2, "")))
                n_links += 1
                if len(batch) >= 50000:
                    lib.db.executemany("INSERT INTO links(ref1,ref2,type,cat1,cat2) VALUES(?,?,?,?,?)", batch)
                    batch = []
        if batch:
            lib.db.executemany("INSERT INTO links(ref1,ref2,type,cat1,cat2) VALUES(?,?,?,?,?)", batch)
        lib.db.commit()
        print("links:", n_links, flush=True)
    lib.db.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('library_format', 'otzaria')") if \
        lib.db.execute("SELECT name FROM sqlite_master WHERE name='meta'").fetchone() else None
    lib.db.commit()
    print("Done.", lib.stats(), "with English:", n_en)


if __name__ == "__main__":
    main()
