"""SeforimStudio-Setup.exe — one double-click installs Seforim Studio (no admin rights needed).

Puts the whole portable app into a folder (default: <your user folder>\\SeforimStudio), keeps your notes and library when
updating, makes Desktop + Start-menu shortcuts, installs the Hebrew fonts into Windows (so Word can use them too),
and starts the app.  The folder stays portable: copy it to any offline computer.

Silent mode (for testing):  SeforimStudio-Setup.exe --silent --dir C:\\some\\folder [--no-launch] [--no-shortcuts] [--no-fonts] [--allusers]

For ALL users of the computer (--allusers, asks for administrator once): the app goes to Program Files, and the library,
AI models and fonts go ONCE into C:\\ProgramData\\SeforimStudio, shared by everyone. Each Windows user keeps their own
notes and settings (in their own AppData).
"""
import argparse
import ctypes
import glob
import os
import shutil
import subprocess
import sys
import threading
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from core import installer as INST  # the same unpacking code the app uses
except Exception:  # noqa
    INST = None

APP = "Seforim Studio"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def payload():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    p = os.path.join(base, "SeforimStudio-Portable.zip")
    if not os.path.exists(p):
        raise FileNotFoundError("The setup file is damaged (app package missing). Please download it again.")
    return p


PROGRAM_FILES = os.path.join(os.environ.get("ProgramW6432") or os.environ.get("ProgramFiles") or "C:\\Program Files", "Seforim Studio")
SHARED = os.path.join(os.environ.get("ProgramData") or "C:\\ProgramData", "SeforimStudio")


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin(args):
    """Start Setup again with administrator rights (Windows shows the 'Yes / No' question)."""
    exe = sys.executable
    params = " ".join(f'"{a}"' for a in (args if getattr(sys, "frozen", False) else [os.path.abspath(__file__)] + args))
    r = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    return r > 32


def install(dest, log=print, progress=lambda f: None, shared=None):
    os.makedirs(dest, exist_ok=True)
    if shared:
        os.makedirs(shared, exist_ok=True)
    with zipfile.ZipFile(payload()) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        prefix = os.path.commonprefix(names)
        prefix = prefix[:prefix.rfind("/") + 1] if "/" in prefix else ""
        kept = 0
        for i, n in enumerate(names):
            rel = n[len(prefix):]
            if not rel:
                continue
            out = os.path.join(dest, *rel.split("/"))
            if shared and rel.startswith("data/"):  # all users: library, fonts, catalog -> the one shared folder
                out = os.path.join(shared, *rel.split("/")[1:])
            # When updating: never overwrite the user's library, notes or settings in data\
            if rel.startswith("data/") and os.path.exists(out):
                kept += 1
                continue
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with z.open(n) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
            if i % 40 == 0:
                progress(i / len(names))
    progress(1.0)
    if shared:
        import json
        json.dump({"mode": "allusers", "shared": shared}, open(os.path.join(dest, "install.json"), "w", encoding="utf-8"))
        # every user may add to the shared library / AI models (e.g. when another user installs the AI pack)
        subprocess.run(["icacls", shared, "/grant", "*S-1-5-32-545:(OI)(CI)M", "/T", "/Q"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)
        log(f"Shared library / AI folder for all users: {shared}")
    log(f"Installed to {dest}" + (f" (kept {kept} of your existing data files)" if kept else ""))
    return os.path.join(dest, "SeforimStudio.exe")


def make_shortcuts(exe, all_users=False):
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    menu = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")
    if all_users:
        desktop = os.path.join(os.environ.get("PUBLIC", "C:\\Users\\Public"), "Desktop")
        menu = os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "Microsoft", "Windows", "Start Menu", "Programs")
    for folder in (desktop, menu):
        if not os.path.isdir(folder):
            continue
        lnk = os.path.join(folder, f"{APP}.lnk")
        ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');$s.TargetPath='{exe}';"
              f"$s.WorkingDirectory='{os.path.dirname(exe)}';$s.IconLocation='{exe},0';$s.Description='{APP}';$s.Save()")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)


def install_fonts(dest, all_users=False, fonts_dir=None):
    import winreg
    target = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")
    hive = winreg.HKEY_CURRENT_USER
    if all_users:
        target = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
        hive = winreg.HKEY_LOCAL_MACHINE
    os.makedirs(target, exist_ok=True)
    key = winreg.CreateKey(hive, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts")
    n = 0
    for p in glob.glob(os.path.join(fonts_dir or os.path.join(dest, "data", "fonts"), "*", "*.ttf")):
        fam = os.path.basename(os.path.dirname(p))
        bold = "-Bold-" in os.path.basename(p)
        d = os.path.join(target, os.path.basename(p))
        try:
            if not os.path.exists(d):
                shutil.copy2(p, d)
            winreg.SetValueEx(key, f"{fam}{' Bold' if bold else ''} (TrueType)", 0, winreg.REG_SZ, os.path.basename(d) if all_users else d)
            ctypes.windll.gdi32.AddFontResourceW(d)
            n += 1
        except Exception:
            pass
    winreg.CloseKey(key)
    try:
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001D, 0, 0, 0x0002, 1000, None)
    except Exception:
        pass
    return n


