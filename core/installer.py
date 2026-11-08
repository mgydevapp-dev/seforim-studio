"""Install the pre-built full library that is downloaded separately (too big to be inside the app zip).

Files look like:  SeforimLibrary.sqlite.xz                     (one file)
             or:  SeforimLibrary.sqlite.xz.part1of3, …part2of3, …part3of3   (several parts)
They are found next to SeforimStudio.exe, in its data folder, or in the user's Downloads folder,
decompressed once into data/library.sqlite, and remembered so they are not installed twice."""
import glob
import json
import lzma
import os
import re
import sqlite3

PACKS = {"library": "SeforimLibrary.sqlite.xz", "ai": "SeforimAI.tar"}


PART_SIZE = 1900 * 1024 * 1024  # every part except the last one is exactly this big (split -b 1900M)
UNFINISHED = (".crdownload", ".partial", ".download", ".tmp", ".opdownload")


def _part_re(base):
    # also accept the names browsers give a second download: "SeforimLibrary.sqlite.xz (1).part1of2"
    return re.compile(re.escape(base) + r"(?: ?\(\d+\))?(?:\.part(\d+)of(\d+))?$", re.I)


PART_RE = _part_re(PACKS["library"])


def search_dirs(app_dir, data_dir, extra=None):
    """Folders where downloaded library / AI files are looked for: the app folder, Downloads, Desktop, Documents,
    OneDrive, the folder the Setup ran from, and every USB stick / other drive (its top folder and one level below)."""
    home = os.path.expanduser("~")
    dirs = [extra, app_dir, data_dir]
    for base in (home, os.path.join(home, "OneDrive")):
        dirs += [os.path.join(base, n) for n in ("Downloads", "Desktop", "Documents")]
    dirs.append(home)
    if os.name == "nt":
        import string
        for L in string.ascii_uppercase[2:]:
            root = f"{L}:\\"
            if os.path.isdir(root):
                dirs.append(root)
                try:
                    for p in glob.glob(os.path.join(root, "*", "Seforim*")):
                        dirs.append(os.path.dirname(p))
                except OSError:
                    pass
    out = []
    for d in dirs:
        try:
            if d and os.path.isdir(d) and os.path.abspath(d) not in out:
                out.append(os.path.abspath(d))
        except OSError:
            pass
    return out


def scan(dirs, base=PACKS["library"]):
    """Look for a complete, fully downloaded set of parts.
    Returns {"parts": [...], "expected": n, "problem": "plain-English explanation or ''"}."""
    rx = _part_re(base)
    problems = []
    for d in dirs:
        try:
            names = os.listdir(d)
        except OSError:
            continue
        sets, single = {}, None
        for n in names:
            if not n.lower().startswith(base.lower()):
                continue
            p = os.path.join(d, n)
            if n.lower().endswith(UNFINISHED):
                problems.append(f"{n} in {d} is still downloading (or the download stopped). Let the download finish, then press Install again.")
                continue
            m = rx.search(n)
            if not m or not os.path.isfile(p):
                continue
            if m.group(1) is None:
                single = p
            else:
                sets.setdefault(int(m.group(2)), {}).setdefault(int(m.group(1)), p)
        if single:
            return {"parts": [single], "expected": 1, "problem": ""}
        for total, files in sorted(sets.items(), key=lambda kv: -len(kv[1])):
            missing = [i for i in range(1, total + 1) if i not in files]
            if missing:
                problems.append(f"In {d}: found {len(files)} of the {total} parts - part {', '.join(map(str, missing))} is missing. "
                                f"Download every {base}.part…of{total} file into the same folder.")
                continue
            short = [i for i in range(1, total) if os.path.getsize(files[i]) != PART_SIZE]
            if short:
                problems.append(f"In {d}: part {', '.join(map(str, short))} is not completely downloaded "
                                f"({os.path.getsize(files[short[0]]) / 1e9:.2f} GB of {PART_SIZE / 1e9:.2f} GB). Delete it and download it again.")
                continue
            return {"parts": [files[i] for i in range(1, total + 1)], "expected": total, "problem": ""}
    return {"parts": [], "expected": 0, "problem": " ".join(dict.fromkeys(problems))}


def find_parts(dirs, base=PACKS["library"]):
    """Return (list of part paths in order, total parts expected) for the first complete set found."""
    r = scan(dirs, base)
    return r["parts"], r["expected"]


def free_space(parts, data_dir, ratio=5.0):
    """(bytes needed, bytes free) for unpacking next to data/: the library grows about 4.6x when unpacked."""
    import shutil
    need = int(sum(os.path.getsize(p) for p in parts) * ratio) + (500 << 20)
    try:
        free = shutil.disk_usage(data_dir).free
    except OSError:
        free = need
    return need, free


