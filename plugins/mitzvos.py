PLUGIN = {"id": "mitzvos", "name": "613 Mitzvos", "icon": "📜", "version": "1.0",
          "description": "The 613 mitzvos numbered like the Rambam — 248 positive (עשה) and 365 negative (לא תעשה) — plus the "
                         "7 mitzvos d'Rabbanan. Each mitzvah shows its source in the Torah, the Rambam's words, the Sefer HaChinukh "
                         "and every sefer that discusses it."}

import re

RABBANAN = [
    ("נטילת ידים", "Washing the hands (before bread)", "Berakhot 53b"),
    ("עירובין", "Eruvin (carrying and walking on Shabbos)", "Eruvin 21b"),
    ("ברכות", "Blessings before enjoying food and other pleasures", "Berakhot 35a"),
    ("הלל", "Saying Hallel on Yom Tov", "Pesachim 117a"),
    ("נר שבת", "Lighting Shabbos candles", "Shabbat 25b"),
    ("מקרא מגילה", "Reading the Megillah on Purim", "Megillah 7a"),
    ("נר חנוכה", "Lighting Chanukah lights", "Shabbat 21b"),
]
SOURCES = {"positive": ("Mishneh Torah, Positive Mitzvot", "Sefer HaMitzvot, Positive Commandments"),
           "negative": ("Mishneh Torah, Negative Mitzvot", "Sefer HaMitzvot, Negative Commandments")}


def _rows(app, title):
    return app.lib.q("SELECT p.id, p.ref, p.he, p.en, p.chapter, p.verse FROM passages p JOIN works w ON w.id=p.work_id "
                     "WHERE w.title=? ORDER BY p.seq", (title,))


def _short(s, n=220):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def listing(app, a):
    out = {"positive": [], "negative": [], "rabbanan": [], "missing": []}
    for kind, (mt, _) in SOURCES.items():
        rows = _rows(app, mt)
        if not rows:
            out["missing"].append(mt)
        for i, r in enumerate(rows):
            out[kind].append({"n": i + 1, "he": _short(re.sub(r"^\s*מצו?ה\s+\S+\s*[:.]?\s*", "", r["he"] or "")),
                              "en": _short(r["en"] or ""), "ref": r["ref"], "id": r["id"]})
    out["rabbanan"] = [{"n": i + 1, "he": he, "en": en, "ref": ref} for i, (he, en, ref) in enumerate(RABBANAN)]
    return out


def detail(app, a):
    kind, n = a["kind"], int(a["n"])
    if kind == "rabbanan":
        he, en, ref = RABBANAN[n - 1]
        r = app.lib.find_ref(ref)
        p = app.lib.passage(r["id"]) if r else None
        return {"title_he": he, "title_en": en, "sections": [{"name": "Talmud", "ref": ref, "he": p["he"] if p else "", "en": p["en"] if p else ""}],
                "links": []}
    mt, shm = SOURCES[kind]
    item = listing(app, {})[kind][n - 1]
    sections = []
    # the Rambam's Sefer HaMitzvot on this mitzvah
    rows = app.lib.q("SELECT p.id, p.ref, p.he, p.en FROM passages p JOIN works w ON w.id=p.work_id WHERE w.title='Sefer HaMitzvot' "
                     "AND p.ref>=? AND p.ref<? ORDER BY p.seq LIMIT 40", (f"{shm} {n}:", f"{shm} {n};"))
    if rows:
        sections.append({"name": "Rambam, Sefer HaMitzvot", "ref": f"{shm} {n}", "he": " ".join(r["he"] or "" for r in rows),
                         "en": " ".join(r["en"] or "" for r in rows), "id": rows[0]["id"]})
    # everything linked to it: the Torah verse, Sefer HaChinukh, Mishneh Torah, Smag …
    groups = app.lib.connections(item["ref"]) + (app.lib.connections(f"{shm} {n}:1") if rows else [])
    seen, links = set(), []
    for g in groups:
        for it in g["items"]:
            for x in it["texts"][:3]:
                if x["ref"] in seen:
                    continue
                seen.add(x["ref"])
                links.append({"title": g["title"], "he_title": g["he_title"], "ref": x["ref"], "id": x["id"],
                              "he": _short(x["he"], 400), "en": _short(x["en"], 400), "cat": it.get("cat") or ""})
    order = {"Tanakh": 0, "Halakhah": 1}
    links.sort(key=lambda l: (order.get(l["cat"], 5), l["title"]))
    return {"title_he": item["he"], "title_en": item["en"], "ref": item["ref"], "sections": sections, "links": links}


ROUTES = {"list": listing, "detail": detail}


def home(app):
    return None


