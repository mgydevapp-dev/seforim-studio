PLUGIN = {"id": "daily_learning", "name": "Daily Learning", "icon": "📅", "version": "1.0",
          "description": "Today's learning on the Home screen: Daf Yomi, Tehillim (monthly & weekly), Shnayim Mikra, "
                         "and your own plans to finish any sefer by a date — with check-off, progress and streaks."}

import datetime as dt
import uuid

from core import hcalendar as C
from core.data_tables import PARSHIYOS

# Traditional division of Tehillim by day of the Hebrew month (30 days) and by day of the week
TEHILLIM_MONTH = [(1, 9), (10, 17), (18, 22), (23, 28), (29, 34), (35, 38), (39, 43), (44, 48), (49, 54), (55, 59),
                  (60, 65), (66, 68), (69, 71), (72, 76), (77, 78), (79, 82), (83, 87), (88, 89), (90, 96), (97, 103),
                  (104, 105), (106, 107), (108, 112), (113, 118), ("119:1", "119:96"), ("119:97", "119:176"),
                  (120, 134), (135, 139), (140, 144), (145, 150)]
TEHILLIM_WEEK = [(1, 29), (30, 50), (51, 72), (73, 89), (90, 106), (107, 119), (120, 150)]
DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Shabbos"]


def _tref(a, b):
    return f"Psalms {a}" if a == b else f"Psalms {a}-{b}"


def tehillim_today(d):
    y, m, day = C.greg_to_heb(d)
    parts = [TEHILLIM_MONTH[day - 1]]
    if day == 29 and C.month_length(m, y) == 29:
        parts.append(TEHILLIM_MONTH[29])  # short month: say day 30 too
    return parts


def shnayim_mikra(app, d):
    """This week's parasha divided into 7 days (by verses) — Sunday through Shabbos."""
    name = C.parasha(d)
    names = [n.strip() for n in name.replace("–", "-").split("-")]
    ranges = [p for p in PARSHIYOS if any(n.lower().replace("'", "") == p[0].lower().replace("'", "") for n in names)]
    if not ranges:
        return {"parasha": name, "today": None, "note": "No regular parasha this week"}
    lib = app.lib
    rows = []
    for _, he, a, b in ranges:
        ha, hb = lib.find_ref(a), lib.find_ref(b)
        if not ha or not hb:
            return {"parasha": name, "today": None, "note": "Download Torah (Genesis–Deuteronomy) to use Shnayim Mikra"}
        s1 = lib.q1("SELECT seq FROM passages WHERE id=?", (ha["id"],))["seq"]
        s2 = lib.q1("SELECT seq FROM passages WHERE id=?", (hb["id"],))["seq"]
        rows += lib.q("SELECT ref FROM passages WHERE work_id=? AND seq BETWEEN ? AND ? ORDER BY seq", (ha["work_id"], s1, s2))
    n = len(rows)
    wd = C.weekday_index(d)
    a_i, b_i = wd * n // 7, (wd + 1) * n // 7 - 1
    if b_i < a_i:
        return {"parasha": name, "today": None}
    first, last = rows[a_i]["ref"], rows[b_i]["ref"]
    return {"parasha": name, "he": " / ".join(r[1] for r in ranges), "day": DAYS[wd], "from": first, "to": last,
            "today": f"{first} – {last.split(' ')[-1]}", "verses": b_i - a_i + 1}


# ---------------------------------------------------------------- personal plans
def _plans(app):
    return app.pget("daily_learning", "plans", [])


def _save(app, plans):
    app.pset("daily_learning", "plans", plans)


def _chapters(app, work_id):
    return [(c["node"], c["chapter"]) for c in app.lib.toc(work_id)]


def plan_today(app, p, d):
    chs = _chapters(app, p["work_id"])
    start, end = dt.date.fromisoformat(p["start"]), dt.date.fromisoformat(p["end"])
    days = (end - start).days + 1
    i = (d - start).days
    if not chs or i < 0 or i >= days:
        return None
    a, b = i * len(chs) // days, (i + 1) * len(chs) // days
    today = chs[a:b]
    done = p.get("done", {})
    upto = (i + 1) * len(chs) // days
    # chapters learned = the chapters of every day that was ticked off
    learned = min(len(chs), sum((j + 1) * len(chs) // days - j * len(chs) // days
                                for j in range(days) if done.get((start + dt.timedelta(j)).isoformat())))
    return {"id": p["id"], "title": p["title"], "work_id": p["work_id"], "chapters": [{"node": n, "chapter": c} for n, c in today],
            "label": (f"{today[0][1]}" + (f"–{today[-1][1]}" if len(today) > 1 else "")) if today else "(no new chapter today — review)",
            "done": bool(done.get(d.isoformat())), "progress": learned, "total": len(chs), "should_be": upto,
            "day": i + 1, "days": days}


