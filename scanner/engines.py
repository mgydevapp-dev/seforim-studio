"""STEP 2 — Handwritten Hebrew text recognition, fully offline.

  A) Local AI vision model through Ollama (best for messy handwriting / cursive).
     Default model: qwen3-vl:8b (6.1 GB download; needs ~8 GB GPU VRAM, or 16 GB RAM on CPU — slow).
     Smaller: qwen3-vl:4b (3.3 GB; 8 GB RAM).  Stronger: qwen3-vl:30b (20 GB; 24 GB+ VRAM/RAM).
  B) Kraken OCR with a Hebrew handwriting model (.mlmodel) — good for consistent handwriting; trainable.
  C) Tesseract with the 'heb' language pack — fast fallback for neat block letters / print.

Default order: A if Ollama + a vision model are installed, else B, else C.
Command line:  python -m scanner.engines page.png [--engine ollama|kraken|tesseract]
"""
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

import cv2
import numpy as np

from .cleanup import split_strips

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
if not OLLAMA_URL.startswith("http"):
    OLLAMA_URL = "http://" + OLLAMA_URL
VISION_HINTS = ("vl", "vision", "llava", "gemma3", "minicpm-v", "moondream", "llama4", "mistral-small3", "granite3.2-vision")
PREFERRED = ["qwen3-vl:8b", "qwen3-vl:latest", "qwen3-vl:4b", "qwen3-vl:30b", "qwen3-vl:32b", "qwen3-vl:2b", "qwen2.5vl:7b", "gemma3:12b"]

PROMPT = """You are a careful transcriber of handwritten Hebrew.
Transcribe ALL the Hebrew handwriting in this image exactly as written, line by line, top to bottom.
Rules:
- Output only the transcription, in Hebrew letters. No translation, no explanation, no commentary.
- Keep one output line for each handwritten line. Keep the original line breaks.
- Do not correct spelling, do not complete words, do not add words that are not there.
- Keep abbreviations and their marks (״ ׳ ") exactly; keep numbers and punctuation where they are.
- If a word cannot be read, write [???] in its place.
- Ignore printed ruled lines, page numbers and stains."""

HEB = re.compile(r"[\u05D0-\u05EA]")


def _norm_line(s):
    return re.sub(r"[\u0591-\u05C7\s\"'״׳.,:;!?\-]", "", s)


def clean_transcription(text):
    """Strip model chatter / code fences / bidi marks; normalise quotes; keep line breaks."""
    t = text.replace("\r\n", "\n")
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.S)
    t = re.sub(r"^```[a-z]*\n?|```$", "", t.strip(), flags=re.M)
    t = re.sub(r"[\u200E\u200F\u202A-\u202E\u2066-\u2069]", "", t)
    lines = []
    for l in t.split("\n"):
        s = l.strip()
        if not s:
            lines.append("")
            continue
        if not HEB.search(s) and re.match(r"^(here|the |transcription|this image|sure|i )", s, re.I):
            continue  # model chatter in English
        s = re.sub(r'(?<=[\u05D0-\u05EA])"(?=[\u05D0-\u05EA])', "״", s)
        s = re.sub(r"(?<=[\u05D0-\u05EA])'", "׳", s)
        lines.append(s)
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def merge_strips(parts):
    """Join transcriptions of overlapping strips, dropping lines repeated at the seams."""
    out = []
    for p in parts:
        lines = [l for l in p.split("\n")]
        if out:
            # drop up to 3 leading lines that match the last lines already collected
            tail = [_norm_line(x) for x in out[-4:] if x.strip()]
            k = 0
            while k < min(3, len(lines)) and _norm_line(lines[k]) and any(
                    _similar(_norm_line(lines[k]), t) for t in tail):
                k += 1
            lines = lines[k:]
        out += lines
    return "\n".join(out).strip()


def _similar(a, b):
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    import difflib
    return difflib.SequenceMatcher(None, a, b).ratio() > 0.8


def _to_png_b64(img, max_side=1800):
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    h, w = img.shape[:2]
    if max(h, w) > max_side:
        f = max_side / max(h, w)
        img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".png", img)
    return base64.b64encode(buf.tobytes()).decode()


def imread(path):
    img = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Cannot read {path}")
    return img