def library_parts_hint():
    here = os.path.dirname(os.path.abspath(sys.executable))
    for d in (here, os.path.join(os.path.expanduser("~"), "Downloads"), os.path.join(os.path.expanduser("~"), "Desktop")):
        if glob.glob(os.path.join(d, "SeforimLibrary.sqlite.xz*")):
            return d
    return None


def copy_packs(dest, log=print):
    """Library / AI part files sitting next to Setup (e.g. all on one USB stick) are copied into the app folder,
    where the app installs them on first start - so the whole thing works on an offline computer."""
    here = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
    n = 0
    for p in glob.glob(os.path.join(here, "SeforimLibrary.sqlite.xz*")) + glob.glob(os.path.join(here, "SeforimMore.sqlite.xz*")):
        if p.lower().endswith((".crdownload", ".partial", ".download", ".tmp", ".opdownload")):
            log(f"{os.path.basename(p)} has not finished downloading - skipped")
            continue
        target = os.path.join(dest, os.path.basename(p))
        if os.path.abspath(p) == os.path.abspath(target) or (os.path.exists(target) and os.path.getsize(target) == os.path.getsize(p)):
            continue
        log(f"Copying {os.path.basename(p)}…")
        shutil.copyfile(p, target)
        n += 1
    return n


def install_ai(data_dir, log=print, progress=lambda f: None):
    """Install the AI handwriting reader during Setup (no waiting when the app opens).
    The 3 SeforimAI.tar.part files are taken from next to Setup, Downloads, Desktop or a USB stick."""
    if INST is None:
        return False
    here = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
    found = INST.scan(INST.search_dirs(here, data_dir, here), INST.PACKS["ai"])
    parts = found["parts"]
    if not parts:
        if found["problem"]:
            log("AI reader: " + found["problem"])
        else:
            log("AI reader files (SeforimAI.tar.part1of3 …) not found next to Setup or in Downloads - you can add them later.")
        return False
    if INST.already_installed(data_dir, parts, "ai") and os.path.isdir(os.path.join(data_dir, "ai", "models")):
        log("AI handwriting reader is already installed")
        return True
    log("Installing the AI handwriting reader (5.6 GB, a few minutes)…")
    INST.extract_tar(parts, data_dir, lambda f: progress(f))
    INST.mark_installed(data_dir, parts, "ai")
    log("AI handwriting reader installed ✓")
    return True


def install_library(data_dir, log=print, progress=lambda f: None):
    """Unpack the complete library during Setup too (when this computer does not have it yet)."""
    if INST is None:
        return False
    here = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
    found = INST.scan(INST.search_dirs(here, data_dir, here), INST.PACKS["library"])
    parts = found["parts"]
    target = os.path.join(data_dir, "library.sqlite")
    if not parts or INST.already_installed(data_dir, parts):
        return False
    if os.path.exists(target) and os.path.getsize(target) > 500 << 20:
        return False  # a full library is already here (with the user's own seforim) - the app updates it safely
    log("Installing the complete seforim library (a few minutes)…")
    tmp = target + ".installing"
    INST.decompress(parts, tmp, progress)
    os.replace(tmp, target)
    INST.mark_installed(data_dir, parts)
    log("Seforim library installed ✓")
    return True


def run_all(dest, shortcuts=True, fonts=True, log=print, progress=lambda f: None, all_users=False, ai=True):
    shared = SHARED if all_users else None
    exe = install(dest, log, progress, shared)
    try:
        install_library(shared or os.path.join(dest, "data"), log, progress)
    except Exception as e:  # noqa
        log(f"(The library will be installed when the app starts: {e})")
    if ai:
        try:
            install_ai(shared or os.path.join(dest, "data"), log, progress)
        except Exception as e:  # noqa
            log(f"(Could not install the AI reader now: {e} - the app will try again when it starts)")
    if copy_packs(shared or dest, log):
        log("Library / AI files copied - they install automatically when the app starts")
    if shortcuts:
        try:
            make_shortcuts(exe, all_users)
            log("Shortcuts added to the Desktop and Start menu")
        except Exception as e:  # noqa
            log(f"(Could not add shortcuts: {e})")
    if fonts:
        try:
            log(f"{install_fonts(dest, all_users, os.path.join(shared, 'fonts') if shared else None)} Hebrew font files installed for Word and other programs"
                + (" (for all users)" if all_users else ""))
        except Exception as e:  # noqa
            log(f"(Could not install fonts into Windows: {e})")
    return exe


ALL_USERS_START = False
AUTOSTART = False
DIR_START = None