def today(app, a):
    d = dt.date.fromisoformat(a["date"]) if a.get("date") else dt.date.today()
    daf = C.daf_yomi(d)
    out = {"date": d.isoformat(), "hebrew": C.format_hebrew(*C.greg_to_heb(d)),
           "daf": {"title": f"Daf Yomi: {daf[0]} {daf[1]}", "he": daf[2], "ref": f"{daf[0]} {daf[1]}a"},
           "tehillim_month": [{"label": f"Tehillim {x[0]}–{x[1]}" if x[0] != x[1] else f"Tehillim {x[0]}", "ref": "Psalms " + str(x[0])} for x in tehillim_today(d)],
           "tehillim_week": {"label": f"Tehillim {TEHILLIM_WEEK[C.weekday_index(d)][0]}–{TEHILLIM_WEEK[C.weekday_index(d)][1]}",
                             "ref": f"Psalms {TEHILLIM_WEEK[C.weekday_index(d)][0]}"},
           "shnayim": shnayim_mikra(app, d),
           "plans": [x for x in (plan_today(app, p, d) for p in _plans(app)) if x]}
    checks = app.pget("daily_learning", "checks", {}).get(d.isoformat(), {})
    out["checks"] = checks
    streak, k = 0, d
    allchecks = app.pget("daily_learning", "checks", {})
    while allchecks.get(k.isoformat()) and any(allchecks[k.isoformat()].values()):
        streak += 1
        k -= dt.timedelta(days=1)
    out["streak"] = streak
    return out


def check(app, a):
    allc = app.pget("daily_learning", "checks", {})
    day = allc.setdefault(a.get("date") or dt.date.today().isoformat(), {})
    day[a["key"]] = bool(a.get("on"))
    app.pset("daily_learning", "checks", allc)
    if a["key"].startswith("plan:"):
        plans = _plans(app)
        for p in plans:
            if "plan:" + p["id"] == a["key"]:
                p.setdefault("done", {})[a.get("date") or dt.date.today().isoformat()] = bool(a.get("on"))
        _save(app, plans)
    return {"ok": True}


