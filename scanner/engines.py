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

try:
    from core import winproc
except ImportError:  # running scanner/engines.py on its own
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core import winproc

def _ollama_url():
    h = (os.environ.get("OLLAMA_HOST") or "").strip()
    if not h or h.startswith("0.0.0.0") or h.startswith("[::]"):
        return "http://127.0.0.1:11434"
    if not h.startswith("http"):
        h = "http://" + h
    if h.count(":") < 2:
        h += ":11434"
    return h.rstrip("/")


OLLAMA_URL = _ollama_url()
# Talk to the AI on this computer directly - never through a proxy / internet filter (e.g. NetFree), which breaks
# local addresses and gives "https" / certificate errors.
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))
AI_DEBUG = os.environ.get("SEFORIM_AI_DEBUG")
if not OLLAMA_URL.startswith("http"):
    OLLAMA_URL = "http://" + OLLAMA_URL
VISION_HINTS = ("vl", "vision", "llava", "gemma3", "minicpm-v", "moondream", "llama4", "mistral-small3", "granite3.2-vision")
PREFERRED = ["qwen3-vl:8b-instruct", "qwen3-vl:4b-instruct", "qwen3-vl:8b", "qwen3-vl:latest", "qwen3-vl:4b", "qwen3-vl:30b", "qwen3-vl:32b", "qwen3-vl:2b", "qwen2.5vl:7b", "gemma3:12b"]

