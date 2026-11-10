"""Find errors everywhere: run every tool with several inputs, call every read-only API, and crawl every screen,
clicking buttons and filling inputs. Reports console errors, page crashes, failed requests and server tracebacks.

    python tests/sweep.py <results-folder> [--port 8890]
"""
import json, os, re
sys_ = __import__("sys"); sys_.stdout.reconfigure(encoding="utf-8", errors="replace")
import json, os, re, subprocess, sys, tempfile, time, urllib.request, traceback
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
OUT = os.path.abspath(sys.argv[1]); os.makedirs(OUT, exist_ok=True)
PORT = 8890
data = os.environ.get("SWEEP_DATA") or tempfile.mkdtemp(prefix="sweep_data_")
EXE = os.environ.get("SWEEP_EXE")
log = open(os.path.join(OUT, "server_log.txt"), "w")
proc = subprocess.Popen(([EXE] if EXE else [sys.executable, os.path.join(ROOT, "SeforimStudio.py")]) + ["--no-window", "--port", str(PORT), "--data", data],
                        stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
TOKEN = None
for _ in range(60):
    try:
        TOKEN = re.search(r'TOKEN = "([^"]+)"', urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=2).read().decode()).group(1); break
    except Exception:
        time.sleep(0.5)
problems = []
def bad(kind, what, detail):
    problems.append((kind, what, str(detail)[:600])); print("!!", kind, what, str(detail)[:200], flush=True)

def api(name, **a):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/api/{name}", data=json.dumps(a).encode(), headers={"X-Token": TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:400]}")

def wait_job(j):
    for _ in range(600):
        r = api("job", id=j)
        if r.get("done"): return r
        time.sleep(0.3)

api("setting", key="ask_save", value="0")  # no "Save as" boxes during the robot test
BIG = bool(os.environ.get("SWEEP_DATA"))
if not BIG:  # small sample library
    sample = tempfile.mkdtemp(prefix="sweep_sefaria_")
    subprocess.run([sys.executable, os.path.join(HERE, "make_sample_data.py"), sample], check=True, stdout=subprocess.DEVNULL)
    r = wait_job(api("import_folder", path=os.path.join(sample, "sefaria"))["job"])
print("library:", api("status")["library"], flush=True)
timings = []

def timed(name, **a):
    t0 = time.time()
    try:
        r = api(name, **a)
        if isinstance(r, dict) and r.get("job"):
            r = wait_job(r["job"])
            if r and r.get("error"):
                bad("api", name, (a, r["error"]))
    except Exception as e:
        bad("api", name, (a, e)); r = None
    dt_ = time.time() - t0
    timings.append((round(dt_, 2), name, json.dumps(a, ensure_ascii=False)[:120]))
    if dt_ > 8:
        bad("slow", name, f"{dt_:.1f}s {a}")
    return r

# ---------------- the heavy features with typical input
for nm, a in [("status", {}), ("catalog_tree", {}), ("lib_works", {}), ("library_health", {}), ("dashboard", {}),
              ("find_ref", {"ref": "Genesis 1:1"}), ("find_ref", {"ref": "Berakhot 2a"}), ("find_ref", {"ref": "בראשית א:א"}),
              ("search", {"q": "שלום", "lang": "he"}), ("search", {"q": "peace", "lang": "en"}), ("search", {"q": "אור", "lang": "he", "sort": "book"}),
              ("search", {"q": "\"קריאת שמע\"", "lang": "he"}), ("search", {"q": "אהב*", "lang": "he"}), ("search", {"q": "light AND darkness", "lang": "en"}),
              ("cross_lingual", {"q": "שלום"}), ("cross_lingual", {"q": "peace"}),
              ("gematria_value", {"text": "שלום"}), ("gematria_words", {"value": 376}), ("gematria_phrases", {"value": 376}),
              ("gematria_passages", {"value": 376}), ("roshei", {"letters": "אבג"}), ("roshei", {"letters": "שמע", "mode": "sofei"}),
              ("word_cloud", {"q": "שבת"}), ("histogram", {"q": "שבת"}), ("cooccurrence", {"q": "שבת", "a": "שבת", "b": "שמירה"}),
              ("search_compare", {"q": "שבת"}), ("timeline", {}), ("abbrevs", {}), ("he_coverage", {}), ("reading_log", {}),
              ("search_history", {}), ("tools", {}), ("plugins", {}), ("home_cards", {}),
              ("plugin_call", {"id": "daily_learning", "fn": "today"}), ("plugin_call", {"id": "daily_learning", "fn": "plans"}),
              ("plugin_call", {"id": "chazara", "fn": "add", "args": {"ref": "Genesis 1:1", "whole_chapter": True}}),
              ("plugin_call", {"id": "chazara", "fn": "add", "args": {"question": "Q?", "answer": "A"}}),
              ("plugin_call", {"id": "chazara", "fn": "due"}), ("plugin_call", {"id": "chazara", "fn": "decks"}),
              ("plugin_call", {"id": "word_study", "fn": "study", "args": {"word": "אור"}}),
              ("plugin_call", {"id": "tehillim", "fn": "for_name", "args": {"name": "משה", "mother": "שרה", "neshama": True, "age": "40"}}),
              ("plugin_call", {"id": "tehillim", "fn": "texts", "args": {"refs": ["Psalms 119:1-8", "Psalms 20"]}}),
              ("plugin_call", {"id": "tehillim", "fn": "occasions"}),
              ("translate", {"q": "שלום"}), ("translate", {"q": "peace"}), ("translate", {"q": "בראשית ברא אלהים"}),
              ("interlinear", {"refs": ["Genesis 1:1"], "texts": ["בראשית ברא"]}), ("locations", {}),
              ("plugin_call", {"id": "mitzvos", "fn": "list"}), ("plugin_call", {"id": "mitzvos", "fn": "detail", "args": {"kind": "rabbanan", "n": 1}})]:
    timed(nm, **a)
