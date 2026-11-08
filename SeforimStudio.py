"""Seforim Studio — offline Hebrew seforim library, search, gematria, notes, covers and scanner.

Double-click (or run:  python SeforimStudio.py ).  It starts a private local engine (127.0.0.1 only) and opens
the app in its own window using Microsoft Edge / Google Chrome "app mode" (no address bar, no internet used).
Options:  --port 8765   --data D:\\SeforimData   --no-window (just print the address)
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
import webbrowser

BASE = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
HOME = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
sys.path.insert(0, BASE)

try:
    from core.server import App, serve  # noqa: E402
except ModuleNotFoundError as _e:  # running from source without the add-ons installed
    _msg = (f"Seforim Studio is missing a part: {_e.name}\n\nRun install_windows.bat once (needs internet), "
            "or use the portable SeforimStudio.exe which has everything inside.")
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, _msg, "Seforim Studio", 0x10)
    except Exception:
        print(_msg)
    sys.exit(1)


def find_browser():
    cands = []
    if os.name == "nt":
        for env in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
            root = os.environ.get(env)
            if root:
                cands += [os.path.join(root, "Microsoft", "Edge", "Application", "msedge.exe"),
                          os.path.join(root, "Google", "Chrome", "Application", "chrome.exe"),
                          os.path.join(root, "BraveSoftware", "Brave-Browser", "Application", "brave.exe")]
    elif sys.platform == "darwin":
        cands += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                  "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"]
    for name in ("msedge", "google-chrome", "chromium", "chromium-browser", "microsoft-edge", "chrome"):
        p = shutil.which(name)
        if p:
            cands.append(p)
    return next((c for c in cands if c and os.path.exists(c)), None)


def install_mode():
    """install.json next to the exe (written by Setup) = installed for ALL users: the library, AI models and fonts are
    in one shared folder (installed once), and every Windows user keeps their own notes and settings."""
    f = os.path.join(HOME, "install.json")
    try:
        import json
        return json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
    except Exception:
        return {}


def main():
    mode = install_mode()
    shared = mode.get("shared") if mode.get("mode") == "allusers" else None
    default_data = (os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "SeforimStudio")
                    if shared else os.path.join(HOME, "data"))
    # The .exe has no console window: send messages to a log file instead.
    if sys.stdout is None or sys.stderr is None:
        os.makedirs(default_data, exist_ok=True)
        log = open(os.path.join(default_data, "app_log.txt"), "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--data", default=default_data)
    ap.add_argument("--shared", default=shared, help="folder with the library / AI models shared by all users")
    ap.add_argument("--no-window", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.data, exist_ok=True)
    # first run: ship the catalog next to the app
    bundled = os.path.join(BASE, "data", "seforim_catalog.db")
    target = os.path.join(a.shared or a.data, "seforim_catalog.db")
    if os.path.exists(bundled) and not os.path.exists(target):
        try:
            shutil.copy2(bundled, target)
        except OSError:
            pass
    app = App(BASE, a.data, a.shared)
    srv = serve(app, a.port)
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print("Seforim Studio is running at", url)
    print("Data folder:", a.data)
    if a.no_window:
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return
    browser = find_browser()
    if browser:
        prof = os.path.join(a.data, "window_profile")
        proc = subprocess.Popen(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, args=[browser, f"--app={url}", f"--user-data-dir={prof}", "--window-size=1440,920",
                                 "--no-first-run", "--no-default-browser-check", "--disable-features=Translate",
                                 "--lang=en-US"])
        proc.wait()  # app window closed → quit
        # some browsers hand off to an existing process; keep running while the page still pings us
        while time.time() - app.last_ping < 20:
            time.sleep(5)
        if app.ollama_proc:
            app.ollama_proc.terminate()  # stop the bundled AI reader together with the app
    else:
        webbrowser.open(url)
        print("Opened in your default browser. Close this window to quit.")
        while True:
            time.sleep(10)
            if time.time() - app.last_ping > 120:
                break


if __name__ == "__main__":
    main()
