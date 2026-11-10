"""Click through the REAL built SeforimStudio.exe the way a person would (runs on the Windows build server).

    python tests/windows_ui_test.py <path-to-SeforimStudio.exe> <results-folder>

Uses Playwright driving Microsoft Edge. Records every screen as a screenshot, every browser console error,
every failed request, the app's own log, and a pass/fail list -> results-folder/report.md
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
EXE, OUT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8799
os.makedirs(OUT, exist_ok=True)
results, console, failed_requests = [], [], []


def check(name, ok, detail=""):
    results.append((name, bool(ok), str(detail)[:400]))
    print(("PASS " if ok else "FAIL ") + name + (" — " + str(detail)[:200] if detail else ""), flush=True)


def api(name, **a):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/api/{name}", data=json.dumps(a).encode("utf-8"),
                                 headers={"X-Token": TOKEN, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


# ------------------------------------------------------------------ start the exe
cmd = ([sys.executable, EXE] if EXE.endswith(".py") else [EXE]) + ["--no-window", "--port", str(PORT)]
if os.environ.get("TEST_DATA"):
    cmd += ["--data", os.environ["TEST_DATA"]]
proc = subprocess.Popen(cmd, cwd=os.path.dirname(EXE))
TOKEN = None
for _ in range(60):
    try:
        html = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=2).read().decode()
        TOKEN = re.search(r'TOKEN = "([^"]+)"', html).group(1)
        break
    except Exception:
        time.sleep(1)
check("exe starts and answers", TOKEN)
if not TOKEN:
    sys.exit(1)
api("setting", key="ask_save", value="0")  # the robot cannot answer "Save as" boxes: save to Downloads

# ------------------------------------------------------------------ library: import sample folder + REAL downloads
try:
    sample = tempfile.mkdtemp(prefix="sefaria_export_")
    subprocess.run([sys.executable, os.path.join(HERE, "make_sample_data.py"), sample], check=True)
    job = api("import_folder", path=os.path.join(sample, "sefaria"))["job"]
    for _ in range(60):
        st = api("job", id=job)
        if st["done"]:
            break
        time.sleep(1)
    check("import a Sefaria export folder", api("status")["library"]["works"] >= 3, api("status")["library"])
except Exception as e:  # noqa
    check("import a Sefaria export folder", False, e)

try:
    api("dl_start", work_ids=[1355, 487, 4634, 1120], english=True)  # Genesis, Berakhot, Rashi on Genesis, Deuteronomy
    t0 = time.time()
    while time.time() - t0 < 300:
        st = api("dl_status")
        if not st["running"]:
            break
        time.sleep(2)
    works = {w["title"]: w for w in api("lib_works")}
    check("REAL download from the internet (4 seforim)", all(t in works and works[t]["n_passages"] > 20 for t in ("Genesis", "Berakhot", "Deuteronomy")),
          f"errors={st.get('errors')} passages={ {k: v['n_passages'] for k, v in works.items()} }")
except Exception as e:  # noqa
    check("REAL download from the internet (4 seforim)", False, e)

try:
    r = api("search", q="בראשית ברא", lang="auto", opts={"prefixes": True})
    check("Hebrew search finds Genesis 1:1", any(x["ref"] == "Genesis 1:1" for x in r["results"]), r.get("total"))
    r = api("search", q="beginning", lang="auto", opts={})
    check("English search", r["total"] > 0, r.get("total"))
    r = api("gematria_words", text="שלום")
    check("Gematria value of שלום = 376", r["value"] == 376, r["value"])
    r = api("roshei", letters="בבא")
    check("Roshei teivos search runs", "total" in r, r.get("total"))
    fonts = api("fonts")
    fams = sorted({f["family"] for f in fonts})
    check("Hebrew fonts are included (40+ families, TrueType)", len(fams) >= 40 and all(f["file"].endswith(".ttf") for f in fonts),
          f"{len(fams)} families: {', '.join(fams[:12])}…")
    eng = {e["key"]: e for e in api("scan_engines")}
    check("Tesseract Hebrew engine available in the exe", eng["tesseract"]["ok"], eng["tesseract"]["info"])
except Exception as e:  # noqa
    check("core API", False, traceback.format_exc())

# ------------------------------------------------------------------ click through in Edge
from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as p:
    b = (p.chromium.launch(executable_path=os.environ["BROWSER"], args=["--no-sandbox"]) if os.environ.get("BROWSER")
         else p.chromium.launch(channel="msedge", headless=True))
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    pg = ctx.new_page()
    pg.on("console", lambda m: console.append(f"[{m.type}] {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: console.append(f"[PAGE ERROR] {e}"))
    pg.on("response", lambda r: failed_requests.append(f"{r.status} {r.url}") if r.status >= 400 else None)
    pg.goto(f"http://127.0.0.1:{PORT}/")
    pg.wait_for_timeout(2500)
    n = [0]

    def shot(name):
        n[0] += 1
        pg.screenshot(path=os.path.join(OUT, f"{n[0]:02d}_{name}.png"))

    def go(pid):
        pg.click(f'#rail button[data-id="{pid}"]')
        pg.wait_for_timeout(1200)

    def step(name, fn):
        before = len(console)
        try:
            fn()
            new = [c for c in console[before:] if "favicon" not in c]
            check(name, not any("PAGE ERROR" in c or "[error]" in c for c in new), "; ".join(new))
        except Exception as e:  # noqa
            check(name, False, f"{e.__class__.__name__}: {str(e)[:300]}")
            try:
                shot("FAILED_" + re.sub(r"\W+", "_", name)[:30])
            except Exception:
                pass

    step("Home screen", lambda: shot("home"))

    def fonts_render():
        pg.evaluate("document.fonts.ready")
        bad = pg.evaluate("""async () => { const fams = ["Frank Ruhl Libre", "David Libre", "Heebo", "Noto Rashi Hebrew", "Rubik", "Suez One"];
            const out = []; for (const f of fams) { await document.fonts.load(`24px "${f}"`, "שלום"); if (!document.fonts.check(`24px "${f}"`, "שלום")) out.push(f); } return out; }""")
        assert not bad, f"fonts not loading: {bad}"
        go("settings"); pg.click("#stTabs [data-t=fonts]"); pg.wait_for_timeout(2500); shot("fonts")
        assert pg.locator("#fList .list-item").count() >= 40, "font list too short"
    step("Hebrew fonts load and display", fonts_render)

    def library():
        go("library")
        pg.fill("#libFilter", "genesis"); pg.wait_for_timeout(700)
        pg.click('.work[data-id="1355"]'); pg.wait_for_timeout(2000)
        pg.click(".psg >> nth=0"); pg.wait_for_timeout(1200)
        shot("library_genesis")
        assert pg.locator(".psg").count() >= 3, "no passages shown"
        pg.select_option("#rMode", "daf"); pg.wait_for_timeout(3000); shot("library_daf"); pg.select_option("#rMode", "side")
        pg.fill("#libFilter", "berakhot"); pg.wait_for_timeout(600); pg.click('.work[data-id="487"]'); pg.wait_for_timeout(2000); shot("library_berakhot")
    step("Library: open Genesis & Berakhot", library)

    def note():
        pg.fill("#libFilter", "genesis"); pg.wait_for_timeout(500); pg.click('.work[data-id="1355"]'); pg.wait_for_timeout(1500)
        pg.hover(".psg >> nth=1"); pg.click(".psg >> nth=1 >> [data-act=note]"); pg.wait_for_timeout(400)
        pg.fill("#nTxt", "חידוש לבדיקה"); pg.click("#nOk"); pg.wait_for_timeout(1000)
        assert pg.locator(".psg .note").count() >= 1, "note not shown"
        shot("library_note")
    step("Library: add a note", note)

    def search():
        go("search")
        pg.fill("#sQ", "אור"); pg.click("#sGo"); pg.wait_for_timeout(1500); shot("search_hebrew")
        assert pg.locator(".result").count() > 0, "no Hebrew results"
        pg.fill("#sQ", "light"); pg.click("#sGo"); pg.wait_for_timeout(1500)
        pg.click("#sHeEq"); pg.wait_for_timeout(1500); shot("search_english")
    step("Search Hebrew & English", search)

    def gematria():
        go("gematria"); pg.fill("#gIn", "יהי אור"); pg.click("#gGo"); pg.wait_for_timeout(2500); shot("gematria")
    step("Gematria", gematria)

    def roshei():
        go("roshei"); pg.fill("#rtIn", "באה"); pg.click("#rtGo"); pg.wait_for_timeout(1500); shot("roshei")
    step("Roshei teivos", roshei)

    def analysis():
        go("analysis"); pg.wait_for_timeout(800); pg.click("#anGo"); pg.wait_for_timeout(2000); shot("analysis")
    step("Analysis", analysis)

    def tools():
        go("tools"); pg.wait_for_timeout(1200)
        for tid in ["today", "zmanim", "gem_all", "kb_en_to_he", "holidays"]:
            pg.fill("#tlF", ""); pg.wait_for_timeout(200)
            pg.evaluate("id => Tools.open(id)", tid); pg.wait_for_timeout(300)
            ta = pg.locator("#tlBody textarea")
            if ta.count():
                ta.first.fill("שלום akuo")
            pg.click("#tlRun"); pg.wait_for_timeout(900)
            assert pg.inner_text("#tlOut").strip(), f"tool {tid} gave no result"
        shot("tools")
    step("Tools (5 tools)", tools)

    step("Calendar", lambda: (go("calendar"), pg.wait_for_timeout(1500), shot("calendar")))

    def notes():
        go("notes"); pg.wait_for_timeout(1000)
        pg.click("#edPage"); pg.keyboard.press("Control+a"); pg.keyboard.press("Delete")
        pg.click("#kbToggle"); pg.click("#edPage"); pg.keyboard.type("akuo "); pg.click("#kbToggle")
        pg.click("#edPage"); pg.keyboard.press("End"); pg.keyboard.type('רמב"ם')
        pg.wait_for_timeout(500); pg.keyboard.press("Tab")
        pg.fill("#edTitle", "בדיקה"); pg.click('#edTb [data-a=save]'); pg.wait_for_timeout(1000)
        txt = pg.inner_text("#edPage")
        assert "שלום" in txt and "רבי משה בן מימון" in txt, f"editor text: {txt!r}"
        pg.click('#edTb [data-a=export]'); pg.wait_for_timeout(500)
        with pg.expect_download() as dl:
            pg.click('#modal [data-f=docx]')
        path = os.path.join(OUT, "notes_export.docx"); dl.value.save_as(path)
        assert os.path.getsize(path) > 3000, "docx too small"
        pg.click("#modal [data-close]") if pg.locator("#modal [data-close]").count() else None
        shot("notes")
    step("Notes: Hebrew keyboard, abbreviation, save, export Word", notes)

    step("My Library", lambda: (go("mylib"), pg.wait_for_timeout(1200), shot("mylib")))

    def covers():
        go("cover"); pg.wait_for_timeout(2000)
        for t in ["vilna", "night", "leather"]:
            pg.click(f"#cvTpls canvas[data-t={t}]"); pg.wait_for_timeout(500)
        pg.click("#cvTpls canvas[data-t=blank]"); pg.check("#cv_hideText"); pg.click("#cvAddText"); pg.wait_for_timeout(300)
        pg.fill('#cvProps textarea[data-k=text]', "העיצוב שלי"); pg.dispatch_event('#cvProps textarea[data-k=text]', "input")
        pg.select_option("#cvAddOrn", "menorah"); pg.wait_for_timeout(300)
        c = pg.locator("#cvCan").bounding_box()
        pg.mouse.move(c["x"] + c["width"] * .5, c["y"] + c["height"] * .5); pg.mouse.down()
        pg.mouse.move(c["x"] + c["width"] * .5, c["y"] + c["height"] * .2, steps=6); pg.mouse.up()
        assert pg.locator("#cvLayers .list-item").count() == 2, "own-design layers missing"
        shot("cover")
        with pg.expect_download() as dl:
            pg.click("#cvPng")
        dl.value.save_as(os.path.join(OUT, "cover.png"))
    step("Covers: templates + my own design (text, ornament, drag), export PNG", covers)

    def scanner():
        go("scanner"); pg.wait_for_timeout(1500)
        with pg.expect_file_chooser() as fc:
            pg.click("#scAdd")
        fc.value.set_files([os.path.join(HERE, "data", "handwriting_sample.jpg"), os.path.join(HERE, "data", "typed_hebrew.pdf")])
        pg.wait_for_timeout(1500)
        pg.click("#scKind button[data-k=\"auto\"]")
        pg.click("#scStart")
        for _ in range(180):
            pg.wait_for_timeout(1000)
            if pg.inner_text("#scStat").startswith("Done"):
                break
        pg.wait_for_timeout(1000)
        shot("scanner")
        text = pg.input_value("#scOut")
        open(os.path.join(OUT, "scanner_text.txt"), "w", encoding="utf-8").write(text)
        assert "בראשית" in text, f"scanner text: {text[:300]!r} / status: {pg.inner_text('#scStat')}"
        with pg.expect_download() as dl:
            pg.click("#scDocx"); pg.wait_for_timeout(400); pg.fill("#pIn", "scan-test"); pg.click("#pOk")
        dl.value.save_as(os.path.join(OUT, "scanner_export.docx"))
    step("Scanner: clean + read handwriting + PDF, save Word", scanner)

    def scanner_text():
        pg.click("#scText"); pg.wait_for_timeout(2000)
        t = pg.input_value("#scOut")
        assert "רש" in t and "Rashi on Genesis" in t, t[:300]
    step("Scanner: extract text from typed PDF", scanner_text)

    def share():
        go("share"); pg.wait_for_timeout(800); pg.check("#shOn"); pg.wait_for_timeout(2500); shot("share")
        assert re.search(r"\d{6}", pg.inner_text("#shInfo")), "no pairing code"
        pg.uncheck("#shOn"); pg.wait_for_timeout(500)
    step("Share: turn receiving on/off", share)

    def settings():
        go("settings"); pg.wait_for_timeout(2000); shot("settings_library")
        for t in ["fonts", "appearance", "privacy", "backup", "dev"]:
            pg.click(f"#stTabs [data-t={t}]"); pg.wait_for_timeout(1000)
        shot("settings_dev")
    step("Settings (all tabs)", settings)

    def themes():
        pg.select_option("#themeSel", "dark"); go("library"); pg.wait_for_timeout(1000); shot("dark")
        pg.select_option("#themeSel", "light"); pg.select_option("#langSel", "he"); pg.wait_for_timeout(800); shot("hebrew_menus")
        pg.select_option("#langSel", "en")
    step("Themes & Hebrew menus", themes)
    b.close()

proc.terminate()
time.sleep(1)
log = ""
lp = os.path.join(os.environ.get("TEST_DATA") or os.path.join(os.path.dirname(EXE), "data"), "app_log.txt")
if os.path.exists(lp):
    log = open(lp, encoding="utf-8", errors="replace").read()[-15000:]

passed = sum(1 for r in results if r[1])
with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8") as f:
    f.write(f"# Windows test of SeforimStudio.exe\n\n**{passed}/{len(results)} passed**\n\n")
    for name, ok, d in results:
        f.write(f"- {'✅' if ok else '❌'} {name}" + (f" — `{d}`" if d and not ok else "") + "\n")
    f.write("\n## Browser console errors/warnings\n" + ("\n".join(f"- {c}" for c in console) or "none") + "\n")
    f.write("\n## Failed requests\n" + ("\n".join(f"- {r}" for r in failed_requests) or "none") + "\n")
    f.write("\n## App log (tail)\n```\n" + (log or "(empty)") + "\n```\n")
print(f"\n{passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