def add_plan(app, a):
    w = app.lib.work(int(a["work_id"]))
    if not w:
        raise ValueError("That sefer is not in your library")
    plans = _plans(app)
    start = a.get("start") or dt.date.today().isoformat()
    if a.get("end"):
        end = a["end"]
    else:  # by chapters per day
        n = len(_chapters(app, w["id"]))
        per = max(1, int(a.get("per_day") or 1))
        end = (dt.date.fromisoformat(start) + dt.timedelta(days=max(0, -(-n // per) - 1))).isoformat()
    plans.append({"id": uuid.uuid4().hex[:8], "work_id": w["id"], "title": w["title"] + (f" — {w['he_title']}" if w.get("he_title") else ""),
                  "start": start, "end": end, "done": {}})
    _save(app, plans)
    return plans[-1]


def del_plan(app, a):
    _save(app, [p for p in _plans(app) if p["id"] != a["id"]])
    return {"ok": True}


def plans(app, a):
    d = dt.date.today()
    out = []
    for p in _plans(app):
        t = plan_today(app, p, d) or {}
        out.append({**p, "today": t.get("label"), "progress": t.get("progress", 0), "total": t.get("total") or len(_chapters(app, p["work_id"])),
                    "day": t.get("day"), "days": t.get("days")})
    return out


ROUTES = {"today": today, "check": check, "add_plan": add_plan, "del_plan": del_plan, "plans": plans}


def home(app):
    t = today(app, {})
    items = [(t["daf"]["title"], t["daf"]["ref"], "daf")] + [(x["label"], x["ref"], "tehillim") for x in t["tehillim_month"]]
    if t["shnayim"].get("today"):
        items.append((f"Shnayim Mikra: {t['shnayim']['today']}", t["shnayim"]["from"], "shnayim"))
    for p in t["plans"]:
        items.append((f"{p['title']}: {p['label']}", None, "plan:" + p["id"]))
    html = "".join(f"<div class='list-item small' {'data-ref=' + chr(34) + r + chr(34) if r else ''}>{'✅' if t['checks'].get(k) else '◻️'} {lbl}</div>" for lbl, r, k in items)
    return {"title": "Today's learning" + (f" · 🔥 {t['streak']} days" if t["streak"] else ""), "html": html, "open": "daily_learning"}


PAGE_JS = r"""
App.register("daily_learning", { title: "Learning", icon: "📅", render(el) { DL.render(el); }, onShow() { if (this.el) DL.render(this.el); } });
const DL = {
  async render(el) {
    const t = await Plugins.call("daily_learning", "today");
    const row = (key, label, sub, ref, extra = "") => `<div class="list-item row"><input type="checkbox" data-k="${key}" ${t.checks[key] ? "checked" : ""}>
      <div style="flex:1"><b>${esc(label)}</b> ${sub ? `<span class="he" style="font-size:17px">${esc(sub)}</span>` : ""} ${extra}</div>${ref ? `<button class="btn small" data-ref2="${esc(ref)}">Open ›</button>` : ""}</div>`;
    const sh = t.shnayim;
    el.innerHTML = `<h1 class="page-title">📅 Daily Learning <small>${esc(t.hebrew)}${t.streak ? ` · 🔥 ${t.streak}-day streak` : ""}</small></h1>
      <div class="grid g2"><div class="card"><h2 style="margin-top:0">Today</h2>
        ${row("daf", t.daf.title, t.daf.he, t.daf.ref)}
        ${t.tehillim_month.map((x, i) => row("teh" + i, x.label + " (day of the month)", "", x.ref)).join("")}
        ${row("tehw", t.tehillim_week.label + " (day of the week)", "", t.tehillim_week.ref)}
        ${sh.today ? row("shnayim", `Shnayim Mikra — ${sh.parasha} (${sh.day})`, sh.he || "", sh.from, `<div class="small muted">${esc(sh.today)} · ${sh.verses} pesukim twice + Targum</div>`) : `<div class="list-item small muted">Shnayim Mikra: ${esc(sh.note || sh.parasha)}</div>`}
        ${t.plans.map(p => row("plan:" + p.id, p.title, "", null, `<div class="small">${esc(p.label)} · day ${p.day}/${p.days}</div><div class="progress"><div style="width:${100 * p.progress / p.total}%"></div></div>`) + `<div class="row" style="margin:-4px 0 6px 32px">${p.chapters.map(c => `<button class="btn small" data-w="${p.work_id}" data-n="${esc(c.node)}" data-c="${esc(c.chapter)}">${esc(c.chapter || c.node)}</button>`).join("")}</div>`).join("")}
      </div>
      <div class="card"><h2 style="margin-top:0">My learning plans</h2><div id="dlPlans"></div>
        <h2>New plan — finish a sefer</h2>
        <select id="dlW" style="width:100%"></select>
        <div class="row" style="margin-top:6px"><label class="small">Start <input type="date" id="dlS"></label>
          <label class="small"><input type="radio" name="dlm" value="end" checked> finish by <input type="date" id="dlE"></label>
          <label class="small"><input type="radio" name="dlm" value="per"> <input type="number" id="dlP" value="1" min="1" style="width:60px"> chapters a day</label></div>
        <button class="btn primary" id="dlAdd" style="margin-top:8px">+ Add plan</button></div></div>`;
    $$("[data-k]", el).forEach(c => c.onchange = () => Plugins.call("daily_learning", "check", { key: c.dataset.k, on: c.checked }).then(() => DL.render(el)));
    $$("[data-ref2]", el).forEach(b => b.onclick = () => App.quickGo(b.dataset.ref2));
    $$("[data-w]", el).forEach(b => b.onclick = () => Library.open(+b.dataset.w, b.dataset.n, b.dataset.c));
    const works = await App.api("lib_works");
    $("#dlW", el).innerHTML = works.map(w => `<option value="${w.id}">${esc(w.title)}${w.he_title ? " — " + esc(w.he_title) : ""}</option>`).join("");
    const d0 = new Date(); $("#dlS", el).value = d0.toISOString().slice(0, 10); d0.setMonth(d0.getMonth() + 6); $("#dlE", el).value = d0.toISOString().slice(0, 10);
    $("#dlAdd", el).onclick = async () => {
      const per = $("input[name=dlm]:checked", el).value === "per";
      await Plugins.call("daily_learning", "add_plan", { work_id: +$("#dlW", el).value, start: $("#dlS", el).value, end: per ? null : $("#dlE", el).value, per_day: +$("#dlP", el).value });
      App.toast("Plan added"); DL.render(el);
    };
    const ps = await Plugins.call("daily_learning", "plans");
    $("#dlPlans", el).innerHTML = ps.map(p => `<div class="list-item"><div class="row"><b style="flex:1">${esc(p.title)}</b><a href="#" data-del="${p.id}" class="small">remove</a></div>
      <div class="small muted">${esc(p.start)} → ${esc(p.end)} · ${p.progress}/${p.total} chapters ${p.today ? "· today: " + esc(p.today) : ""}</div>
      <div class="progress"><div style="width:${100 * p.progress / (p.total || 1)}%"></div></div></div>`).join("") || `<p class="small muted">No plans yet — e.g. Mishnah Berurah by Pesach, or Tanya in a year.</p>`;
    $$("[data-del]", el).forEach(a => a.onclick = async e => { e.preventDefault(); await Plugins.call("daily_learning", "del_plan", { id: a.dataset.del }); DL.render(el); });
  }
};
"""
