"""Offline Hebrew <-> English dictionary and word-by-word Tanach (langdata/lang.sqlite, built by tools/build_langdata.py)."""
import os
import re
import sqlite3
import threading

MARKS = re.compile(r"[֑-ׇ]")
FIN = str.maketrans("ךםןףץ", "כמנפצ")
PREFIXES = "והבכלמש"


def key(w):
    return MARKS.sub("", w or "").replace("־", "").replace('"', "").replace("״", "").replace("'", "").replace("׳", "").strip().translate(FIN)


def is_hebrew(s):
    return bool(re.search(r"[א-ת]", s or ""))


class LangData:
    def __init__(self, paths):
        self.path = next((p for p in paths if p and os.path.exists(p)), None)
        self._local = threading.local()

    @property
    def ok(self):
        return bool(self.path)

    def db(self):
        c = getattr(self._local, "c", None)
        if c is None:
            c = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, check_same_thread=False)
            c.row_factory = sqlite3.Row
            self._local.c = c
        return c

    def q(self, sql, args=()):
        return [dict(r) for r in self.db().execute(sql, args).fetchall()]

    # ------------------------------------------------------------------ Hebrew -> English
    def lookup_he(self, word, limit=12):
        if not self.ok:
            return []
        k = key(word)
        if not k:
            return []
        out, seen = [], set()

        def add(rows, via):
            for r in rows:
                sig = (r["word"], r["gloss"])
                if sig in seen:
                    continue
                seen.add(sig)
                out.append({**r, "via": via})

        cands = [(k, "")]
        for n in range(1, 4):  # ו/ה/ב/כ/ל/מ/ש in front: ובבית -> בית
            if len(k) - n >= 2 and all(c in PREFIXES for c in k[:n]):
                pre = k[:n]
                cands.append((k[n:], "without " + "־".join(pre) + "־"))
        for kk, via in cands:
            add(self.q("SELECT word, lang, pos, gloss, source, strong FROM dict WHERE k=? ORDER BY source DESC LIMIT 8", (kk,)), via)
            for f in self.q("SELECT lemma_k, strong, SUM(n) n FROM forms WHERE k=? GROUP BY lemma_k, strong ORDER BY n DESC LIMIT 4", (kk,)):
                if f["strong"]:
                    rows = self.q("SELECT word, lang, pos, gloss, source, strong FROM dict WHERE strong=?", (f["strong"],))
                else:
                    rows = self.q("SELECT word, lang, pos, gloss, source, strong FROM dict WHERE k=? LIMIT 4", (f["lemma_k"],))
                add(rows, (via + ", " if via else "") + "a form of " + (rows[0]["word"] if rows else f["lemma_k"]))
            if len(out) >= limit:
                break
        return out[:limit]

    def gloss(self, word):
        """One short English meaning for a Hebrew word (for word-by-word translation)."""
        e = self.lookup_he(word, 3)
        if not e:
            return ""
        g = re.split(r"[;,(]", e[0]["gloss"] or "")[0].strip()
        via = e[0].get("via") or ""
        pre = ""
        m = re.match(r"without (\S+)־", via)
        if m:
            pre = " ".join({"ו": "and", "ה": "the", "ב": "in", "כ": "like", "ל": "to", "מ": "from", "ש": "that"}[c] for c in m.group(1).split("־") if c)
        return (pre + " " + g).strip()[:40]

    # ------------------------------------------------------------------ English -> Hebrew
    def lookup_en(self, text, limit=30):
        if not self.ok:
            return []
        words = re.findall(r"[A-Za-z']+", text)
        if not words:
            return []
        q = " ".join(f'"{w}"' for w in words)
        rows = self.q("SELECT d.word, d.lang, d.pos, d.gloss, d.source, d.strong, bm25(dict_fts) AS score FROM dict_fts "
                      "JOIN dict d ON d.id = dict_fts.rowid WHERE dict_fts MATCH ? ORDER BY score LIMIT 300", (q,))
        t = text.strip().lower()

        def rank(r):
            items = [x.strip().lower() for x in re.split(r"[;,]", r["gloss"] or "")]
            exact = t in items or ("to " + t) in items
            first = items[0] == t or items[0] == "to " + t if items else False
            return (not first, not exact, r["source"] != "Wiktionary", len(r["gloss"] or ""), r["score"])
        rows.sort(key=rank)
        seen, out = set(), []
        for r in rows:
            if r["word"] in seen:
                continue
            seen.add(r["word"])
            out.append(r)
            if len(out) >= limit:
                break
        return out

    # ------------------------------------------------------------------ word by word
    def interlinear(self, ref):
        if not self.ok:
            return []
        return self.q("SELECT w, strong, g FROM inter WHERE ref=? ORDER BY idx", (ref,))