# ====================================================================== A) Ollama
class OllamaEngine:
    key, name = "ollama", "A · Local AI vision (Ollama)"

    def __init__(self, model=None, url=OLLAMA_URL, timeout=600):
        self.url, self.timeout = url, timeout
        self.model = model

    def _get(self, path, timeout=3):
        with urllib.request.urlopen(self.url + path, timeout=timeout) as r:
            return json.loads(r.read())

    def models(self):
        try:
            tags = self._get("/api/tags")["models"]
        except Exception:
            return None  # Ollama not running / not installed
        names = [m["name"] for m in tags]
        vis = [n for n in names if any(h in n.lower() for h in VISION_HINTS)]
        return vis

    def pick_model(self):
        vis = self.models() or []
        if self.model and self.model in vis:
            return self.model
        for p in PREFERRED:
            if p in vis:
                return p
        return vis[0] if vis else None

    def available(self):
        try:
            vis = self.models()
        except Exception:
            vis = None
        if vis is None:
            return False, "Ollama is not running (install from ollama.com, then run: ollama pull qwen3-vl:8b)"
        if not vis:
            return False, "Ollama is running but no vision model is installed. Run: ollama pull qwen3-vl:8b"
        return True, f"model {self.pick_model()}"

    def read_image(self, img, strips=None, progress=None, cancel=None):
        model = self.pick_model()
        if not model:
            raise RuntimeError(self.available()[1])
        h, w = img.shape[:2]
        if strips is None:
            strips = max(1, int(round(h / max(w * 0.9, 1) * 1.0))) if h > w * 1.25 else 1
        parts = split_strips(img, strips, overlap=0.12) if strips > 1 else [img]
        texts = []
        for i, part in enumerate(parts):
            if cancel and cancel():
                break
            if progress:
                progress(i, len(parts), f"AI reading part {i + 1}/{len(parts)}")
            body = {"model": model, "stream": False, "keep_alive": "10m",
                    "options": {"temperature": 0, "top_p": 0.9, "num_ctx": 8192, "num_predict": 2048},
                    "messages": [{"role": "user", "content": PROMPT + ("" if len(parts) == 1 else
                                  f"\n(This is part {i + 1} of {len(parts)} of a page; transcribe only what is visible.)"),
                                  "images": [_to_png_b64(part)]}]}
            req = urllib.request.Request(self.url + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                out = json.loads(r.read())
            texts.append(clean_transcription(out.get("message", {}).get("content", "")))
        return merge_strips(texts)


# ====================================================================== B) Kraken
class KrakenEngine:
    key, name = "kraken", "B · Kraken handwriting model"

    def __init__(self, model_path=None, models_dir=None):
        self.model_path = model_path
        self.models_dir = models_dir
        self._net = None

    def find_model(self):
        if self.model_path and os.path.exists(self.model_path):
            return self.model_path
        dirs = [d for d in (self.models_dir, os.path.join(os.path.expanduser("~"), ".local", "share", "htrmopo"),
                            os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "htrmopo")) if d]
        for d in dirs:
            if os.path.isdir(d):
                for root, _, files in os.walk(d):
                    for f in sorted(files):
                        if f.endswith(".mlmodel") and "seg" not in f.lower():
                            return os.path.join(root, f)
        return None

    def available(self):
        try:
            import kraken  # noqa
        except Exception:
            return False, "Kraken is not installed (pip install kraken) — works on Mac/Linux; on Windows use WSL"
        m = self.find_model()
        if not m:
            return False, "No Hebrew recognition model (.mlmodel) found — put one in data/models"
        return True, os.path.basename(m)

    def read_image(self, img, strips=None, progress=None, cancel=None):
        from PIL import Image
        from kraken import blla, rpred
        from kraken.lib import models as kmodels
        if self._net is None:
            self._net = kmodels.load_any(self.find_model())
        gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        pil = Image.fromarray(gray)
        if progress:
            progress(0, 2, "Kraken: finding lines")
        seg = blla.segment(pil, text_direction="horizontal-rl")
        if progress:
            progress(1, 2, "Kraken: reading lines")
        lines = []
        for rec in rpred.rpred(self._net, pil, seg, bidi_reordering=True):
            if cancel and cancel():
                break
            lines.append(rec.prediction.strip())
        return clean_transcription("\n".join(lines))


