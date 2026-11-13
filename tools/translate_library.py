"""English for the library without Sefaria.

  * Tanach: the JPS 1917 translation (public domain), from ebible.org (engjps, verse per line).
  * Everything else that matters most (Mishnah, Shas, Rashi, Rambam, Shulchan Aruch, …): an offline machine translation
    (OPUS-MT by the University of Helsinki, run with CTranslate2). Marked in the app as a machine translation.

  translate:  python tools/translate_library.py translate --lib library.sqlite --model ct2dir --tok HF-name
                  --shard 0 --shards 6 --budget 18000 --out trans_0.sqlite
  apply:      python tools/translate_library.py apply --lib library.sqlite --jps engjps_vpl.txt trans_*.sqlite
"""
import argparse
import glob
import os
import re
import sqlite3
import sys
import time

TAG_RE = re.compile(r"<[^>]+>")
NIKUD_RE = re.compile(r"[֑-ׇ]")

# what to translate first (pattern on "category_path | he_title | title"), then everything else by size
TIERS = [
    r"^Mishnah",
    r"בבלי|Bavli",
    r"^Tanakh.*(רש\"?י על|Rashi on)",
    r"משנה תורה|Mishneh Torah",
    r"שולחן ערוך|Shulchan Arukh",
    r"ירושלמי|Yerushalmi",
    r"(רש\"?י על|Rashi on).*(ברכות|שבת|עירובין|פסחים|יומא|סוכה|ביצה|ראש השנה|תענית|מגילה|מועד קטן|חגיגה|יבמות|כתובות|נדרים|נזיר|סוטה|גיטין|קידושין|בבא|סנהדרין|מכות|שבועות|עבודה זרה|הוריות|זבחים|מנחות|חולין|בכורות|ערכין|תמורה|כריתות|מעילה|נדה)",
    r"(תוספות על|Tosafot on)",
    r"^Tanakh.*(רמב\"?ן|אבן עזרא|ספורנו|Ramban|Ibn Ezra|Sforno)",
    r"משנה ברורה|Mishnah Berurah",
    r"^Midrash",
    r"^Musar|^Chasidut|^Jewish Thought",
]


def clean(he):
    t = TAG_RE.sub(" ", he or "")
    t = NIKUD_RE.sub("", t).replace("־", " ")
    return re.sub(r"\s+", " ", t).strip()