g = timed("find_ref", ref="Genesis 1:1")
if g and g.get("work_id"):
    timed("lib_toc", work_id=g["work_id"]); timed("lib_chapter", work_id=g["work_id"], node=g.get("node", ""), chapter=g.get("chapter", ""))
    timed("connections", ref="Genesis 1:1"); timed("passage", id=g["id"], ref="Genesis 1:1")
    timed("work_stats", work_id=g["work_id"], q="אור", a="אור", b="חשך")
    timed("els", work_id=g["work_id"], word="תורה", id=g["id"], min=2, max=60)
b_ = timed("find_ref", ref="Berakhot 2a")
if b_ and b_.get("work_id"):
    timed("lib_toc", work_id=b_["work_id"]); timed("lib_chapter", work_id=b_["work_id"], node=b_.get("node", ""), chapter=b_.get("chapter", ""))
    timed("connections", ref=b_["ref"])

# ---------------- every tool, several inputs
SAMPLES = {"text": ["שלום עולם", "בְּרֵאשִׁית בָּרָא אֱלֹהִים", "", "abc 123", "תשפ\"ז", "a"*3],
           "number": ["376", "0", "-5", "abc", ""], "date": ["2026-11-07", "", "1900-01-01", "bad"],
           "select": None}
tools = api("tools")
print(len(tools), "tools")
for t in tools:
    variants = []
    for i in range(4):
        args = {}
        for inp in t.get("inputs", []):
            typ = inp.get("type", "text"); nm = inp["name"]
            if inp.get("options"):
                opts = inp["options"]; o = opts[i % len(opts)]
                args[nm] = o["value"] if isinstance(o, dict) else o
            elif typ in ("number", "int"):
                args[nm] = SAMPLES["number"][i % 5]
            elif typ == "date":
                args[nm] = SAMPLES["date"][i % 4]
            elif typ in ("check", "checkbox", "bool"):
                args[nm] = bool(i % 2)
            else:
                args[nm] = (inp.get("default") if i == 0 and inp.get("default") else SAMPLES["text"][i % 6])
        variants.append(args)
    for args in variants:
        try:
            res = api("tool_run", id=t["id"], args=args)
            if isinstance(res, dict) and res.get("error") and "Traceback" in str(res.get("error")):
                bad("tool", t["id"], (args, res["error"]))
        except Exception as e:
            if "HTTP 400" not in str(e):  # 400 = a friendly "please type a number" message - fine
                bad("tool", t["id"], (args, e))

