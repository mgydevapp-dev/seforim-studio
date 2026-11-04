"""Build the COMPLETE offline library in one go (used by the GitHub build so users get everything pre-downloaded).

    python tools/prebuild_library.py --out build/library.sqlite [--english] [--links] [--titles-only] [--limit N]

Downloads every sefer in the catalog (Hebrew + English), exact Hebrew titles/authors/dates, and (optionally) all
cross-references, straight into one SQLite library file, then optimises it.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.catalog import Catalog, Downloader  # noqa: E402
from core.library import Library  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--catalog", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "seforim_catalog.db"))
    ap.add_argument("--english", action="store_true", default=True)
    ap.add_argument("--no-english", dest="english", action="store_false")
    ap.add_argument("--links", action="store_true")
    ap.add_argument("--titles-only", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="only the first N works (for testing)")
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    cat = Catalog(a.catalog)
    lib = Library(a.out)
    dl = Downloader(cat, lib, os.path.dirname(os.path.abspath(a.out)))
    t0 = time.time()
    last = [0]

    def progress(st):
        if time.time() - last[0] > 20:
            last[0] = time.time()
            print(f"[{int(time.time() - t0)}s] {st['done']}/{st['total']} {st['current'][:60]} | "
                  f"{st['bytes'] / 1e9:.2f} GB | errors {len(st['errors'])}", flush=True)

    if a.titles_only:
        dl._titles(a.workers, progress)
    else:
        ids = [r["id"] for r in cat.q("SELECT id FROM works ORDER BY id")]
        if a.limit:
            ids = ids[:a.limit]
        dl.run_all(ids, include_english=a.english, include_links=a.links, include_titles=True, workers=a.workers, progress=progress)

    st = dl.state
    print(f"\nFinished in {int(time.time() - t0)} s. Downloaded {st['bytes'] / 1e9:.2f} GB. Errors: {len(st['errors'])}")
    for e in st["errors"][:40]:
        print("  !", e)
    print("Optimising…", flush=True)
    s = lib.compact()
    print("Library:", s)
    with open(os.path.join(os.path.dirname(os.path.abspath(a.out)), "library_report.txt"), "w", encoding="utf-8") as f:
        f.write(f"{s}\nerrors: {len(st['errors'])}\n" + "\n".join(st["errors"]))


if __name__ == "__main__":
    main()
