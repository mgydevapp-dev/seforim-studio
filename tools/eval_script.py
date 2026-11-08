"""Compare Hebrew readers on cursive: the normal print model (heb) vs the cursive model (heb_script).
    python tools/eval_script.py <tessdata-dir> <heldout-gt-dir> <report.md> [real images with .txt next to them...]
"""
import glob, os, re, subprocess, sys

def letters(t):
    return re.sub(r"[^א-ת ]", "", re.sub(r"\s+", " ", t or "")).strip()

def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]

def read(td, lang, img, psm):
    r = subprocess.run(["tesseract", img, "stdout", "--tessdata-dir", td, "-l", lang, "--psm", psm], capture_output=True, text=True)
    return r.stdout

td, gt, out = sys.argv[1:4]
reals = sys.argv[4:]
langs = [l for l in ("heb", "heb_script") if os.path.exists(os.path.join(td, l + ".traineddata"))]
rep = ["# Cursive (כתב) reader test", ""]
files = sorted(glob.glob(os.path.join(gt, "*.png")))[:300]
for lang in langs:
    e = n = 0
    for f in files:
        truth = letters(open(f[:-4] + ".gt.txt", encoding="utf-8").read())
        e += lev(letters(read(td, lang, f, "7")), truth); n += len(truth)
    rep.append(f"- **{lang}** on {len(files)} new handwriting-style lines: **{100 * (1 - e / max(1, n)):.1f}% of letters right**")
for img in reals:
    truth_f = os.path.splitext(img)[0] + ".txt"
    truth = letters(open(truth_f, encoding="utf-8").read()) if os.path.exists(truth_f) else ""
    rep += ["", f"## {os.path.basename(img)}", f"Correct: `{truth}`"]
    for lang in langs:
        for psm in ("6", "11"):
            got = read(td, lang, img, psm)
            g = letters(got)
            acc = 100 * (1 - lev(g, truth) / max(1, len(truth))) if truth else -1
            rep.append(f"- {lang} psm {psm}: {acc:.0f}% → `{g}`")
open(out, "w", encoding="utf-8").write("\n".join(rep) + "\n")
print("\n".join(rep))
