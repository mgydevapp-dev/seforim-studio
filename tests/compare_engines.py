"""STEP 5 — Compare the three engines on your own handwriting.

Usage:
    python tests/compare_engines.py my_page.jpg
    python tests/compare_engines.py my_page.jpg --truth my_page.txt     (optional: the correct text, to score accuracy)

It cleans the image (Step 1), runs every installed engine (A Ollama AI, B Kraken, C Tesseract),
prints each result, and — if you give the correct text — the character error rate (CER) and word accuracy.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scanner import cleanup, engines  # noqa: E402


def levenshtein(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def norm(s):
    import re
    s = re.sub(r"[֑-ׇ]", "", s)          # ignore nikud
    s = s.replace("״", '"').replace("׳", "'")
    return re.sub(r"\s+", " ", s).strip()


def score(pred, truth):
    p, t = norm(pred), norm(truth)
    cer = levenshtein(p, t) / max(1, len(t))
    pw, tw = p.split(), t.split()
    wer = levenshtein(pw, tw) / max(1, len(tw))
    return cer, 1 - wer


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--truth", help="text file with the correct transcription")
    ap.add_argument("--out", default="compare_out")
    ap.add_argument("--ollama-model", default=None)
    ap.add_argument("--kraken-model", default=None)
    a = ap.parse_args()
    truth = open(a.truth, encoding="utf-8").read() if a.truth else None

    print("Step 1: cleaning image…")
    page = cleanup.process_files([a.image], a.out)[0]
    print("  ", page["info"], "→", a.out)
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "models")
    rows = []
    for e in engines.engines(models_dir, a.ollama_model, a.kraken_model):
        ok, info = e.available()
        print("\n" + "=" * 70 + f"\n{e.name}\n" + "=" * 70)
        if not ok:
            print("  not installed:", info)
            continue
        t0 = time.time()
        try:
            text = e.read_image(engines.imread(engines.best_input(page["files"], e.key)))
        except Exception as ex:  # noqa
            print("  error:", ex)
            continue
        secs = time.time() - t0
        print(text)
        print(f"\n  ⏱ {secs:.1f} s")
        if truth:
            cer, wacc = score(text, truth)
            print(f"  characters wrong (CER): {cer:.1%}   words correct: {wacc:.1%}")
            rows.append((e.name, secs, cer, wacc))
        with open(os.path.join(a.out, f"result_{e.key}.txt"), "w", encoding="utf-8") as f:
            f.write(text)
    if rows:
        print("\nSummary (lower CER is better):")
        for n, s, c, w in sorted(rows, key=lambda r: r[2]):
            print(f"  {n:<36} CER {c:6.1%}   words {w:6.1%}   {s:6.1f}s")


if __name__ == "__main__":
    main()