def signature(parts):
    return [[os.path.basename(p), os.path.getsize(p)] for p in parts]


def already_installed(data_dir, parts, pack="library"):
    f = os.path.join(data_dir, f"installed_{pack}.json")
    try:
        with open(f, encoding="utf-8") as fh:
            return json.load(fh) == signature(parts)
    except Exception:
        return False


def mark_installed(data_dir, parts, pack="library"):
    with open(os.path.join(data_dir, f"installed_{pack}.json"), "w", encoding="utf-8") as fh:
        json.dump(signature(parts), fh)


def decompress(parts, dest, progress=None):
    total = sum(os.path.getsize(p) for p in parts) or 1
    done = 0
    dec = lzma.LZMADecompressor()
    with open(dest, "wb") as out:
        for p in parts:
            with open(p, "rb") as f:
                while True:
                    chunk = f.read(4 << 20)
                    if not chunk:
                        break
                    done += len(chunk)
                    out.write(dec.decompress(chunk))
                    if progress:
                        progress(done / total)
    if not dec.eof:
        raise ValueError("The library download is incomplete or damaged — please download it again.")
    # quick sanity check
    c = sqlite3.connect(dest)
    try:
        n = c.execute("SELECT COUNT(*) FROM works").fetchone()[0]
    finally:
        c.close()
    return n


def copy_user_works(old_path, new_lib):
    """Keep seforim the user added themselves (My Library) when the big library replaces the old file."""
    if not os.path.exists(old_path):
        return 0
    from .library import skeleton
    from . import hebrew as H
    from collections import Counter
    old = sqlite3.connect(old_path)
    old.row_factory = sqlite3.Row
    n = 0
    try:
        works = old.execute("SELECT * FROM works WHERE source='user'").fetchall()
    except sqlite3.OperationalError:
        works = []
    db = new_lib.db
    for w in works:
        cols = [k for k in w.keys()]
        db.execute(f"INSERT OR REPLACE INTO works({','.join(cols)}) VALUES({','.join('?' * len(cols))})", tuple(w))
        wc = Counter()
        for p in old.execute("SELECT * FROM passages WHERE work_id=? ORDER BY seq", (w["id"],)):
            cur = db.execute("INSERT INTO passages(work_id,seq,node,chapter,verse,ref,he,en,he_plain,initials,finals) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                             (p["work_id"], p["seq"], p["node"], p["chapter"], p["verse"], p["ref"], p["he"], p["en"],
                              p["he_plain"], p["initials"], p["finals"]))
            pid = cur.lastrowid
            if p["he_plain"]:
                db.execute("INSERT INTO fts_he(rowid,he_plain,he_skel) VALUES(?,?,?)",
                           (pid, p["he_plain"], " ".join(skeleton(x) for x in p["he_plain"].split())))
                wc.update(p["he_plain"].split())
            if p["en"]:
                db.execute("INSERT INTO fts_en(rowid,en) VALUES(?,?)", (pid, p["en"]))
        new_lib._add_words(wc)
        n += 1
    db.commit()
    old.close()
    return n


class _Concat:
    """Read several files one after another as if they were one (for split downloads)."""

    def __init__(self, parts, progress=None):
        self.parts, self.i, self.f = list(parts), 0, None
        self.total = sum(os.path.getsize(p) for p in parts) or 1
        self.done, self.progress = 0, progress

    def read(self, n=-1):
        out = b""
        while n < 0 or len(out) < n:
            if self.f is None:
                if self.i >= len(self.parts):
                    break
                self.f = open(self.parts[self.i], "rb")
                self.i += 1
            chunk = self.f.read(-1 if n < 0 else n - len(out))
            if not chunk:
                self.f.close()
                self.f = None
                continue
            out += chunk
        self.done += len(out)
        if self.progress:
            self.progress(self.done / self.total)
        return out


def extract_tar(parts, dest, progress=None):
    """Unpack a (split) .tar download into dest, safely (no paths outside dest)."""
    import tarfile
    os.makedirs(dest, exist_ok=True)
    root = os.path.abspath(dest)
    n = 0
    with tarfile.open(fileobj=_Concat(parts, progress), mode="r|") as t:
        for m in t:
            target = os.path.abspath(os.path.join(dest, m.name))
            if not (target == root or target.startswith(root + os.sep)) or m.issym() or m.islnk():
                continue
            if m.isdir():
                os.makedirs(target, exist_ok=True)
                continue
            if not m.isfile():
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            src = t.extractfile(m)
            with open(target, "wb") as out:
                while True:
                    b = src.read(4 << 20)
                    if not b:
                        break
                    out.write(b)
            try:
                os.chmod(target, (m.mode & 0o777) | 0o600)
            except OSError:
                pass
            n += 1
    return n