def gui():
    import tkinter as tk
    from tkinter import filedialog, ttk
    root = tk.Tk()
    root.title(f"{APP} — Setup")
    root.geometry("680x440")
    root.resizable(False, False)
    try:
        root.iconbitmap(os.path.join(getattr(sys, "_MEIPASS", "."), "icon.ico"))
    except Exception:
        pass
    pad = {"padx": 16, "pady": 6}
    tk.Label(root, text=APP, font=("Segoe UI", 20, "bold"), fg="#1e3a5f").pack(anchor="w", **pad)
    tk.Label(root, text="Hebrew seforim library, search, gematria, notes, covers and handwriting scanner — works offline.",
             font=("Segoe UI", 10), fg="#555").pack(anchor="w", padx=16)
    row = tk.Frame(root); row.pack(fill="x", **pad)
    tk.Label(row, text="Install to:", font=("Segoe UI", 10)).pack(side="left")
    path = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "SeforimStudio"))
    tk.Entry(row, textvariable=path, font=("Segoe UI", 10), width=52).pack(side="left", padx=6)
    tk.Button(row, text="Browse…", command=lambda: path.set(os.path.join(filedialog.askdirectory() or os.path.dirname(path.get()), "SeforimStudio"))).pack(side="left")
    v_sc, v_fo, v_go = tk.BooleanVar(value=True), tk.BooleanVar(value=True), tk.BooleanVar(value=True)
    v_all = tk.BooleanVar(value=ALL_USERS_START)
    def all_changed():
        path.set(PROGRAM_FILES if v_all.get() else os.path.join(os.path.expanduser("~"), "SeforimStudio"))
    tk.Checkbutton(root, text="Install for ALL users of this computer (library + AI installed once for everyone; asks for administrator)",
                   variable=v_all, command=all_changed, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16)
    if ALL_USERS_START:
        path.set(DIR_START or PROGRAM_FILES)
    tk.Checkbutton(root, text="Add shortcuts to the Desktop and Start menu", variable=v_sc, font=("Segoe UI", 10)).pack(anchor="w", padx=16)
    tk.Checkbutton(root, text="Install the Hebrew fonts into Windows (so Word can use them)", variable=v_fo, font=("Segoe UI", 10)).pack(anchor="w", padx=16)
    tk.Checkbutton(root, text="Start Seforim Studio when finished", variable=v_go, font=("Segoe UI", 10)).pack(anchor="w", padx=16)
    bar = ttk.Progressbar(root, length=580, mode="determinate"); bar.pack(**pad)
    status = tk.Label(root, text="", font=("Segoe UI", 9), fg="#333", justify="left", wraplength=580); status.pack(anchor="w", padx=16)
    btn = tk.Button(root, text="Install", font=("Segoe UI", 11, "bold"), bg="#b8892b", fg="white", width=14)
    btn.pack(pady=8)
    lines = []

    def log(t):
        lines.append(t)
        root.after(0, lambda: status.config(text="\n".join(lines[-4:])))

    def go():
        if v_all.get() and not is_admin():
            args = ["--allusers", "--autostart", "--dir", path.get().strip()] + ([] if v_sc.get() else ["--no-shortcuts"]) + \
                   ([] if v_fo.get() else ["--no-fonts"]) + ([] if v_go.get() else ["--no-launch"])
            if relaunch_as_admin(args):
                root.destroy()
            else:
                log("Administrator permission was not given - untick 'all users' to install just for you.")
            return
        btn.config(state="disabled", text="Installing…")
        dest = path.get().strip()

        def work():
            try:
                exe = run_all(dest, v_sc.get(), v_fo.get(), log, lambda f: root.after(0, lambda: bar.config(value=f * 100)), v_all.get())
                lib = library_parts_hint()
                log("When the library and AI have installed, use Settings -> Backup -> 'Make the complete zip' to get ONE zip for any offline computer.")
                log("Library download found — it will be installed when the app starts." if lib else
                    "Tip: download the two SeforimLibrary…part files and put them in the install folder (or leave them in Downloads).")
                if v_go.get():
                    subprocess.Popen([exe], cwd=os.path.dirname(exe))
                root.after(0, lambda: btn.config(state="normal", text="Close", command=root.destroy))
            except Exception as e:  # noqa
                log(f"Problem: {e}")
                root.after(0, lambda: btn.config(state="normal", text="Try again"))
        threading.Thread(target=work, daemon=True).start()
    btn.config(command=go)
    if AUTOSTART:
        root.after(400, go)
    root.mainloop()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--silent", action="store_true")
    ap.add_argument("--dir")
    ap.add_argument("--no-launch", action="store_true")
    ap.add_argument("--no-shortcuts", action="store_true")
    ap.add_argument("--no-fonts", action="store_true")
    ap.add_argument("--allusers", action="store_true")
    ap.add_argument("--autostart", action="store_true")
    a = ap.parse_args()
    if a.silent:
        dest = a.dir or (PROGRAM_FILES if a.allusers else os.path.join(os.path.expanduser("~"), "SeforimStudio"))
        exe = run_all(dest, not a.no_shortcuts, not a.no_fonts, all_users=a.allusers)
        if not a.no_launch:
            subprocess.Popen([exe], cwd=os.path.dirname(exe))
        return
    global ALL_USERS_START, AUTOSTART, DIR_START
    ALL_USERS_START, AUTOSTART, DIR_START = a.allusers, a.autostart and is_admin(), a.dir
    gui()


if __name__ == "__main__":
    main()
