PLUGIN = {"id": "tehillim", "name": "Tehillim", "icon": "📖", "version": "1.0",
          "description": "Tehillim for a name (Tehillim 119 by the letters of the name, plus נשמה), "
                         "for a person's age (their kapitel), and traditional Tehillim for refuah, parnassa, travel and more."}

from core import hebrew as H
from core.tools import tool

# The 22 sections of Tehillim 119 (8 pesukim each), one for every letter of the alef-beis
LETTERS = "אבגדהוזחטיכלמנסעפצקרשת"
FINALS = {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"}
OCCASIONS = [
    ("Refuah – for the sick (רפואה)", [20, 6, 9, 13, 16, 17, 18, 22, 23, 28, 30, 31, 32, 33, 37, 38, 39, 41, 49, 55, 56, 69, 86, 88, 89, 90, 91, 102, 103, 104, 107, 116, 118, 142, 143, 148]),
    ("Parnassa – livelihood (פרנסה)", [23, 34, 36, 62, 65, 67, 85, 104, 121, 136, 145]),
    ("Travel – Tefilas HaDerech (דרך)", [91, 121]),
    ("Shidduch (שידוך)", [32, 38, 70, 71, 121, 124]),
    ("Children (זרע של קיימא)", [102, 103, 128]),
    ("Easy birth (לידה)", [1, 2, 3, 4, 20, 21, 22, 23, 24, 33, 47, 72, 86, 90, 91, 92, 93, 104, 112]),
    ("Thanksgiving (הודאה)", [100, 107, 118, 136]),
    ("Times of trouble (עת צרה)", [20, 22, 69, 83, 121, 130, 142]),
    ("Yahrzeit / for a neshama (עליה לנשמה)", [33, 16, 17, 72, 91, 104, 130]),
    ("Shalom bayis (שלום בית)", [128, 133]),
    ("Success (הצלחה)", [1, 57, 112, 122]),
    ("Repentance (תשובה)", [6, 25, 32, 38, 51, 102, 130, 143]),
]


def name_sections(name):
    """[(letter, first verse, last verse)] of Tehillim 119 for every letter of the name."""
    out = []
    for ch in H.letters_only(name):
        ch = FINALS.get(ch, ch)
        if ch in LETTERS:
            i = LETTERS.index(ch)
            out.append({"letter": ch, "ref": f"Psalms 119:{i * 8 + 1}-{i * 8 + 8}", "first": f"Psalms 119:{i * 8 + 1}"})
    return out


def for_name(app, a):
    name = a.get("name", "")
    mother = a.get("mother", "")
    secs = name_sections(name)
    if mother:
        secs += [{"letter": "", "sep": "בן/בת"}] + name_sections(mother)
    neshama = name_sections("נשמה") if a.get("neshama") else []
    return {"name": name, "sections": secs, "neshama": neshama,
            "age_kapitel": int(a["age"]) + 1 if str(a.get("age") or "").isdigit() and 0 <= int(a["age"]) < 150 else None}


def texts(app, a):
    """The Hebrew text of the given refs (Psalms ...) from the library."""
    out = []
    for ref in a.get("refs", [])[:60]:
        r = app.lib.find_ref(ref.split("-")[0])
        if not r:
            out.append({"ref": ref, "missing": True})
            continue
        rows = app.lib.chapter(r["work_id"], r["node"], r["chapter"])
        if "-" in ref and ":" in ref:
            a1, b1 = ref.split(":")[-1].split("-")
            rows = [x for x in rows if x["verse"].isdigit() and int(a1) <= int(x["verse"]) <= int(b1)]
        out.append({"ref": ref, "verses": [{"v": x["verse"], "he": x["he"], "en": x["en"]} for x in rows]})
    return out


ROUTES = {"for_name": for_name, "texts": texts, "occasions": lambda app, a: [{"name": n, "chapters": c} for n, c in OCCASIONS]}


@tool("Tehillim", "Tehillim 119 for a name", "Which pesukim of Tehillim 119 to say for each letter of a name.",
      [{"name": "text", "label": "Hebrew name", "type": "text"}])
def tehillim_name(a, ctx=None):
    return {"headers": ["Letter", "Tehillim"], "table": [[s["letter"], s["ref"]] for s in name_sections(a.get("text", ""))]}


@tool("Tehillim", "Kapitel for an age", "The chapter of Tehillim to say for a person's age (age + 1).",
      [{"name": "n", "label": "Age", "type": "number"}])
def tehillim_age(a, ctx=None):
    n = int(float(a.get("n") or 0))
    return f"Age {n} → Tehillim {n + 1} (קאפיטל {H.int_to_hebrew(n + 1)})" if 0 <= n < 150 else "Please type an age from 0 to 149"


PAGE_JS = r"""
App.register("tehillim", { title: "Tehillim", icon: "📖", render(el) { TH.render(el); } });
const TH = {
  async render(el) {
    const occ = await Plugins.call("tehillim", "occasions");
    el.innerHTML = `<h1 class="page-title">📖 Tehillim</h1><div class="grid g2">
      <div class="card"><h2 style="margin-top:0">For a name</h2>
        <div class="row"><input id="thN" class="he" placeholder="שם" style="flex:1"><span>בן/בת</span><input id="thM" class="he" placeholder="שם האם (optional)" style="flex:1"></div>
        <div class="row small"><label><input type="checkbox" id="thNs" checked> add נשמה</label><label>Age <input type="number" id="thAge" style="width:60px"></label>
        <button class="btn primary" id="thGo">Show</button></div></div>
      <div class="card"><h2 style="margin-top:0">For an occasion</h2>${occ.map((o, i) => `<button class="btn small" data-o="${i}" style="margin:2px">${esc(o.name)}</button>`).join("")}</div></div>
      <div id="thOut" class="card" style="margin-top:12px;display:none"></div>`;
    const show = async (title, refs) => {
      const out = $("#thOut", el); out.style.display = ""; out.innerHTML = `<h2 style="margin-top:0">${esc(title)}</h2><p class="small muted">Loading…</p>`;
      const t = await Plugins.call("tehillim", "texts", { refs });
      out.innerHTML = `<h2 style="margin-top:0">${esc(title)} <button class="btn small" id="thCopy">Copy all</button></h2>` + t.map(x => x.missing
        ? `<p class="small muted">${esc(x.ref)} — Tehillim is not in your library yet (Library → Tanakh → Writings → Psalms).</p>`
        : `<h3>${esc(x.ref.replace("Psalms", "Tehillim"))}</h3><div class="he" style="font-size:21px;line-height:1.8">${x.verses.map(v => `${v.he} `).join("")}</div>`).join("");
      $("#thCopy", out).onclick = () => { navigator.clipboard.writeText(out.innerText); App.toast("Copied"); };
    };
    $("#thGo", el).onclick = async () => {
      const r = await Plugins.call("tehillim", "for_name", { name: $("#thN", el).value, mother: $("#thM", el).value, neshama: $("#thNs", el).checked, age: $("#thAge", el).value });
      const refs = r.sections.filter(s => s.ref).map(s => s.ref).concat(r.neshama.map(s => s.ref));
      if (r.age_kapitel) refs.unshift("Psalms " + r.age_kapitel);
      if (!refs.length) return App.toast("Type a Hebrew name", true);
      show("Tehillim for " + r.name, refs);
    };
    $$("[data-o]", el).forEach(b => b.onclick = () => { const o = occ[+b.dataset.o]; show(o.name, o.chapters.map(c => "Psalms " + c)); });
  }
};
"""