def pieces(t, max_words=45):
    """Sentences small enough for the translator."""
    out = []
    for s in re.split(r"(?<=[.:?!;])\s+", t):
        w = s.split()
        while len(w) > max_words:
            cut = max_words
            for j in range(max_words, max_words // 2, -1):  # cut after a comma if there is one
                if w[j - 1].endswith(","):
                    cut = j
                    break
            out.append(" ".join(w[:cut]))
            w = w[cut:]
        if w:
            out.append(" ".join(w))
    return out


def plan(db, shard, shards):
    works = db.execute("SELECT id, title, he_title, category_path, n_passages FROM works WHERE top_category != 'Tanakh' "
                       "OR he_title LIKE '%על%' OR title LIKE '% on %'").fetchall()
    tiers = [[] for _ in range(len(TIERS) + 1)]
    for w in works:
        key = f"{w[3] or ''} | {w[2] or ''} | {w[1] or ''}"
        k = next((i for i, p in enumerate(TIERS) if re.search(p, key)), len(TIERS))
        tiers[k].append(w)
    order = []
    for t in tiers:
        t.sort(key=lambda w: -(w[4] or 0)) if t is tiers[-1] else t.sort(key=lambda w: w[0])
        order += t
    return [w for i, w in enumerate(order) if i % shards == shard]


def translate(a):
    import ctranslate2
    import transformers
    tok = transformers.AutoTokenizer.from_pretrained(a.tok)
    tr = ctranslate2.Translator(a.model, device="cpu", compute_type="int8", inter_threads=1, intra_threads=os.cpu_count() or 4)
    db = sqlite3.connect(a.lib)
    out = sqlite3.connect(a.out)
    out.execute("CREATE TABLE IF NOT EXISTS tr(pid INTEGER PRIMARY KEY, en TEXT)")
    out.execute("CREATE TABLE IF NOT EXISTS done(work_id INTEGER PRIMARY KEY, title TEXT, n INTEGER)")
    t0, total_words = time.time(), 0
    for wid, title, he_title, cat, n in plan(db, a.shard, a.shards):
        if time.time() - t0 > a.budget:
            break
        rows = db.execute("SELECT id, he FROM passages WHERE work_id=? ORDER BY seq", (wid,)).fetchall()
        segs, owner = [], []
        for pid, he in rows:
            for p in pieces(clean(he)):
                if re.search(r"[א-ת]", p):
                    segs.append(p)
                    owner.append(pid)
        if not segs:
            continue
        res = {}
        for i in range(0, len(segs), 512):
            chunk = segs[i:i + 512]
            src = [tok.convert_ids_to_tokens(tok.encode(s))[:250] for s in chunk]
            hyp = tr.translate_batch(src, max_batch_size=64, beam_size=a.beam, max_decoding_length=300,
                                     repetition_penalty=1.1, no_repeat_ngram_size=4)
            for pid, h in zip(owner[i:i + 512], hyp):
                res.setdefault(pid, []).append(tok.decode(tok.convert_tokens_to_ids(h.hypotheses[0]), skip_special_tokens=True))
            if time.time() - t0 > a.budget + 900:  # never run past the job's time limit
                break
        out.executemany("INSERT OR REPLACE INTO tr(pid, en) VALUES(?,?)", [(p, " ".join(v)) for p, v in res.items()])
        out.execute("INSERT OR REPLACE INTO done(work_id, title, n) VALUES(?,?,?)", (wid, title, len(res)))
        out.commit()
        total_words += sum(len(s.split()) for s in segs)
        print(f"[{int(time.time() - t0)} s] {title} ({he_title}) - {len(res)} passages · {total_words / (time.time() - t0):.0f} words/s", flush=True)
    print("shard done:", out.execute("SELECT COUNT(*) FROM done").fetchone()[0], "seforim,",
          out.execute("SELECT COUNT(*) FROM tr").fetchone()[0], "passages")


BOOKS = {"GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus", "NUM": "Numbers", "DEU": "Deuteronomy", "JOS": "Joshua",
         "JDG": "Judges", "1SA": "I Samuel", "2SA": "II Samuel", "1KI": "I Kings", "2KI": "II Kings", "ISA": "Isaiah",
         "JER": "Jeremiah", "EZK": "Ezekiel", "HOS": "Hosea", "JOL": "Joel", "AMO": "Amos", "OBA": "Obadiah", "JON": "Jonah",
         "MIC": "Micah", "NAM": "Nahum", "HAB": "Habakkuk", "ZEP": "Zephaniah", "HAG": "Haggai", "ZEC": "Zechariah",
         "MAL": "Malachi", "PSA": "Psalms", "PRO": "Proverbs", "JOB": "Job", "SNG": "Song of Songs", "RUT": "Ruth",
         "LAM": "Lamentations", "ECC": "Ecclesiastes", "EST": "Esther", "DAN": "Daniel", "EZR": "Ezra", "NEH": "Nehemiah",
         "1CH": "I Chronicles", "2CH": "II Chronicles"}
BOOKS_HE = {"GEN": "בראשית", "EXO": "שמות", "LEV": "ויקרא", "NUM": "במדבר", "DEU": "דברים", "JOS": "יהושע", "JDG": "שופטים",
            "1SA": "שמואל א", "2SA": "שמואל ב", "1KI": "מלכים א", "2KI": "מלכים ב", "ISA": "ישעיהו", "JER": "ירמיהו",
            "EZK": "יחזקאל", "HOS": "הושע", "JOL": "יואל", "AMO": "עמוס", "OBA": "עובדיה", "JON": "יונה", "MIC": "מיכה",
            "NAM": "נחום", "HAB": "חבקוק", "ZEP": "צפניה", "HAG": "חגי", "ZEC": "זכריה", "MAL": "מלאכי", "PSA": "תהילים",
            "PRO": "משלי", "JOB": "איוב", "SNG": "שיר השירים", "RUT": "רות", "LAM": "איכה", "ECC": "קהלת", "EST": "אסתר",
            "DAN": "דניאל", "EZR": "עזרא", "NEH": "נחמיה", "1CH": "דברי הימים א", "2CH": "דברי הימים ב"}


def apply(a):
    db = sqlite3.connect(a.lib)
    print("removing the old English…", flush=True)
    db.execute("UPDATE passages SET en='', en_basic=NULL WHERE en != '' OR en_basic IS NOT NULL")
    db.execute("UPDATE works SET description = trim(replace(replace(replace(coalesce(description,''), '[approx-en]', ''), '[machine-en]', ''), '[jps1917]', ''))")
    db.execute("DROP TABLE IF EXISTS fts_en")
    db.execute("CREATE VIRTUAL TABLE fts_en USING fts5(en, content='', contentless_delete=1, tokenize='porter unicode61')")
    db.commit()
    # ---- Tanach: JPS 1917
    n_jps = 0
    if a.jps and os.path.exists(a.jps):
        verses = {}
        for line in open(a.jps, encoding="utf-8-sig"):
            m = re.match(r"(\w{3}) (\d+):(\d+)\s+(.*)", line.strip())
            if m and m.group(1) in BOOKS:
                verses.setdefault(m.group(1), {})[(int(m.group(2)), int(m.group(3)))] = m.group(4).strip()
        for code, vv in verses.items():
            w = db.execute("SELECT id FROM works WHERE top_category='Tanakh' AND (title=? OR replace(replace(he_title,'\"',''),'''','')=?) "
                           "ORDER BY n_passages DESC LIMIT 1", (BOOKS[code], BOOKS_HE[code])).fetchone()
            if not w:
                print("no sefer for", code)
                continue
            got = 0
            for pid, ch, v in db.execute("SELECT id, chapter, verse FROM passages WHERE work_id=?", (w[0],)).fetchall():
                try:
                    en = vv.get((int(ch), int(v)))
                except (TypeError, ValueError):
                    en = None
                if en:
                    db.execute("UPDATE passages SET en=? WHERE id=?", (en, pid))
                    got += 1
            if got:
                db.execute("UPDATE works SET description=trim(coalesce(description,'') || ' [jps1917]') WHERE id=?", (w[0],))
                n_jps += 1
            print(f"JPS {BOOKS[code]}: {got} of {len(vv)} verses", flush=True)
    # ---- machine translation
    n_mt, works = 0, set()
    for f in a.trans:
        t = sqlite3.connect(f)
        for pid, en in t.execute("SELECT pid, en FROM tr"):
            db.execute("UPDATE passages SET en=? WHERE id=? AND en=''", (en, pid))
            n_mt += 1
        works |= {r[0] for r in t.execute("SELECT work_id FROM done")}
        t.close()
    for wid in works:
        db.execute("UPDATE works SET description=trim(coalesce(description,'') || ' [machine-en]') WHERE id=? "
                   "AND coalesce(description,'') NOT LIKE '%[jps1917]%'", (wid,))
    db.commit()
    print("search index for English…", flush=True)
    db.execute("INSERT INTO fts_en(rowid, en) SELECT id, en FROM passages WHERE en != ''")
    db.execute("INSERT INTO fts_en(fts_en) VALUES('optimize')")
    db.commit()
    print(f"Done: JPS on {n_jps} books of Tanach; machine English on {len(works)} seforim ({n_mt} passages).")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("translate")
    t.add_argument("--lib", required=True)
    t.add_argument("--model", required=True)
    t.add_argument("--tok", required=True)
    t.add_argument("--shard", type=int, default=0)
    t.add_argument("--shards", type=int, default=1)
    t.add_argument("--budget", type=int, default=3600)
    t.add_argument("--beam", type=int, default=2)
    t.add_argument("--out", required=True)
    p = sub.add_parser("apply")
    p.add_argument("--lib", required=True)
    p.add_argument("--jps")
    p.add_argument("trans", nargs="*")
    a = ap.parse_args()
    (translate if a.cmd == "translate" else apply)(a)


if __name__ == "__main__":
    sys.exit(main())