# ---------------- browser crawl
from playwright.sync_api import sync_playwright
SKIP = re.compile(r"delete|remove|reset|clear all|stop|quit|exit|wipe|erase|uninstall|install fonts into windows|make the complete zip|"
                  r"bluetooth|load a different|print|open folder|log ?out|forget|restore|download|install|close app|install library|"
                  r"⬇|📥|🗑|×|✕|choose|📂|🖨", re.I)
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge") if os.name == "nt" else p.chromium.launch(); pg = b.new_page(viewport={"width": 1400, "height": 900})
    pg.set_default_timeout(60000)
    pg.add_init_script("""(() => { const f = window.fetch; window.fetch = async (...a) => { const t = performance.now(); const r = await f(...a);
      const d = performance.now() - t; if (d > 8000) console.error('SLOW ' + Math.round(d) + 'ms ' + String(a[0])); return r; }; })()""")
    cur = {"where": "start"}
    pg.on("console", lambda m: m.type == "error" and bad("console", cur["where"], m.text))
    pg.on("pageerror", lambda e: bad("pageerror", cur["where"], e))
    pg.on("response", lambda r: r.status >= 400 and "/favicon" not in r.url and bad("http", cur["where"], f"{r.status} {r.url} {(lambda: r.text()[:300])() if r.status>=500 else ''}"))
    pg.on("dialog", lambda d: d.dismiss())
    pg.goto(f"http://127.0.0.1:{PORT}/"); pg.wait_for_timeout(2500)
    pages = pg.evaluate("Object.keys(App.pages)")
    print("pages:", pages)
    for name in pages:
        cur["where"] = name
        try:
            pg.evaluate(f"App.closeModal && App.closeModal(); App.show({json.dumps(name)})"); pg.wait_for_timeout(1500)
        except Exception as e:
            bad("show", name, e); continue
        pg.screenshot(path=os.path.join(OUT, f"{name}.png"))
        # fill inputs
        try:
            for el in pg.query_selector_all("#main input[type=text]:visible, #main input:not([type]):visible, #main textarea:visible")[:25]:
                try: el.fill("שלום"); el.press("Enter"); pg.wait_for_timeout(150)
                except Exception: pass
        except Exception as e:
            bad("fill", name, e)
        # selects: try each option once
        for i, sel in enumerate(pg.query_selector_all("#main select:visible")[:15]):
            try:
                vals = sel.evaluate("s => [...s.options].map(o => o.value)")
                for v in vals[:6]:
                    cur["where"] = f"{name} select#{sel.get_attribute('id')}={v}"
                    sel.select_option(v); pg.wait_for_timeout(250)
            except Exception: pass
        cur["where"] = name
        # buttons
        n = pg.evaluate("document.querySelectorAll('#main button').length")
        for i in range(min(n, 80)):
            try:
                pg.evaluate(f"App.closeModal && App.closeModal()")
                if pg.evaluate(f"App.current") != name:
                    pg.evaluate(f"App.show({json.dumps(name)})"); pg.wait_for_timeout(800)
                btns = pg.query_selector_all("#main button")
                if i >= len(btns): break
                btn = btns[i]
                if not btn.is_visible() or not btn.is_enabled(): continue
                label = (btn.inner_text() or btn.get_attribute("title") or btn.get_attribute("id") or "").strip()[:50]
                if SKIP.search(label) or SKIP.search(btn.get_attribute("id") or ""): continue
                cur["where"] = f"{name} › [{label}]"
                btn.click(timeout=2000); pg.wait_for_timeout(700)
                # click first button inside a modal (OK) then close
                if pg.is_visible("#modalWrap"):
                    pg.wait_for_timeout(300)
            except Exception as e:
                if "Timeout" not in str(e): bad("click", cur["where"], e)
        cur["where"] = name
    b.close()
proc.terminate(); time.sleep(1); log.close()
tb = open(os.path.join(OUT, "server_log.txt"), encoding="utf-8", errors="replace").read()
if os.path.exists(os.path.join(data, "app_log.txt")):  # the windowed exe writes its log there
    tb += open(os.path.join(data, "app_log.txt"), encoding="utf-8", errors="replace").read()
for m in re.finditer(r"Traceback \(most recent call last\):.*?\n(?=\S)(.*?)\n", tb, re.S):
    bad("server", "traceback", m.group(0)[-500:])
timings.sort(reverse=True)
with open(os.path.join(OUT, "timings.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(f"{t:7.2f}s  {n}  {a}" for t, n, a in timings))
md = ["# Error sweep", "", f"**{len(problems)} problems**", ""] + [f"- **{k}** `{w}` — {d[:400]}" for k, w, d in problems]
md += ["", "## Slowest calls", "```"] + [f"{t:7.2f}s  {n}  {a}" for t, n, a in timings[:40]] + ["```"]
open(os.path.join(OUT, "report.md"), "w", encoding="utf-8").write("\n".join(md))
with open(os.path.join(OUT, "sweep_report.json"), "w", encoding="utf-8") as f:
    json.dump(problems, f, ensure_ascii=False, indent=1)
print(f"\n{len(problems)} problems")
