"""Build langdata/lang.sqlite: the offline Hebrew <-> English dictionary and the word-by-word (interlinear) Tanach.

Sources (all free):
  * Open Scriptures Hebrew Bible (morphhb, CC BY 4.0) - every word of Tanach with its root (Strong's number)
  * Strong's Hebrew dictionary (public domain, via Open Scriptures HebrewLexicon)
  * Wiktionary Hebrew + Aramaic (CC BY-SA, via kaikki.org) - modern and Rabbinic words, English meanings

    python tools/build_langdata.py --out langdata/lang.sqlite [--cache folder]
"""
import argparse, glob, io, json, os, re, sqlite3, sys, urllib.request, zipfile
import xml.etree.ElementTree as ET

MORPHHB = "https://github.com/openscriptures/morphhb/archive/refs/heads/master.zip"
STRONG = "https://raw.githubusercontent.com/openscriptures/HebrewLexicon/master/HebrewStrong.xml"
KAIKKI = ["https://kaikki.org/dictionary/Hebrew/kaikki.org-dictionary-Hebrew.jsonl",
          "https://kaikki.org/dictionary/Aramaic/kaikki.org-dictionary-Aramaic.jsonl"]
BOOKS = {"Gen": "Genesis", "Exod": "Exodus", "Lev": "Leviticus", "Num": "Numbers", "Deut": "Deuteronomy", "Josh": "Joshua",
         "Judg": "Judges", "Ruth": "Ruth", "1Sam": "I Samuel", "2Sam": "II Samuel", "1Kgs": "I Kings", "2Kgs": "II Kings",
         "1Chr": "I Chronicles", "2Chr": "II Chronicles", "Ezra": "Ezra", "Neh": "Nehemiah", "Esth": "Esther", "Job": "Job",
         "Ps": "Psalms", "Prov": "Proverbs", "Eccl": "Ecclesiastes", "Song": "Song of Songs", "Isa": "Isaiah", "Jer": "Jeremiah",
         "Lam": "Lamentations", "Ezek": "Ezekiel", "Dan": "Daniel", "Hos": "Hosea", "Joel": "Joel", "Amos": "Amos",
         "Obad": "Obadiah", "Jonah": "Jonah", "Mic": "Micah", "Nah": "Nahum", "Hab": "Habakkuk", "Zeph": "Zephaniah",
         "Hag": "Haggai", "Zech": "Zechariah", "Mal": "Malachi"}
PREFIX = {"b": "in", "c": "and", "d": "the", "k": "like", "l": "to", "m": "from", "s": "that", "i": "?"}
MARKS = re.compile(r"[֑-ׇ/]")
FIN = str.maketrans("ךםןףץ", "כמנפצ")


def plain(w):
    return MARKS.sub("", w or "").replace("־", "").strip()


def key(w):
    return plain(w).translate(FIN)


def fetch(url, cache):
    name = os.path.join(cache, re.sub(r"[^\w.]", "_", url.split("/", 3)[-1]))
    if os.path.exists(name):
        return open(name, "rb").read()
    print("download", url, flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "SeforimStudio-build/1.0"})
    data = urllib.request.urlopen(req, timeout=600).read()
    open(name, "wb").write(data)
    return data


