PLUGIN = {"id": "chazara", "name": "Chazara Cards", "icon": "🔁", "version": "1.0",
          "description": "Review what you learn with flash cards that come back at the right time (spaced repetition). "
                         "Add any passage, a whole chapter, or your own question and answer."}

import datetime as dt
import uuid

# Spaced repetition (simplified SM-2): each card has an interval in days and an ease factor.
GRADES = {"again": 0, "hard": 3, "good": 4, "easy": 5}


def _cards(app):
    return app.pget("chazara", "cards", [])


def _save(app, cards):
    app.pset("chazara", "cards", cards)


def _today():
    return dt.date.today().isoformat()


def add(app, a):
    cards = _cards(app)
    added = 0
    if a.get("question"):
        cards.append({"id": uuid.uuid4().hex[:10], "front": a["question"], "back": a.get("answer", ""), "ref": a.get("ref", ""),
                      "deck": a.get("deck") or "My questions", "due": _today(), "interval": 0, "ease": 2.5, "reps": 0})
        added = 1
    else:
        rows = []
        if a.get("ref"):
            r = app.lib.find_ref(a["ref"])
            if not r:
                raise ValueError(f"Could not find {a['ref']} in your library")
            if a.get("whole_chapter"):
                rows = app.lib.chapter(r["work_id"], r["node"], r["chapter"])
            else:
                p = app.lib.passage(r["id"])
                rows = [p] if p else []
        have = {c.get("pid") for c in cards}
        for p in rows:
            if p["id"] in have:
                continue
            cards.append({"id": uuid.uuid4().hex[:10], "pid": p["id"], "ref": p["ref"], "front": p["ref"], "back": "",
                          "deck": a.get("deck") or p["ref"].rsplit(" ", 1)[0], "due": _today(), "interval": 0, "ease": 2.5, "reps": 0})
            added += 1
    _save(app, cards)
    return {"added": added, "total": len(cards)}


def due(app, a):
    t = _today()
    deck = a.get("deck")
    cards = [c for c in _cards(app) if c["due"] <= t and (not deck or c["deck"] == deck)]
    cards.sort(key=lambda c: (c["due"], c["reps"]))
    out = []
    for c in cards[:int(a.get("limit") or 50)]:
        c = dict(c)
        if c.get("pid"):
            p = app.lib.passage(c["pid"])
            if p:
                c["he"], c["en"] = p["he"], p["en"]
        out.append(c)
    return {"cards": out, "due": len(cards)}