PAGE_JS = r"""
App.register("mitzvos", { title: "613 Mitzvos", icon: "📜", render(el) { MZ.render(el); } });
const MZ = {
  async render(el) {
    el.innerHTML = `<h1 class="page-title">📜 תרי״ג מצוות <small>613 mitzvos — numbered like the Rambam</small></h1><p class="muted">Loading…</p>`;
    const L = this.L = await Plugins.call("mitzvos", "list");
    this.kind = this.kind || "positive";
    el.innerHTML = `<h1 class="page-title">📜 תרי״ג מצוות <small>613 mitzvos — numbered like the Rambam</small></h1>
      ${L.missing.length ? `<div class="lib-health">Install the full library to see all the mitzvos (missing: ${L.missing.map(esc).join(", ")}).</div>` : ""}
      <div class="row" style="gap:8px;flex-wrap:wrap;margin-bottom:10px">
        <div class="seg" id="mzKind" style="flex:0 0 auto">
          <button data-k="positive">✅ מצוות עשה<small>${L.positive.length} positive</small></button>
          <button data-k="negative">⛔ מצוות לא תעשה<small>${L.negative.length} negative</small></button>
          <button data-k="rabbanan">📜 מצוות דרבנן<small>${L.rabbanan.length} rabbinic</small></button></div>
        <input id="mzQ" placeholder="Search a mitzvah… (e.g. Shabbos, תפילין, 25)" style="flex:1;min-width:200px">
        <label class="tgl small"><input type="checkbox" id="mzEn" checked> English</label></div>
      <div class="grid mz-grid"><div class="card mz-list" id="mzList"></div><div class="card" id="mzDet"><p class="muted">Choose a mitzvah to see its source in the Torah, the Rambam, the Chinukh and more.</p></div></div>`;
    $$("#mzKind button", el).forEach(b => b.onclick = () => { this.kind = b.dataset.k; this.draw(); });
    $("#mzQ", el).oninput = () => this.draw(); $("#mzEn", el).onchange = () => this.draw();
    this.el = el; this.draw();
  },
  draw() {
    const el = this.el, q = $("#mzQ", el).value.trim().toLowerCase(), en = $("#mzEn", el).checked;
    $$("#mzKind button", el).forEach(b => b.classList.toggle("on", b.dataset.k === this.kind));
    const label = { positive: "עשה", negative: "ל״ת", rabbanan: "דרבנן" }[this.kind];
    const items = this.L[this.kind].filter(m => !q || String(m.n) === q || (m.he + " " + m.en).toLowerCase().includes(q));
    $("#mzList", el).innerHTML = items.map(m => `<div class="mz-item" data-n="${m.n}"><span class="mz-n">${label} ${App.heNum(m.n)}<small>${m.n}</small></span>
      <div><div class="he">${esc(m.he)}</div>${en && m.en ? `<div class="small muted">${esc(m.en)}</div>` : ""}</div></div>`).join("") || `<p class="muted">Nothing found.</p>`;
    $$(".mz-item", el).forEach(x => x.onclick = () => { $$(".mz-item.on", el).forEach(y => y.classList.remove("on")); x.classList.add("on"); this.show(+x.dataset.n); });
  },
  async show(n) {
    const box = $("#mzDet", this.el); box.innerHTML = `<p class="muted">Loading…</p>`;
    const d = await Plugins.call("mitzvos", "detail", { kind: this.kind, n });
    const en = $("#mzEn", this.el).checked;
    const kindName = { positive: "מצות עשה", negative: "מצות לא תעשה", rabbanan: "מצוה דרבנן" }[this.kind];
    box.innerHTML = `<div class="small muted">${kindName} ${App.heNum(n)} · #${n}</div><h2 class="he" style="margin:4px 0">${esc(d.title_he)}</h2>${en ? `<p>${esc(d.title_en)}</p>` : ""}
      ${d.ref ? `<a href="#" data-go="${esc(d.ref)}" class="small">Open in the library ›</a>` : ""}
      ${d.sections.map(s => `<h3>${esc(s.name)}</h3><div class="he" style="line-height:1.7">${esc(s.he)}</div>${en && s.en ? `<div class="small" style="margin-top:4px">${esc(s.en)}</div>` : ""}<a href="#" data-go="${esc(s.ref)}" class="small">${esc(s.ref)} ›</a>`).join("")}
      ${d.links.length ? `<h3>Sources & seforim on this mitzvah</h3>${d.links.map(l => `<details class="comm-group"><summary><span class="cg-he">${esc(l.he_title && l.he_title !== l.title ? l.he_title : "")}</span> <span class="cg-en">${esc(l.title)} · ${esc(l.ref)}</span></summary>
        <div class="comm-item"><div class="he">${esc(l.he)}</div>${en && l.en ? `<div class="en">${esc(l.en)}</div>` : ""}<a href="#" data-go="${esc(l.ref)}" class="small">open ›</a></div></details>`).join("")}` : ""}`;
    $$("[data-go]", box).forEach(a => a.onclick = e => { e.preventDefault(); App.quickGo(a.dataset.go); });
  }
};
"""