PROMPT = """You are a careful transcriber of handwritten Hebrew.
Transcribe ALL the Hebrew handwriting in this image exactly as written, line by line, top to bottom.
The writing is often modern Hebrew CURSIVE script (כתב יד), not print letters. Write every letter in its printed (block) form.
Hebrew is written right to left: the first letter of each line is on the RIGHT.
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


def _to_png_b64(img, max_side=1100):
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

    def __init__(self, model=None, url=OLLAMA_URL, timeout=1800):
        self.url, self.timeout = url, timeout
        self.model = model

    def _get(self, path, timeout=3):
        with _LOCAL.open(self.url + path, timeout=timeout) as r:
            return json.loads(r.read())

    def _post(self, path, body):
        req = urllib.request.Request(self.url + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with _LOCAL.open(req, timeout=self.timeout) as r:
            return json.loads(r.read())

    def _ask(self, body):
        """Ask the AI; copes with Ollama versions with/without the "think" switch and with thinking models."""
        def text_of(out):
            msg = out.get("message") or {}
            c = msg.get("content") if msg else out.get("response", "")
            c = c or ""
            if "</think>" in c:
                c = c.split("</think>", 1)[1]
            return c.strip(), (msg.get("thinking") or out.get("thinking") or "")
        tries = [("chat", body)]
        b2 = dict(body)
        b2.pop("think", None)
        b2["messages"] = [dict(body["messages"][0], content="/no_think\n" + body["messages"][0]["content"])]
        tries.append(("chat", b2))
        g = {"model": body["model"], "stream": False, "think": False, "keep_alive": body.get("keep_alive"), "options": body["options"],
             "prompt": body["messages"][0]["content"], "images": body["messages"][0]["images"]}
        tries.append(("generate", g))
        last = ""
        for kind, b in tries:
            try:
                out = self._post("/api/" + kind, b)
            except urllib.error.HTTPError as e:
                last = f"{kind}: HTTP {e.code} {e.read()[:300]!r}"
                continue
            c, thinking = text_of(out)
            if AI_DEBUG:
                with open(AI_DEBUG, "a", encoding="utf-8") as f:
                    f.write(f"--- {kind} keys={list(out)} done_reason={out.get('done_reason')} eval_count={out.get('eval_count')} "
                            f"prompt_eval_count={out.get('prompt_eval_count')} content={c[:300]!r} thinking={thinking[:300]!r}\n")
            if c:
                return c
            last = f"{kind}: empty answer (done_reason={out.get('done_reason')}, thinking {len(thinking)} chars)"
        print("AI gave no text:", last, flush=True)
        raise RuntimeError("The AI gave no text for this page (" + last + "). Try 'Unclear / messy' or the Tesseract reader.")

    def warm_up(self):
        """Load the AI model into memory in the background when the app starts, so the first page is read quickly."""
        model = self.pick_model()
        if model:
            try:
                self._post("/api/generate", {"model": model, "prompt": "", "keep_alive": "60m", "stream": False})
            except Exception:
                pass

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
            return False, "AI pack not installed - download the SeforimAI.tar.part files into Downloads and press 'Install AI pack'"
        if not vis:
            return False, "Ollama is running but no vision model is installed. Run: ollama pull qwen3-vl:8b"
        return True, f"model {self.pick_model()}"

    def read_image(self, img, strips=None, progress=None, cancel=None):
        model = self.pick_model()
        if not model:
            raise RuntimeError(self.available()[1])
        h, w = img.shape[:2]
        if strips is None:
            strips = 1  # one look at the whole page is fastest; 'Unclear / messy' reads in parts
        parts = split_strips(img, strips, overlap=0.12) if strips > 1 else [img]
        texts = []
        for i, part in enumerate(parts):
            if cancel and cancel():
                break
            if progress:
                progress(i, len(parts), f"AI reading part {i + 1}/{len(parts)}")
            body = {"model": model, "stream": False, "keep_alive": "60m", "think": False,  # no hidden "thinking": just read
                    "options": {"temperature": 0, "top_p": 0.9, "num_ctx": 4096, "num_predict": 1200,
                                "num_thread": max(1, (os.cpu_count() or 4)), "repeat_penalty": 1.05},
                    "messages": [{"role": "user", "content": PROMPT + ("" if len(parts) == 1 else
                                  f"\n(This is part {i + 1} of {len(parts)} of a page; transcribe only what is visible.)"),
                                  "images": [_to_png_b64(part)]}]}
            req = urllib.request.Request(self.url + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            content = self._ask(body)
            texts.append(clean_transcription(content))
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
        if os.name == "nt":
            return False, "Kraken does not run on Windows (only Mac/Linux) - the AI reader (A) is the best choice for handwriting"
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
            r = winproc.run([exe, "--list-langs"], timeout=20)
            langs = (r.stdout or "") + (r.stderr or "")
        except Exception as e:  # noqa
            return False, str(e)
        ll = langs.split()
        if "heb" not in ll:
            return False, "Tesseract found but the Hebrew pack 'heb' is missing"
        self.script = "heb_script" in ll or os.path.exists(_script_model())
        return True, exe + ("  · print + cursive (כתב) models" if self.script else "  · print model")

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
            # print model and the cursive (כתב) model; page layouts: a block / columns / scattered letters.
            # Whatever reads as the most real Hebrew wins.
            td = []
            have = (winproc.run([exe, "--list-langs"], timeout=20).stdout or "").split()
            if os.path.exists(_script_model()):
                tdir = _tessdata_with_script(exe)
                td = ["--tessdata-dir", tdir]
                have = [f[:-12] for f in os.listdir(tdir) if f.endswith(".traineddata")]
            # +eng: English words on the page (labels, names) are read as English instead of turning into Hebrew junk
            plus = "+eng" if "eng" in have else ""
            script = "heb_script" in have
            if getattr(self, "kind", "") == "hand":   # handwriting: Hebrew-only models first (English letters would turn into junk)
                langs = (["heb_script"] if script else []) + ["heb"] + (["heb_script" + plus] if script and plus else [])
            else:
                langs = ["heb" + plus] + (["heb_script" + plus] if script else [])
            best, best_q = "", -1
            tries = [(l, psm) for l in langs for psm in ("6", "4", "11")]
            for k, (lang, psm) in enumerate(tries):
                if cancel and cancel():
                    break
                if progress:
                    progress(k, len(tries), f"Reading ({'cursive' if lang.startswith('heb_script') else 'print'} model, layout {psm})")
                r = winproc.run([exe, p, "stdout", *td, "-l", lang, "--psm", psm], timeout=300)
                if r.returncode != 0 and not (r.stdout or "").strip():
                    if k == 0:
                        raise RuntimeError("Tesseract failed: " + (r.stderr or "").strip()[-300:])
                    continue
                txt = clean_transcription(re.sub("[\u200e\u200f\u202a-\u202e]", "", r.stdout))
                q = text_quality(txt) * (1 + 0.02 * min(len(txt.split()), 20))  # prefer reading more of the page
                if getattr(self, "kind", "") == "hand" and lang.startswith("heb_script"):
                    q *= 1.15
                elif getattr(self, "kind", "") == "print" and not lang.startswith("heb_script"):
                    q *= 1.15
                if q > best_q:
                    best, best_q = txt, q
        return strip_noise(best)


def _script_model():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "scanner", "models", "heb_script.traineddata")


def _tessdata_with_script(exe):
    """A tessdata folder that has both heb and heb_script (copied once next to the app's data)."""
    import tempfile
    d = os.path.join(tempfile.gettempdir(), "seforim_tessdata")
    os.makedirs(d, exist_ok=True)
    src = os.environ.get("TESSDATA_PREFIX") or ""
    cands = [os.path.join(os.path.dirname(exe), "tessdata"), src, os.path.join(src, "tessdata"),
             "/usr/share/tesseract-ocr/5/tessdata", "/usr/share/tesseract-ocr/4.00/tessdata", "/usr/local/share/tessdata"]
    for name, from_ in (("heb.traineddata", None), ("heb_script.traineddata", _script_model()), ("osd.traineddata", None),
                        ("eng.traineddata", None)):
        t = os.path.join(d, name)
        if os.path.exists(t) and (not from_ or os.path.getsize(t) == os.path.getsize(from_)):
            continue
        f = from_ or next((os.path.join(c, name) for c in cands if c and os.path.exists(os.path.join(c, name))), None)
        if f:
            shutil.copyfile(f, t)
    return d


# ====================================================================== is the text real Hebrew or random symbols?
_HEB = re.compile(r"[\u05d0-\u05ea]")
KNOWN_WORDS = set()  # filled by the app from the library's word list (for a better check)


def text_quality(text):
    """0..1 - how much of the output looks like real Hebrew words (not symbols / letter salad)."""
    toks = [t for t in re.split(r"\s+", text or "") if t]
    if not toks:
        return 0.0
    good = 0
    for t in toks:
        letters = _HEB.findall(t)
        core = "".join(letters)
        junk = sum(1 for c in t if not (_HEB.match(c) or c in "\"'׳״-.,:;!?()[]0123456789\u05b0-\u05c7"))
        if re.fullmatch(r"[A-Z]?[a-z]{2,}[.,:;!?]?", t) and re.search(r"[aeiouy]", t.lower()) and not re.search(r"(.)\1\1", t):
            good += 0.6  # looks like an English word
        elif len(core) >= 2 and junk == 0:
            good += 1.0 if (not KNOWN_WORDS or core in KNOWN_WORDS or core.lstrip("ובכלמהש") in KNOWN_WORDS) else 0.5
    return good / len(toks)


def strip_noise(text):
    """Drop stray symbols Tesseract invents around Hebrew text (| ~ _ » etc.)."""
    out = []
    for line in (text or "").splitlines():
        line = re.sub(r"[|~_^`«»<>{}\\@#$%&*=+§©®™¦]+", " ", line)
        line = re.sub(r"(?<!\S)[^\u05d0-\u05ea\w\s](?!\S)", " ", line)  # lone symbols
        line = re.sub(r" {2,}", " ", line).strip()
        if line and (len(_HEB.findall(line)) >= 2 or re.search(r"\w{2,}", line)):
            out.append(line)
    return "\n".join(out)


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