def grade(app, a):
    q = GRADES[a["grade"]]
    cards = _cards(app)
    for c in cards:
        if c["id"] == a["id"]:
            if q < 3:
                c["reps"], c["interval"] = 0, 1
            else:
                c["reps"] += 1
                c["interval"] = 1 if c["reps"] == 1 else 3 if c["reps"] == 2 else round(c["interval"] * c["ease"])
                if q == 5:
                    c["interval"] = round(c["interval"] * 1.3) + 1
            c["ease"] = max(1.3, c["ease"] + 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
            c["due"] = (dt.date.today() + dt.timedelta(days=c["interval"])).isoformat()
            c["last"] = _today()
            log = app.pget("chazara", "log", {})
            log[_today()] = log.get(_today(), 0) + 1
            app.pset("chazara", "log", log)
            break
    _save(app, cards)
    return {"ok": True}


def decks(app, a):
    t = _today()
    d = {}
    for c in _cards(app):
        x = d.setdefault(c["deck"], {"deck": c["deck"], "cards": 0, "due": 0, "learned": 0})
        x["cards"] += 1
        x["due"] += c["due"] <= t
        x["learned"] += c["reps"] >= 3
    return sorted(d.values(), key=lambda x: -x["due"])


def remove(app, a):
    _save(app, [c for c in _cards(app) if c["id"] != a.get("id") and c["deck"] != a.get("deck")])
    return {"ok": True}


ROUTES = {"add": add, "due": due, "grade": grade, "decks": decks, "remove": remove}


def home(app):
    n = sum(1 for c in _cards(app) if c["due"] <= _today())
    if not _cards(app):
        return None
    return {"title": "Chazara", "html": f"<p class='small'>{'🔁 <b>' + str(n) + '</b> cards to review today' if n else '✅ All reviewed for today'}</p>",
            "open": "chazara"}


PAGE_JS = r"""
App.register("chazara", { title: "Chazara", icon: "🔁", render(el) { CZ.render(el); }, onShow() { if (this.el) CZ.render(this.el); } });
const CZ = {
  async render(el) {
    const decks = await Plugins.call("chazara", "decks");
    const d = await Plugins.call("chazara", "due", {});
    el.innerHTML = `<h1 class="page-title">🔁 Chazara <small>flash cards that come back just before you forget</small></h1>
      <div class="grid g2"><div class="card" id="czCard"></div>
      <div class="card"><h2 style="margin-top:0">Add cards</h2>
        <div class="row"><input id="czRef" placeholder="e.g. Berakhot 2a, Genesis 1:1, משנה ברכות א:א" style="flex:1">
        <label class="small"><input type="checkbox" id="czCh"> whole chapter / daf</label><button class="btn primary" id="czAdd">+ Add</button></div>
        <h3>…or your own question</h3><input id="czQ" placeholder="Question (e.g. What is the earliest time for Shema?)" style="width:100%">
        <textarea id="czA" placeholder="Answer" style="width:100%;height:60px;margin-top:4px"></textarea>
        <div class="row"><input id="czDeck" placeholder="Deck name (optional)" style="flex:1"><button class="btn" id="czAddQ">+ Add question</button></div>
        <h2>Decks</h2>${decks.map(x => `<div class="list-item row"><b style="flex:1">${esc(x.deck)}</b><span class="small">${x.due} due · ${x.cards} cards · ${x.learned} known</span>
          <a href="#" class="small" data-rmd="${esc(x.deck)}">remove</a></div>`).join("") || `<p class="small muted">No cards yet. Add a passage above — or right-click any passage in the Library.</p>`}
      </div></div>`;
    this.queue = d.cards; this.el = el; this.show();
    $("#czAdd", el).onclick = async () => { const r = await Plugins.call("chazara", "add", { ref: $("#czRef", el).value, whole_chapter: $("#czCh", el).checked }); App.toast(`Added ${r.added} card(s)`); this.render(el); };
    $("#czAddQ", el).onclick = async () => { if (!$("#czQ", el).value.trim()) return App.toast("Type a question", true);
      await Plugins.call("chazara", "add", { question: $("#czQ", el).value, answer: $("#czA", el).value, deck: $("#czDeck", el).value }); App.toast("Card added"); this.render(el); };
    $$("[data-rmd]", el).forEach(a => a.onclick = async e => { e.preventDefault(); if (await App.confirm("Remove all cards of " + a.dataset.rmd + "?")) { await Plugins.call("chazara", "remove", { deck: a.dataset.rmd }); this.render(el); } });
  },
  show() {
    const box = $("#czCard", this.el), c = this.queue[0];
    if (!c) { box.innerHTML = `<h2 style="margin-top:0">Today's review</h2><p>✅ Nothing left to review today. Come back tomorrow!</p>`; return; }
    box.innerHTML = `<h2 style="margin-top:0">Today's review <small class="muted">${this.queue.length} left</small></h2>
      <div class="small muted">${esc(c.deck)}</div><div style="font-size:20px;margin:8px 0"><b>${esc(c.front)}</b></div>
      ${c.he ? `<p class="small muted">Say it over by heart, then show it.</p>` : ""}
      <div id="czBack" style="display:none">${c.he ? `<div class="he" style="font-size:22px;line-height:1.7">${c.he}</div>` : ""}${c.en ? `<div class="small" style="margin-top:6px">${c.en}</div>` : ""}${c.back ? `<div style="white-space:pre-wrap">${esc(c.back)}</div>` : ""}</div>
      <div class="row" id="czBtns" style="margin-top:10px"><button class="btn primary" id="czShow">Show answer</button></div>`;
    $("#czShow", box).onclick = () => {
      $("#czBack", box).style.display = "";
      $("#czBtns", box).innerHTML = [["again", "Again"], ["hard", "Hard"], ["good", "Good"], ["easy", "Easy"]].map(([g, l]) => `<button class="btn ${g === "good" ? "primary" : ""}" data-g="${g}">${l}</button>`).join("") + (c.ref ? ` <button class="btn small" id="czOpen">Open in library</button>` : "");
      $$("[data-g]", box).forEach(b => b.onclick = async () => { await Plugins.call("chazara", "grade", { id: c.id, grade: b.dataset.g }); this.queue.shift(); if (b.dataset.g === "again") this.queue.push(c); this.show(); });
      const o = $("#czOpen", box); if (o) o.onclick = () => App.quickGo(c.ref);
    };
  }
};
"""
