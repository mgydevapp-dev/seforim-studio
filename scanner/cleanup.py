"""STEP 1 — Image cleanup for handwritten Hebrew notes (OpenCV, fully offline).

Pipeline per page:
  load (fix phone EXIF rotation) → find the paper & fix perspective → rough orientation (portrait/landscape)
  → deskew (projection-profile search) → remove shadows / even out lighting → boost contrast (CLAHE, contrast
  stretch for faint pencil) → denoise → binarize (Sauvola, good for pencil) → remove specks.
Outputs per page:  color (cleaned photo for AI vision models), gray (enhanced, for Kraken/Tesseract),
                   bw (black & white).
Also: extract_document_text() pulls text directly from PDFs with a text layer, Word and text files (no OCR).

Command line test:
    python -m scanner.cleanup photo1.jpg notes.pdf --out cleaned_folder
"""
import argparse
import os
import sys

import cv2
import numpy as np

MAX_SIDE = 3600  # pixels; bigger pages are scaled down (plenty for handwriting, keeps it fast)
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".heic"}


# ---------------------------------------------------------------- loading
def load_pages(path, dpi=300):
    """Return list of (label, BGR image). PDFs → one image per page (needs PyMuPDF)."""
    ext = os.path.splitext(path)[1].lower()
    name = os.path.basename(path)
    if ext == ".pdf":
        import pypdfium2 as pdfium
        out = []
        pdf = pdfium.PdfDocument(path)
        try:
            for i in range(len(pdf)):
                w_pt, h_pt = pdf[i].get_size()
                scale = min(dpi / 72, MAX_SIDE / max(w_pt, h_pt))
                pil = pdf[i].render(scale=scale).to_pil().convert("RGB")
                out.append((f"{name} p{i + 1}", cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)))
        finally:
            pdf.close()
        return out
    try:
        from PIL import Image, ImageOps
        im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        return [(name, cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR))]
    except Exception:
        img = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)  # works with Hebrew file names on Windows
        if img is None:
            raise ValueError(f"Cannot read image: {path}")
        return [(name, img)]


# ---------------------------------------------------------------- page detection
def _order_points(pts):
    pts = pts.reshape(4, 2).astype("float32")
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype="float32")


def find_page(img, min_area=0.20):
    """Find the paper outline (4 corners) or None."""
    h, w = img.shape[:2]
    scale = 1000.0 / max(h, w)
    small = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else img.copy()
    scale = min(scale, 1.0)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    candidates = []
    # 1) edges
    edges = cv2.Canny(gray, 40, 140)
    edges = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=2)
    candidates.append(edges)
    # 2) bright paper region (paper is lighter than the table)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    candidates.append(th)
    area_img = small.shape[0] * small.shape[1]
    best = None
    for mask in candidates:
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in sorted(cnts, key=cv2.contourArea, reverse=True)[:5]:
            area = cv2.contourArea(c)
            if area < min_area * area_img or area > 0.98 * area_img:
                continue
            peri = cv2.arcLength(c, True)
            for eps in (0.02, 0.03, 0.05):
                approx = cv2.approxPolyDP(c, eps * peri, True)
                if len(approx) == 4 and cv2.isContourConvex(approx):
                    if best is None or area > best[0]:
                        best = (area, approx)
                    break
    if best is None:
        return None
    quad = _order_points(best[1])
    # Only crop if what lies outside the quad looks like background (clearly darker / different from the paper).
    mask = np.zeros(gray.shape, np.uint8)
    cv2.fillConvexPoly(mask, quad.astype(np.int32), 255)
    inside = gray[mask > 0]
    outside = gray[mask == 0]
    if outside.size < 0.03 * gray.size:
        return quad / scale
    hh, ww = gray.shape
    mx, my = 0.03 * ww, 0.03 * hh
    sides = sum([quad[:, 0].min() > mx, quad[:, 0].max() < ww - mx, quad[:, 1].min() > my, quad[:, 1].max() < hh - my])
    if sides < 2:
        return None  # background on only one side = a shadow edge, not a sheet of paper
    if np.median(outside) > 0.78 * np.median(inside) and abs(float(np.std(outside)) - float(np.std(inside))) < 25:
        return None  # paper fills the frame — the "edge" was a shadow or fold, don't cut text off
    return quad / scale


