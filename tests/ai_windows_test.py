"""Install Seforim Studio + the AI pack exactly like a user, then read the handwriting sample with the AI (engine A).

    python tests/ai_windows_test.py <SeforimStudio-Setup.exe> <folder-with-SeforimAI-parts> <results-folder>
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SETUP, PARTS, OUT = (os.path.abspath(x) for x in sys.argv[1:4])
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)
PORT = 8810
report = []


def say(t):
    print(t, flush=True)
    report.append(t)


inst = os.path.join(os.environ.get("RUNNER_TEMP", os.path.expanduser("~")), "SeforimAI_Test")
subprocess.run([SETUP, "--silent", "--dir", inst, "--no-launch", "--no-shortcuts", "--no-fonts"], check=True)
say(f"Installed app with Setup into {inst}")
exe = os.path.join(inst, "SeforimStudio.exe")
# the app looks for the AI pack in its own folder and in Downloads - put the parts in Downloads like a user
dl = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(dl, exist_ok=True)
for f in os.listdir(PARTS):
    if f.startswith("SeforimAI.tar"):
        import shutil
        shutil.move(os.path.join(PARTS, f), os.path.join(dl, f))  # works across drives (C: / D:)
say("AI pack parts in Downloads: " + ", ".join(sorted(f for f in os.listdir(dl) if f.startswith("SeforimAI"))))

DEBUG = os.path.join(OUT, "ai_debug.txt")
proc = subprocess.Popen([exe, "--no-window", "--port", str(PORT)], cwd=inst, env={**os.environ, "SEFORIM_AI_DEBUG": DEBUG})
tok = None
for _ in range(90):
    try:
        tok = re.search(r'TOKEN = "([^"]+)"', urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=2).read().decode()).group(1)
        break
    except Exception:
        time.sleep(1)


def api(name, timeout=120, **a):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/api/{name}", data=json.dumps(a).encode(), headers={"X-Token": tok})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


t0 = time.time()
while True:
    st = api("ai_status")
    if st["state"] not in ("running",):
        break
    time.sleep(3)
say(f"AI pack install: {st['state']} - {st['message']} ({int(time.time() - t0)} s)")
for _ in range(60):
    eng = {e["key"]: e for e in api("scan_engines")}
    if eng["ollama"]["ok"]:
        break
    time.sleep(2)
say(f"Engine A ready: {eng['ollama']['ok']} - {eng['ollama']['info']}")

ok_all = eng["ollama"]["ok"]
if ok_all:
    def score(pred, truth):
        import re as _re
        def lev(a, b):
            prev = list(range(len(b) + 1))
            for i, x in enumerate(a, 1):
                cur = [i]
                for j, y in enumerate(b, 1):
                    cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
                prev = cur
            return prev[-1]
        norm = lambda t: _re.sub(r"\s+", " ", _re.sub(r"[^\u05d0-\u05ea ]", " ", t or "")).strip()
        p, t = norm(pred), norm(truth)
        return lev(p, t) / max(1, len(t)), 1 - lev(p.split(), t.split()) / max(1, len(t.split()))
    for sample in ("handwriting_sample.jpg", "cursive_alphabet.png", "messy_handwriting.png"):
        up = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/upload",
                       data=open(os.path.join(HERE, "data", sample), "rb").read(), headers={"X-Token": tok, "X-Filename": sample})).read())
        job = api("scan_start", uploads=[up["upload"]], opts={})["job"]
        while not (r := api("job", id=job))["done"]:
            time.sleep(1)
        t1 = time.time()
        o = api("scan_ocr", engine="ollama", pages=r["result"]["pages"])
        while not (r2 := api("job", id=o["job"]))["done"]:
            time.sleep(3)
        text = r2["result"]["pages"][0] if r2.get("result") else str(r2.get("error"))
        say(f"(job: {json.dumps({k: v for k, v in r2.items() if k != 'result'}, ensure_ascii=False)[:500]})")
        secs = int(time.time() - t1)
        tf = os.path.join(HERE, "data", os.path.splitext(sample)[0] + ".txt")
        if not os.path.exists(tf):  # no answer key: just show what it read
            say(f"\nAI read {sample} in {secs} s:\n{text}")
            continue
        truth = open(tf, encoding="utf-8").read()
        cer, wacc = score(text, truth)
        say(f"\nAI read {sample} in {secs} s (CPU only, no graphics card):\n{text}\n\nCharacters wrong: {cer:.1%}  Words correct: {wacc:.1%}")
        if sample == "handwriting_sample.jpg":
            ok_all = ok_all and cer < 0.35
proc.terminate()
if os.path.exists(DEBUG):
    report.append("\n== raw AI answers ==\n" + open(DEBUG, encoding="utf-8", errors="replace").read()[-6000:])
for lf in (os.path.join(inst, "data", "app_log.txt"),):
    if os.path.exists(lf):
        report.append("\n== app log (end) ==\n" + open(lf, encoding="utf-8", errors="replace").read()[-4000:])
with open(os.path.join(OUT, "ai_report.md"), "w", encoding="utf-8") as f:
    f.write("# AI handwriting reader test (Windows)\n\n```\n" + "\n".join(report) + "\n```\n")
sys.exit(0 if ok_all else 1)