# ====================================================================== C) Tesseract
def find_tesseract():
    # 1) portable copy shipped next to SeforimStudio.exe (or the app folder)
    here = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else sys.argv[0] or "."))
    for base in (here, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
        p = os.path.join(base, "tesseract", "tesseract.exe")
        if os.path.exists(p):
            return p
    exe = shutil.which("tesseract")
    if exe:
        return exe
    for p in (r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
              os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe"),
              "/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract"):
        if p and os.path.exists(p):
            return p
    return None


class TesseractEngine:
    key, name = "tesseract", "C · Tesseract (heb)"

    def available(self):
        exe = find_tesseract()
        if not exe:
            return False, "Tesseract not installed (Windows: UB-Mannheim installer, tick 'Hebrew')"
        try:
            langs = subprocess.run([exe, "--list-langs"], capture_output=True, text=True, timeout=10).stdout
        except Exception as e:  # noqa
            return False, str(e)
        if "heb" not in langs.split():
            return False, "Tesseract found but the Hebrew pack 'heb' is missing"
        return True, exe

    def read_image(self, img, strips=None, progress=None, cancel=None):
        import tempfile
        exe = find_tesseract()
        gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h = gray.shape[0]
        if h < 1800:  # tesseract likes ~30px letters
            f = 1800 / h
            gray = cv2.resize(gray, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "page.png")
            cv2.imwrite(p, gray)
            if progress:
                progress(0, 1, "Tesseract reading")
            r = subprocess.run([exe, p, "stdout", "-l", "heb", "--psm", "6"],
                               capture_output=True, text=True, encoding="utf-8", timeout=300)
        return clean_transcription(r.stdout)


# ====================================================================== registry
def engines(models_dir=None, ollama_model=None, kraken_model=None):
    return [OllamaEngine(ollama_model), KrakenEngine(kraken_model, models_dir), TesseractEngine()]


def status(models_dir=None, ollama_model=None, kraken_model=None):
    out = []
    for e in engines(models_dir, ollama_model, kraken_model):
        ok, info = e.available()
        out.append({"key": e.key, "name": e.name, "ok": ok, "info": info,
                    "models": (e.models() or []) if e.key == "ollama" else []})
    return out


def pick(key=None, **kw):
    es = engines(**kw)
    if key and key != "auto":
        e = next(x for x in es if x.key == key)
        ok, info = e.available()
        if not ok:
            raise RuntimeError(info)
        return e
    for e in es:
        if e.available()[0]:
            return e
    raise RuntimeError("No text-recognition engine is installed yet. See README → 'Handwriting engines'.")


def best_input(page_files, engine_key):
    """AI vision reads the cleaned colour photo best; Kraken/Tesseract prefer the enhanced grey/B&W."""
    return page_files["color"] if engine_key == "ollama" else page_files.get("gray") or page_files["bw"]


# ====================================================================== training samples (for Kraken fine-tuning)
def line_images(bw):
    """Split a cleaned black/white page into line images (projection profile). Returns list of (y0,y1)."""
    inv = (255 - bw) // 255
    prof = inv.sum(1).astype(np.float64)
    prof = np.convolve(prof, np.ones(9) / 9, mode="same")
    thr = max(prof.max() * 0.06, 2)
    rows, inside, y0 = [], False, 0
    for y, v in enumerate(prof):
        if v > thr and not inside:
            inside, y0 = True, y
        elif v <= thr and inside:
            inside = False
            if y - y0 > 12:
                rows.append((y0, y))
    if inside:
        rows.append((y0, len(prof)))
    pad = 6
    return [(max(0, a - pad), min(bw.shape[0], b + pad)) for a, b in rows]


def save_training_pairs(bw_path, text, out_dir, prefix):
    """Write line images + .gt.txt pairs (Kraken 'path' format) when line counts match."""
    bw = cv2.imdecode(np.fromfile(bw_path, np.uint8), cv2.IMREAD_GRAYSCALE)
    rows = line_images(bw)
    lines = [l for l in text.split("\n") if l.strip()]
    if len(rows) != len(lines):
        return {"ok": False, "lines_found": len(rows), "text_lines": len(lines)}
    os.makedirs(out_dir, exist_ok=True)
    for i, ((a, b), t) in enumerate(zip(rows, lines)):
        base = os.path.join(out_dir, f"{prefix}_{i + 1:03d}")
        ok, buf = cv2.imencode(".png", bw[a:b])
        buf.tofile(base + ".png")
        with open(base + ".gt.txt", "w", encoding="utf-8") as f:
            f.write(t.strip())
    return {"ok": True, "saved": len(lines), "folder": out_dir}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Read handwritten Hebrew from an image (Step 2).")
    ap.add_argument("image")
    ap.add_argument("--engine", default="auto", choices=["auto", "ollama", "kraken", "tesseract"])
    ap.add_argument("--model", default=None, help="Ollama model or Kraken .mlmodel path")
    a = ap.parse_args()
    for s in status(ollama_model=a.model, kraken_model=a.model):
        print(("✔ " if s["ok"] else "✘ ") + s["name"] + " — " + s["info"])
    eng = pick(a.engine, ollama_model=a.model, kraken_model=a.model)
    print("\nUsing", eng.name, "\n")
    sys.stdout.reconfigure(encoding="utf-8")
    print(eng.read_image(imread(a.image), progress=lambda i, n, l: print(f"  … {l}", file=sys.stderr)))