def short_gloss(s):
    s = re.sub(r"\s+", " ", s or "").strip(" ;,.")
    s = re.split(r"[;,]", s)[0].strip()
    return s[:40]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_build", "langcache"))
    a = ap.parse_args()
    os.makedirs(a.cache, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    if os.path.exists(a.out):
        os.remove(a.out)
    db = sqlite3.connect(a.out)
    db.executescript("""
    CREATE TABLE dict(id INTEGER PRIMARY KEY, word TEXT, k TEXT, lang TEXT, pos TEXT, gloss TEXT, source TEXT, strong TEXT);
    CREATE TABLE forms(k TEXT, lemma_k TEXT, strong TEXT, n INT);
    CREATE TABLE inter(ref TEXT, idx INT, w TEXT, strong TEXT, g TEXT);
    CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
    """)
    # ---- Strong's
    strong = {}
    try:
        root = ET.fromstring(fetch(STRONG, a.cache))
        ns = {"o": root.tag.split("}")[0].strip("{")} if root.tag.startswith("{") else {}
        q = (lambda t: "o:" + t) if ns else (lambda t: t)
        for e in root.iter(("{%s}entry" % ns["o"]) if ns else "entry"):
            sid = e.get("id")
            w = e.find(q("w"), ns)
            if w is None or not sid:
                continue
            defs = [d.text.strip() for d in e.iter(("{%s}def" % ns["o"]) if ns else "def") if d.text and d.text.strip()]
            usage = e.find(q("usage"), ns)
            gloss = "; ".join(dict.fromkeys(defs)) or (usage.text if usage is not None and usage.text else "")
            gloss = re.sub(r"\s+", " ", gloss).strip()
            lang = "arc" if (w.get("{http://www.w3.org/XML/1998/namespace}lang") or "").startswith("arc") else "he"
            strong[sid] = (w.text or "", gloss)
            db.execute("INSERT INTO dict(word,k,lang,pos,gloss,source,strong) VALUES(?,?,?,?,?,?,?)",
                       (w.text, key(w.text), lang, w.get("pos") or "", gloss, "Strong's (Biblical)", sid))
        print("Strong's entries:", len(strong), flush=True)
    except Exception as e:  # noqa
        print("Strong's failed:", e)
    # ---- every word of Tanach
    forms = {}
    try:
        z = zipfile.ZipFile(io.BytesIO(fetch(MORPHHB, a.cache)))
        n = 0
        for name in z.namelist():
            if "/wlc/" not in name or not name.endswith(".xml"):
                continue
            root = ET.fromstring(z.read(name))
            for v in root.iter():
                if not v.tag.endswith("verse") or not v.get("osisID"):
                    continue
                b, c, vs = v.get("osisID").split(".")
                if b not in BOOKS:
                    continue
                ref = f"{BOOKS[b]} {c}:{vs}"
                idx = 0
                for w in v:
                    if not w.tag.endswith("}w") and w.tag != "w":
                        continue
                    lemma = w.get("lemma") or ""
                    parts = lemma.split("/")
                    pre = [PREFIX.get(p, "") for p in parts[:-1]]
                    num = re.sub(r"\D", "", parts[-1]) if parts else ""
                    sid = "H" + num if num else ""
                    main_g = short_gloss(strong.get(sid, ("", ""))[1])
                    g = " ".join(x for x in pre + [main_g] if x)
                    word = (w.text or "").replace("/", "")
                    db.execute("INSERT INTO inter VALUES(?,?,?,?,?)", (ref, idx, word, sid, g))
                    idx += 1
                    k = key(word)
                    lem = key(strong.get(sid, ("", ""))[0])
                    if k and lem:
                        forms[(k, lem, sid)] = forms.get((k, lem, sid), 0) + 1
                        # also the word without its prefixes, e.g. ובבית -> בית
                        segs = (w.text or "").split("/")
                        if len(parts) > 1 and len(segs) >= len(parts):
                            bare = key("".join(segs[len(parts) - 1:]))
                            if bare:
                                forms[(bare, lem, sid)] = forms.get((bare, lem, sid), 0) + 1
                    n += 1
        print("Tanach words:", n, flush=True)
    except Exception as e:  # noqa
        print("morphhb failed:", e)
    # ---- Wiktionary (modern + Rabbinic Hebrew, Aramaic)
    for url in KAIKKI:
        try:
            raw = fetch(url, a.cache)
        except Exception as e:  # noqa
            print("Wiktionary failed:", url, e)
            continue
        lang = "arc" if "Aramaic" in url else "he"
        k_n = 0
        for line in raw.decode("utf-8", "replace").splitlines():
            try:
                j = json.loads(line)
            except Exception:
                continue
            word = j.get("word") or ""
            if not re.search(r"[א-ת]", word):
                continue
            glosses = []
            for s in j.get("senses") or []:
                for g in s.get("glosses") or []:
                    if g and g not in glosses:
                        glosses.append(g)
            if not glosses:
                continue
            canon = next((f["form"] for f in j.get("forms") or [] if "canonical" in (f.get("tags") or [])), word)
            db.execute("INSERT INTO dict(word,k,lang,pos,gloss,source,strong) VALUES(?,?,?,?,?,?,?)",
                       (canon, key(word), lang, j.get("pos") or "", "; ".join(glosses[:6]), "Wiktionary", ""))
            for f in j.get("forms") or []:
                fk = key(f.get("form") or "")
                if fk and re.fullmatch(r"[א-ת ]+", fk) and fk != key(word):
                    forms[(fk, key(word), "")] = forms.get((fk, key(word), ""), 0) + 1
            k_n += 1
        print("Wiktionary", lang, k_n, flush=True)
    db.executemany("INSERT INTO forms VALUES(?,?,?,?)", [(k, l, s, n) for (k, l, s), n in forms.items()])
    db.executescript("""
    CREATE INDEX ix_dict_k ON dict(k); CREATE INDEX ix_forms_k ON forms(k); CREATE INDEX ix_inter ON inter(ref, idx);
    CREATE VIRTUAL TABLE dict_fts USING fts5(gloss, content='dict', content_rowid='id', tokenize='porter unicode61');
    INSERT INTO dict_fts(rowid, gloss) SELECT id, gloss FROM dict;
    """)
    db.execute("INSERT INTO meta VALUES('built', datetime('now'))")
    db.commit()
    for t in ("dict", "forms", "inter"):
        print(t, db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
    db.execute("VACUUM")
    db.close()
    print("size MB", round(os.path.getsize(a.out) / 1e6, 1))


if __name__ == "__main__":
    main()
