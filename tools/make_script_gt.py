"""Make training lines for a Hebrew CURSIVE (כתב יד) reader: every line is drawn in a cursive script font,
letter by letter with handwriting-like wobble (size, slant, spacing, marker thickness, blur, noise),
and saved as  NNNNN.png + NNNNN.gt.txt  (the tesstrain ground-truth format).

    python tools/make_script_gt.py --fonts f1.ttf f2.ttf --corpus heb.txt --out gt --lines 30000
"""
import argparse, math, os, random, re
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

LETTERS = "אבגדהוזחטיכךלמםנןסעפףצץקרשת"
NONFINAL = "אבגדהוזחטיכלמנסעפצקרשת"
FINAL = {"כ": "ך", "מ": "ם", "נ": "ן", "פ": "ף", "צ": "ץ"}


def clean(line):
    line = re.sub(r"[֑-ׇ]", "", line)          # no nikud / trop in handwriting
    line = re.sub(r"[^א-ת .,\"'\-:]", " ", line)
    return re.sub(r"\s+", " ", line).strip()


def corpus_lines(path, n):
    words = []
    if path and os.path.exists(path):
        for l in open(path, encoding="utf-8"):
            words += clean(l).split()
    words = [w for w in words if re.search(r"[א-ת]", w)] or ["שלום"]
    out = []
    for i in range(n):
        r = random.random()
        if r < 0.12:      # the alphabet, single letters with spaces (like a chart of the letters)
            k = random.randint(3, 8)
            out.append(" ".join(random.choice(LETTERS) for _ in range(k)))
        elif r < 0.22:    # random letter "words" - teaches the shapes, not the language
            ws = []
            for _ in range(random.randint(2, 6)):
                w = "".join(random.choice(NONFINAL) for _ in range(random.randint(1, 5)))
                if w[-1] in FINAL and random.random() < .7:
                    w = w[:-1] + FINAL[w[-1]]
                ws.append(w)
            out.append(" ".join(ws))
        else:             # real Hebrew text
            k = random.randint(2, 8)
            j = random.randint(0, max(0, len(words) - k))
            out.append(" ".join(words[j:j + k]))
    return out


def render(text, font_path):
    size = random.randint(34, 64)
    font = ImageFont.truetype(font_path, size)
    vis = text[::-1]  # Hebrew is drawn right-to-left: reverse for left-to-right drawing (no shaping needed)
    W = int(size * (len(vis) * 0.85 + 4)); H = int(size * 2.2)
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    x = size // 2; base = H // 2
    wob = random.uniform(0, 3.5); freq = random.uniform(0.01, 0.05); phase = random.uniform(0, 6)
    for ch in vis:
        s = max(12, int(size * random.uniform(0.9, 1.1)))
        f = font if s == size else ImageFont.truetype(font_path, s)
        y = base - s * 0.75 + wob * math.sin(x * freq + phase) + random.uniform(-1.5, 1.5)
        d.text((x, y), ch, font=f, fill=0)
        try:
            adv = f.getlength(ch)
        except Exception:
            adv = s * 0.6
        x += adv * random.uniform(0.92, 1.12) + (s * random.uniform(0.05, 0.3) if ch == " " else random.uniform(-1, 2.5))
    img = img.crop((0, 0, min(W, int(x + size // 2)), H))
    img = ImageOps.expand(img, border=size, fill=255)  # room for slant / rotation
    # marker / pen thickness
    t = random.choice([0, 0, 3, 3, 5])
    if t:
        img = img.filter(ImageFilter.MinFilter(t))
    # slant and rotation
    sh = random.uniform(-0.18, 0.12)
    img = img.transform(img.size, Image.AFFINE, (1, sh, -sh * img.size[1] / 2, 0, 1, 0), resample=Image.BILINEAR, fillcolor=255)
    img = img.rotate(random.uniform(-2.5, 2.5), resample=Image.BILINEAR, expand=True, fillcolor=255)
    if random.random() < .6:
        img = img.filter(ImageFilter.GaussianBlur(random.uniform(0.3, 1.4)))
    # paper: grey level, contrast, noise
    lo, hi = random.randint(0, 70), random.randint(185, 255)
    img = img.point(lambda v: lo + (hi - lo) * v // 255)
    if random.random() < .5:
        import numpy as np
        a = np.asarray(img).astype("int16") + np.random.normal(0, random.uniform(2, 12), (img.size[1], img.size[0])).astype("int16")
        img = Image.fromarray(a.clip(0, 255).astype("uint8"))
    # tight crop with a margin
    bbox = ImageOps.invert(img).point(lambda v: 255 if v > 60 else 0).getbbox()
    if bbox:
        m = 8
        img = img.crop((max(0, bbox[0] - m), max(0, bbox[1] - m), min(img.size[0], bbox[2] + m), min(img.size[1], bbox[3] + m)))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", nargs="+", required=True)
    ap.add_argument("--corpus")
    ap.add_argument("--out", required=True)
    ap.add_argument("--lines", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    random.seed(a.seed)
    os.makedirs(a.out, exist_ok=True)
    good = []
    for f in a.fonts:  # keep only fonts that really have Hebrew letters
        try:
            ft = ImageFont.truetype(f, 40)
            if ft.getbbox("א")[2] > 5 and ft.getmask("א").getbbox() != ft.getmask("￿").getbbox():
                good.append(f)
        except Exception as e:
            print("skip font", f, e)
    print("fonts:", good)
    for i, line in enumerate(corpus_lines(a.corpus, a.lines)):
        if not line:
            continue
        f = good[i % len(good)]
        try:
            render(line, f).save(os.path.join(a.out, f"{i:06d}.png"))
            open(os.path.join(a.out, f"{i:06d}.gt.txt"), "w", encoding="utf-8").write(line + "\n")
        except Exception as e:
            print("line", i, e)
        if i % 5000 == 0:
            print(i, flush=True)


if __name__ == "__main__":
    main()