def warp_page(img, quad):
    tl, tr, br, bl = quad
    wid = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    hei = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    dst = np.array([[0, 0], [wid - 1, 0], [wid - 1, hei - 1], [0, hei - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(quad.astype("float32"), dst)
    out = cv2.warpPerspective(img, M, (wid, hei), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return trim(out, 0.012)


def trim(img, frac):
    """Cut a thin margin (removes the table/edge shadow left around the paper)."""
    h, w = img.shape[:2]
    dy, dx = int(h * frac), int(w * frac)
    return img[dy:h - dy, dx:w - dx].copy()


def _inner(inv, frac=0.04):
    h, w = inv.shape
    out = np.zeros_like(inv)
    dy, dx = int(h * frac), int(w * frac)
    out[dy:h - dy, dx:w - dx] = inv[dy:h - dy, dx:w - dx]
    return out


# ---------------------------------------------------------------- lighting / contrast
def flatten_illumination(img):
    """Divide by an estimated background → removes shadows and uneven light, keeps colour."""
    out = np.empty_like(img)
    k = max(31, (min(img.shape[:2]) // 25) | 1)
    for c in range(3):
        ch = img[:, :, c]
        bg = cv2.morphologyEx(ch, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        bg = cv2.medianBlur(bg, 21)
        norm = cv2.divide(ch, bg, scale=255)
        out[:, :, c] = norm
    return out


def stretch(gray, lo=1, hi=99):
    """Percentile contrast stretch — makes faint pencil darker."""
    a, b = np.percentile(gray, (lo, hi))
    if b - a < 5:
        return gray
    return np.clip((gray.astype(np.float32) - a) * 255.0 / (b - a), 0, 255).astype(np.uint8)


def clahe(gray, clip=2.0):
    return cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8)).apply(gray)


def sauvola(gray, window=None, k=0.2, R=128):
    """Sauvola binarization implemented with box filters (no opencv-contrib needed)."""
    if window is None:
        window = max(15, (min(gray.shape) // 40) | 1)
    g = gray.astype(np.float64)
    mean = cv2.boxFilter(g, -1, (window, window), borderType=cv2.BORDER_REFLECT)
    sqmean = cv2.boxFilter(g * g, -1, (window, window), borderType=cv2.BORDER_REFLECT)
    std = np.sqrt(np.maximum(sqmean - mean * mean, 0))
    thresh = mean * (1 + k * (std / R - 1))
    return np.where(g > thresh, 255, 0).astype(np.uint8)


def remove_ruled_lines(bw):
    """Remove long horizontal notebook lines while keeping letters that touch them."""
    inv = 255 - bw
    w = bw.shape[1]
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(40, w // 12), 1))
    lines = cv2.morphologyEx(inv, cv2.MORPH_OPEN, kernel)
    lines = cv2.dilate(lines, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    cleaned = cv2.subtract(inv, lines)
    # repair letter strokes cut by the removal
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5)))
    return 255 - cleaned


def remove_specks(bw, min_area=None):
    inv = 255 - bw
    n, labels, stats, _ = cv2.connectedComponentsWithStats(inv, connectivity=8)
    if min_area is None:
        min_area = max(4, int(bw.shape[0] * bw.shape[1] * 2e-6))
    keep = np.zeros(n, bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_area
    return np.where(keep[labels], 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- orientation & skew
def _profile_score(bw_inv, angle):
    h, w = bw_inv.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    rot = cv2.warpAffine(bw_inv, M, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
    prof = rot.sum(axis=1, dtype=np.float64)
    return np.var(prof)


def estimate_skew(gray, max_angle=15.0):
    small = gray
    s = 800.0 / max(gray.shape)
    if s < 1:
        small = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    bw = sauvola(small)
    inv = _inner(((255 - bw) // 255).astype(np.uint8))
    best_a, best = 0.0, -1
    for a in np.arange(-max_angle, max_angle + 0.01, 1.0):
        sc = _profile_score(inv, a)
        if sc > best:
            best, best_a = sc, a
    center = best_a
    for a in np.arange(center - 1, center + 1.01, 0.1):
        sc = _profile_score(inv, a)
        if sc > best:
            best, best_a = sc, a
    return float(best_a)


def rotate(img, angle, border=(255, 255, 255)):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    cos, sin = abs(M[0, 0]), abs(M[0, 1])
    nw, nh = int(h * sin + w * cos), int(h * cos + w * sin)
    M[0, 2] += nw / 2 - w / 2
    M[1, 2] += nh / 2 - h / 2
    bv = border if img.ndim == 3 else border[0]
    return cv2.warpAffine(img, M, (nw, nh), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=bv)


def text_is_vertical(gray):
    """True if text lines run vertically (page photographed sideways): compares the best
    line-profile score (over small tilts) of the page vs the page turned 90°."""
    sc = 500.0 / max(gray.shape)
    small = cv2.resize(gray, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA) if sc < 1 else gray
    inv = _inner(((255 - sauvola(small)) // 255).astype(np.uint8))
    turned = np.ascontiguousarray(np.rot90(inv))
    best = lambda m: max(_profile_score(m, a) for a in np.arange(-15, 15.1, 1.5))
    return best(turned) > best(inv) * 1.15


# ---------------------------------------------------------------- main pipeline
DEFAULTS = {"crop": True, "orient": True, "deskew": True, "shadows": True, "faint": True, "denoise": True,
            "specks": True, "lines": True, "rotate_extra": 0}


def clean_page(img, opts=None):
    """Returns dict(color, gray, bw, info)."""
    o = dict(DEFAULTS, **(opts or {}))
    info = {}
    if max(img.shape[:2]) > MAX_SIDE:
        f = MAX_SIDE / max(img.shape[:2])
        img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    work = img.copy()
    if o["crop"]:
        quad = find_page(work)
        if quad is not None:
            work = warp_page(work, quad)
            info["page_found"] = True
        else:
            info["page_found"] = False
    if o.get("rotate_extra"):
        k = int(o["rotate_extra"]) // 90 % 4
        work = np.ascontiguousarray(np.rot90(work, -k))
    color = flatten_illumination(work) if o["shadows"] else work
    gray = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
    if o["orient"] and text_is_vertical(gray):
        color = np.ascontiguousarray(np.rot90(color, -1))
        gray = np.ascontiguousarray(np.rot90(gray, -1))
        info["rotated_90"] = True
    if o["deskew"]:
        ang = estimate_skew(gray)
        info["skew_deg"] = round(ang, 2)
        if abs(ang) > 0.15:
            color = rotate(color, ang)
            gray = rotate(gray, ang)
    if o["faint"]:
        gray = stretch(gray, 1, 99.5)
    gray = clahe(gray, 2.0)
    if o["denoise"]:
        gray = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=15)
        color = cv2.bilateralFilter(color, 5, 30, 5)
    bw = sauvola(gray, k=0.15 if o["faint"] else 0.25)
    if o.get("lines"):
        bw = remove_ruled_lines(bw)
    if o["specks"]:
        bw = remove_specks(bw)
    info["size"] = [int(bw.shape[1]), int(bw.shape[0])]
    return {"color": color, "gray": gray, "bw": bw, "info": info}


def split_strips(img, n=None, overlap=0.12, max_h=1400):
    """Split a tall page into overlapping horizontal strips (used later by the AI reader)."""
    h = img.shape[0]
    if n is None:
        n = max(1, int(np.ceil(h / max_h)))
    if n == 1:
        return [img]
    step = h / n
    ov = int(step * overlap)
    return [img[max(0, int(i * step) - ov): min(h, int((i + 1) * step) + ov)] for i in range(n)]


def imwrite(path, img):
    ok, buf = cv2.imencode(os.path.splitext(path)[1] or ".png", img)
    if ok:
        buf.tofile(path)  # works with Hebrew folder names on Windows
    return ok


def process_files(paths, out_dir, opts=None, progress=None):
    os.makedirs(out_dir, exist_ok=True)
    pages = []
    for p in paths:
        pages += load_pages(p)
    results = []
    for i, (label, img) in enumerate(pages):
        if progress:
            progress(i, len(pages), label)
        r = clean_page(img, opts)
        base = os.path.join(out_dir, f"page_{i + 1:03d}")
        for kind in ("color", "gray", "bw"):
            imwrite(f"{base}_{kind}.png", r[kind])
        imwrite(f"{base}_original.jpg", img)
        results.append({"page": i + 1, "label": label, "info": r["info"],
                        "files": {k: f"{base}_{k}.png" for k in ("color", "gray", "bw")} | {"original": f"{base}_original.jpg"}})
    if progress:
        progress(len(pages), len(pages), "done")
    return results


def extract_document_text(path):
    """Text straight from documents (no OCR): PDF text layer, .docx, .txt/.md/.html.
    Returns list of page texts; a PDF page with no text layer returns '' (it needs OCR)."""
    ext = os.path.splitext(path)[1].lower()
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core import formats
    if ext == ".pdf":
        return formats.pdf_text_pages(path)
    _, _, text = formats.import_file(path)
    return [text]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Clean photos/scans of handwritten Hebrew (Step 1).")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", default="cleaned")
    ap.add_argument("--no-crop", action="store_true")
    ap.add_argument("--no-deskew", action="store_true")
    a = ap.parse_args()
    res = process_files(a.files, a.out, {"crop": not a.no_crop, "deskew": not a.no_deskew},
                        lambda i, n, l: print(f"[{i}/{n}] {l}"))
    for r in res:
        print(r["page"], r["label"], r["info"])
    print("Saved to", os.path.abspath(a.out))
