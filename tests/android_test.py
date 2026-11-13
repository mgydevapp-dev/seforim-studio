"""Check the Android app on an emulator: it starts, every screen opens without errors, and nothing is wider than the
phone screen. Connects to the app's WebView through Chrome DevTools (adb forward) with Playwright.
Usage: python tests/android_test.py OUTDIR"""
import json
import os
import re
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

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
with sync_playwright() as p:
    dev = p._android.devices()[0]
    page = None
    t0 = time.time()
    while time.time() - t0 < 240 and not page:
        try:
            wv = dev.web_view({"pkg": PKG}, timeout=20000)
            pg = wv.page()
            if pg.url.startswith("http://127.0.0.1"):
                page = pg
            else:
                time.sleep(3)
        except Exception as e:  # noqa
            print("waiting for the WebView:", e)
            time.sleep(3)
    if not page:
        try:
            print("page text:", pg.inner_text("body")[:3000])
        except Exception:
            pass
    note(page is not None, f"the app's pages loaded ({time.time() - t0:.0f} s after start)")
    errors = []
    if page:
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.wait_for_function("window.App && document.querySelector('#rail button')", timeout=120000)
        page.evaluate("App.closeModal && App.closeModal()")
        ids = page.evaluate("App.order")
        st = page.evaluate("fetch('/api/android_storage',{method:'POST',headers:{'X-Token':TOKEN},body:'{}'}).then(r=>r.json())")
        note("storages" in st, "phone storage places: " + json.dumps(st)[:600])
        for pid_ in ids:
            n0 = len(errors)
            try:
                page.evaluate(f"App.show({json.dumps(pid_)})")
                page.wait_for_timeout(2500)
                wide = page.evaluate("""(id)=>{const W=innerWidth, out=[];
                  document.querySelectorAll('#page-'+id+' *').forEach(e=>{const r=e.getBoundingClientRect();
                    if(r.width>0&&r.right>W+4&&getComputedStyle(e).position!=='fixed'&&!e.closest('.reader-toolbar,.tabs,table,.vilna,.ed-toolbar')) out.push(e.tagName+'.'+e.className+' '+Math.round(r.right))});
                  return out.slice(0,5)}""", pid_)
                page.screenshot(path=os.path.join(OUT, f"screen_{pid_}.png"))
                note(len(errors) == n0, f"screen {pid_} opens" + (": " + "; ".join(errors[n0:])[:300] if len(errors) > n0 else ""))
                if wide:
                    report.append(f"   ⚠ wider than the phone on {pid_}: {wide}")
            except Exception as e:  # noqa
                note(False, f"screen {pid_}: {e}")
        # tools that use the engine
        for name, args in [("status", {}), ("gematria", {"text": "שלום"}), ("ai_status", {}), ("library_health", {})]:
            r2 = page.evaluate(f"fetch('/api/{name}',{{method:'POST',headers:{{'X-Token':TOKEN}},body:JSON.stringify({json.dumps(args)})}}).then(r=>r.text())")
            note(not r2.startswith('{"error"'), f"api {name}: {r2[:250]}")
        page.evaluate("App.show('home')")
        page.wait_for_timeout(1500)
        page.screenshot(path=os.path.join(OUT, "home.png"))
    dev.close()

log = adb("logcat", "-d", "-s", "python.stdout:*", "python.stderr:*", "SeforimStudio:*", "AndroidRuntime:E")
open(os.path.join(OUT, "logcat.txt"), "w").write(log)
open(os.path.join(OUT, "report.md"), "w").write("\n".join(report) + f"\n\n{len(failed)} problem(s)\n")
print(f"{len(failed)} problem(s)")
sys.exit(1 if failed else 0)
