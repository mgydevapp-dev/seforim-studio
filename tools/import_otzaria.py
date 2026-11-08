"""Build the "more seforim" pack from the Otzaria library (github.com/Sivan22/otzaria-library, folder אוצריא):
thousands of seforim from Dicta, Torat Emet, Wikisource, Ben-Yehuda and others, as .txt files with <h1>/<h2> headings.
Seforim the main (Sefaria) library already has are skipped.

    python tools/import_otzaria.py <otzaria-folder> --out more.sqlite [--catalog data/seforim_catalog.db]
"""
import argparse, glob, html, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.library import Library  # noqa: E402

TAG = re.compile(r"<[^>]+>")
HEAD = re.compile(r"^\s*<h([1-6])[^>]*>(.*?)</h\1>\s*$", re.I)
START_ID = 3_000_000
TOP = "More seforim"


def norm_title(t):
    t = re.sub(r"[֑-ׇ\"'״׳.,\-–()\[\]]", "", t or "")
    return re.sub(r"\s+", " ", t).strip()


def known_titles(catalog):
    out = set()
    if not catalog or not os.path.exists(catalog):
        return out
    import sqlite3
    from core.order import he_name
    for (t,) in sqlite3.connect(catalog).execute("SELECT title FROM works"):
        h = he_name(t)
        if h and h != t:
            out.add(norm_title(h))
    return out


def parse(path):
    """-> (title, [(node, chapter, [paragraphs])])"""
    try:
        text = open(path, encoding="utf-8").read()
    except UnicodeDecodeError:
        text = open(path, encoding="cp1255", errors="replace").read()
    title = os.path.splitext(os.path.basename(path))[0]
    heads = {}
    chapters, cur = [], None
    for line in text.splitlines():
        m = HEAD.match(line)
        if m:
            lvl, name = int(m.group(1)), html.unescape(TAG.sub("", m.group(2))).strip()
            if lvl == 1:
                title = name or title
                continue
            heads[lvl] = name
            for k in [k for k in heads if k > lvl]:
                del heads[k]
            levels = sorted(heads)
            node = " / ".join(heads[k] for k in levels[:-1])[:120]
            cur = (node, heads[levels[-1]][:60], [])
            chapters.append(cur)
            continue
        s = html.unescape(TAG.sub("", line)).strip()
        if not s:
            continue
        if cur is None:
            cur = ("", "", [])
            chapters.append(cur)
        cur[2].append(s)
    return title, [c for c in chapters if c[2]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--out", required=True)
    ap.add_argument("--catalog", default="data/seforim_catalog.db")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    lib = Library(a.out)
    skip = known_titles(a.catalog)
    files = sorted(glob.glob(os.path.join(a.root, "**", "*.txt"), recursive=True))
    print(len(files), "books found;", len(skip), "Sefaria titles known", flush=True)
    wid, n_ok, n_skip, t0 = START_ID, 0, 0, time.time()
    report = []
    for i, f in enumerate(files[: a.limit or None]):
        rel = os.path.relpath(f, a.root).split(os.sep)
        try:
            title, chapters = parse(f)
        except Exception as e:  # noqa
            report.append(f"error {f}: {e}")
            continue
        if not chapters:
            continue
        if norm_title(title) in skip:
            n_skip += 1
            continue
        cat = " > ".join([TOP] + rel[:-1])
        # structure: one "chapter" per heading; numbered paragraphs inside
        he = [[p for p in c[2]] for c in chapters]
        try:
            lib.import_work({"id": wid, "title": title, "he_title": title, "category_path": cat, "top_category": TOP},
                            {"text": he, "heTitle": title, "schema": {"sectionNames": ["Chapter", "Paragraph"]}}, None, source="otzaria")
            with lib.lock:  # keep the real chapter names (פרק א, סימן ב, …)
                for k, (node, ch, _) in enumerate(chapters):
                    lib.db.execute("UPDATE passages SET node=?, chapter=? WHERE work_id=? AND chapter=?",
                                   (node, ch or str(k + 1), wid, str(k + 1)))
                lib.db.execute("UPDATE works SET he_title=? WHERE id=?", (title, wid))
                lib.db.commit()
            wid += 1
            n_ok += 1
        except Exception as e:  # noqa
            report.append(f"error {title}: {e}")
        if i % 200 == 0:
            print(f"{i}/{len(files)} books · {n_ok} added · {n_skip} already in Sefaria · {int(time.time() - t0)} s", flush=True)
    print("Done:", n_ok, "added,", n_skip, "skipped (already in the main library)")
    print(lib.stats())
    open(os.path.splitext(a.out)[0] + "_report.txt", "w", encoding="utf-8").write(
        f"{n_ok} seforim added, {n_skip} skipped as duplicates\n" + "\n".join(report))


if __name__ == "__main__":
    main()
