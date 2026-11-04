"""One-time download of free (open-license) Hebrew fonts from Google Fonts into data/fonts/<Family>/.
After that they work offline inside the app (editor, reader, cover designer)."""
import os
import re
import urllib.request

HEBREW_FONTS = [
    # serif / sefer style
    "Frank Ruhl Libre", "David Libre", "Noto Serif Hebrew", "Noto Rashi Hebrew", "Bona Nova SC", 
    "Tinos", "Cousine", "Bellefair", "Suez One", "Bona Nova",
    # sans
    "Heebo", "Assistant", "Rubik", "Alef", "Varela Round", "Noto Sans Hebrew", "Open Sans", "Arimo", "IBM Plex Sans Hebrew",
    "Secular One", "Miriam Libre", "Karantina", "Amatic SC",
    # display / handwriting
    "Solitreo", "Gveret Levin", "Fredoka", "Playpen Sans Hebrew", "Rubik Doodle Shadow",
    "Rubik Glitch", "Rubik Puddles", "Rubik Wet Paint", "Rubik Vinyl", "Rubik Dirt", "Rubik Beastly", "Rubik Bubbles",
    "Rubik Mono One", "Rubik Moonrocks", "Rubik Spray Paint", "Rubik Burned", "Rubik Microbe", "Rubik Iso",
    "Rubik Distressed", "Rubik Maze", "Rubik Marker Hatch", "Rubik Storm", "Rubik Lines", "Rubik Pixels",
    "Rubik 80s Fade", "Rubik Gemstones", "Rubik Maps", "Rubik Scribble", "Rubik Broken Fax",
]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def _css(fam, weights):
    url = "https://fonts.googleapis.com/css2?family=" + fam.replace(" ", "+") + (f":wght@{weights}" if weights else "")
    # A plain (non-browser) client gets full TrueType files - these work in the app AND in Microsoft Word.
    req = urllib.request.Request(url, headers={"User-Agent": "SeforimStudio/1.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")


def download_font_pack(dest, families=None, progress=None, cancel=None):
    """Download each family as TrueType (.ttf, regular + bold where available) into dest/<Family>/."""
    families = list(dict.fromkeys(families or HEBREW_FONTS))
    got, failed = [], []
    for i, fam in enumerate(families):
        if cancel and cancel():
            break
        if progress:
            progress(i, len(families), fam)
        folder = os.path.join(dest, fam)
        if os.path.isdir(folder) and any(f.endswith(".ttf") for f in os.listdir(folder)):
            got.append(fam)
            continue
        try:
            css = None
            for w in ("400;700", "400", None):
                try:
                    css = _css(fam, w)
                    break
                except Exception:
                    continue
            if not css:
                raise RuntimeError("not available")
            os.makedirs(folder, exist_ok=True)
            n = 0
            for block in re.findall(r"@font-face\s*{([^}]*)}", css):
                m = re.search(r"url\((https://[^)]+)\)", block)
                w = re.search(r"font-weight:\s*(\d+)", block)
                if not m:
                    continue
                weight = w.group(1) if w else "400"
                data = urllib.request.urlopen(urllib.request.Request(m.group(1), headers={"User-Agent": "SeforimStudio/1.0"}), timeout=60).read()
                ext = ".ttf" if data[:4] in (b"\x00\x01\x00\x00", b"true", b"OTTO") else ".woff2"
                name = f"{fam.replace(' ', '')}-{'Bold' if weight == '700' else 'Regular'}-{weight}{ext}"
                with open(os.path.join(folder, name), "wb") as f:
                    f.write(data)
                n += 1
            # remove older browser-only copies
            for old in os.listdir(folder):
                if old.endswith(".woff2") and n:
                    os.remove(os.path.join(folder, old))
            (got if n else failed).append(fam)
        except Exception:
            failed.append(fam)
    if progress:
        progress(len(families), len(families), "done")
    return {"downloaded": got, "failed": failed}


def install_windows(fonts_dir):
    """Install the .ttf fonts for the current Windows user (no admin needed) so Word and other programs can use them."""
    import glob
    import shutil
    if os.name != "nt":
        return {"installed": 0, "message": "Only needed on Windows"}
    import winreg
    import ctypes
    target = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")
    os.makedirs(target, exist_ok=True)
    n = 0
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts")
    for p in glob.glob(os.path.join(fonts_dir, "*", "*.ttf")):
        fam = os.path.basename(os.path.dirname(p))
        bold = "-Bold-" in os.path.basename(p)
        dest = os.path.join(target, os.path.basename(p))
        try:
            if not os.path.exists(dest):
                shutil.copy2(p, dest)
            winreg.SetValueEx(key, f"{fam}{' Bold' if bold else ''} (TrueType)", 0, winreg.REG_SZ, dest)
            ctypes.windll.gdi32.AddFontResourceW(dest)
            n += 1
        except Exception:
            pass
    winreg.CloseKey(key)
    try:  # tell running programs that new fonts are available
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001D, 0, 0, 0x0002, 1000, None)
    except Exception:
        pass
    return {"installed": n, "message": f"{n} font files installed for Word and other programs"}
