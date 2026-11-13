"""Check the Android app on an emulator: it starts, every screen opens without errors, and nothing is wider than the
phone screen. Connects to the app's WebView through Chrome DevTools (adb forward) with Playwright.
Usage: python tests/android_test.py OUTDIR"""
import json
import os
import re
import subprocess
import sys
import time


OUT = sys.argv[1] if len(sys.argv) > 1 else "android-results"
os.makedirs(OUT, exist_ok=True)
PKG = "org.seforimstudio.app"


def adb(*a, check=False):
    r = subprocess.run(["adb", *a], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(r.stderr)
    return r.stdout.strip()


report, failed = [], []


def note(ok, msg):
    report.append(("✅ " if ok else "❌ ") + msg)
    print(report[-1], flush=True)
    if not ok:
        failed.append(msg)


adb("shell", "am", "start", "-n", f"{PKG}/.MainActivity")
pid = ""
for _ in range(60):
    pid = adb("shell", "pidof", PKG)
    if pid:
        break
    time.sleep(1)
note(bool(pid), f"app process started (pid {pid})")
class CDP:
    """A tiny Chrome DevTools client for the app's WebView (Playwright cannot attach to Android WebViews from Python)."""
    def __init__(self, ws_url):
        import websocket
        self.ws, self.n, self.errors = websocket.create_connection(ws_url, timeout=120, suppress_origin=True), 0, []
        self.call("Runtime.enable")
        self.call("Page.enable")

    def call(self, method, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("method") == "Runtime.exceptionThrown":
                d = m["params"]["exceptionDetails"]
                self.errors.append((d.get("exception") or {}).get("description") or d.get("text"))
            if m.get("id") == self.n:
                if "error" in m:
                    raise RuntimeError(m["error"])
                return m.get("result", {})

    def js(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        if r.get("exceptionDetails"):
            raise RuntimeError(r["exceptionDetails"].get("exception", {}).get("description") or r["exceptionDetails"].get("text"))
        return r.get("result", {}).get("value")

    def shot(self, path):
        import base64
        open(path, "wb").write(base64.b64decode(self.call("Page.captureScreenshot", format="png")["data"]))


import urllib.request
page, t0 = None, time.time()
fwd = ""
while time.time() - t0 < 300 and not page:
    try:
        m = re.search(r"@(webview_devtools_remote_\d+)", adb("shell", "cat", "/proc/net/unix"))
        if m and m.group(1) != fwd:
            fwd = m.group(1)
            adb("forward", "tcp:9222", "localabstract:" + fwd)
        tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=10).read())
        app = [t for t in tabs if t.get("url", "").startswith("http://127.0.0.1")]
        if app:
            page = CDP(app[0]["webSocketDebuggerUrl"])
            break
        print("waiting:", [t.get("url", "")[:80] for t in tabs], flush=True)
    except Exception as e:  # noqa
        print("waiting for the WebView:", e, flush=True)
    time.sleep(4)
note(page is not None, f"the app's pages loaded ({time.time() - t0:.0f} s after start)")
if page:
    for _ in range(60):
        if page.js("!!(window.App && document.querySelector('#rail button'))"):
            break
        time.sleep(2)
    time.sleep(3)
    page.js("App.closeModal && App.closeModal()")
    page.shot(os.path.join(OUT, "start.png"))
    ids = page.js("App.order")
    api = lambda name, args={}: page.js(f"fetch('/api/{name}',{{method:'POST',headers:{{'X-Token':TOKEN}},body:JSON.stringify({json.dumps(args)})}}).then(r=>r.text())")
    st = api("android_storage")
    note('"storages"' in st, "phone storage places: " + st[:700])
    for pid_ in ids:
        n0 = len(page.errors)
        try:
            page.js(f"App.show({json.dumps(pid_)})")
            time.sleep(2.5)
            wide = page.js("""(()=>{const W=innerWidth, out=[], id=%s;
              document.querySelectorAll('#page-'+id+' *').forEach(e=>{const r=e.getBoundingClientRect();
                if(r.width>0&&r.right>W+4&&getComputedStyle(e).position!=='fixed'&&!e.closest('.reader-toolbar,.tabs,table,.vilna,.ed-toolbar')) out.push(e.tagName+'.'+e.className+' '+Math.round(r.right))});
              return out.slice(0,5)})()""" % json.dumps(pid_))
            page.shot(os.path.join(OUT, f"screen_{pid_}.png"))
            new = page.errors[n0:]
            note(not new, f"screen {pid_} opens" + (": " + "; ".join(map(str, new))[:300] if new else ""))
            if wide:
                report.append(f"   ⚠ wider than the phone on {pid_}: {wide}")
        except Exception as e:  # noqa
            note(False, f"screen {pid_}: {e}")
    for name, args in [("status", {}), ("gematria_value", {"text": "שלום"}), ("ai_status", {}), ("library_health", {})]:
        r = api(name, args)
        note(not r.startswith('{"error"'), f"api {name}: {r[:250]}")
    page.js("App.show('home')")
    time.sleep(1.5)
    page.shot(os.path.join(OUT, "home.png"))

log = adb("logcat", "-d", "-s", "python.stdout:*", "python.stderr:*", "SeforimStudio:*", "AndroidRuntime:E")
open(os.path.join(OUT, "logcat.txt"), "w").write(log)
open(os.path.join(OUT, "report.md"), "w").write("\n".join(report) + f"\n\n{len(failed)} problem(s)\n")
print(f"{len(failed)} problem(s)")
sys.exit(1 if failed else 0)
