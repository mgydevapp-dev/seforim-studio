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


def download_font_pack(dest, families=None, progress=None, cancel=None):
    families = list(dict.fromkeys(families or HEBREW_FONTS))
    got, failed = [], []
    for i, fam in enumerate(families):
        if cancel and cancel():
            break
        if progress:
            progress(i, len(families), fam)
        folder = os.path.join(dest, fam)
        if os.path.isdir(folder) and os.listdir(folder):
            got.append(fam)
            continue
        try:
            url = "https://fonts.googleapis.com/css2?family=" + fam.replace(" ", "+") + ":wght@400;700&display=swap"
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            css = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
            # keep the hebrew and latin subsets (each block is preceded by /* subset */)
            blocks = re.findall(r"/\*\s*([\w-]+)\s*\*/\s*@font-face\s*{([^}]*)}", css)
            if not blocks:
                blocks = [("all", b) for b in re.findall(r"@font-face\s*{([^}]*)}", css)]
            os.makedirs(folder, exist_ok=True)
            n = 0
            for subset, block in blocks:
                if subset not in ("hebrew", "latin", "all"):
                    continue
                m = re.search(r"url\((https://[^)]+)\)", block)
                w = re.search(r"font-weight:\s*(\d+)", block)
                if not m:
                    continue
                data = urllib.request.urlopen(urllib.request.Request(m.group(1), headers={"User-Agent": UA}), timeout=60).read()
                with open(os.path.join(folder, f"{subset}-{w.group(1) if w else '400'}.woff2"), "wb") as f:
                    f.write(data)
                n += 1
            (got if n else failed).append(fam)
        except Exception:
            failed.append(fam)
    if progress:
        progress(len(families), len(families), "done")
    return {"downloaded": got, "failed": failed}
