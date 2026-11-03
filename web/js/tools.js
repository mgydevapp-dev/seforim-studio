/* 130+ Hebrew tools (generic runner) and the Hebrew/English month calendar */
const Tools = {
  list: [], cur: null,
  async render(el) {
    el.innerHTML = `<div style="display:grid;grid-template-columns:300px 1fr;gap:14px;height:100%">
      <div class="card" style="overflow:auto"><input id="tlF" placeholder="Find a tool…" style="width:100%"><div id="tlList" style="margin-top:8px"></div></div>
      <div class="card" style="overflow:auto" id="tlBody"><h1 class="page-title">🧰 Hebrew tools</h1><p class="muted">Pick a tool on the left. Every tool works offline.</p></div></div>`;
    this.list = await App.api("tools");
    $("#tlF", el).oninput = () => this.drawList();
    this.drawList();
  },
  drawList() {
    const f = ($("#tlF").value || "").toLowerCase();
    const cats = {};
    this.list.filter(t => !f || (t.name + t.desc + t.category).toLowerCase().includes(f)).forEach(t => (cats[t.category] = cats[t.category] || []).push(t));
    $("#tlList").innerHTML = `<p class="small muted">${this.list.length} tools</p>` + Object.entries(cats).map(([c, ts]) => `<details ${f ? "open" : ""}><summary style="cursor:pointer;font-weight:600;padding:4px 0">${esc(c)} <span class="small muted">(${ts.length})</span></summary>${ts.map(t => `<div class="list-item small" data-id="${t.id}">${esc(t.name)}</div>`).join("")}</details>`).join("");
    $$("#tlList [data-id]").forEach(x => x.onclick = () => this.open(x.dataset.id));
  },
  open(id) {
    const t = this.list.find(x => x.id === id); this.cur = t;
    const today = new Date().toISOString().slice(0, 10);
    const s = App.state.settings;
    const inp = i => {
      const def = i.default ?? (i.name === "lat" ? s.lat : i.name === "lon" ? s.lon : i.name === "tz" ? s.tz : "") ?? "";
      if (i.type === "text") return i.name === "text" ? `<textarea data-n="${i.name}" class="he-input" dir="auto" placeholder="${esc(i.label)}"></textarea>` : `<input type="text" data-n="${i.name}" dir="auto" placeholder="${esc(i.label)}">`;
      if (i.type === "number") return `<input type="number" step="any" data-n="${i.name}" value="${esc(def)}">`;
      if (i.type === "date") return `<input type="date" data-n="${i.name}" value="${today}">`;
      if (i.type === "bool") return `<input type="checkbox" data-n="${i.name}">`;
      if (i.type === "select") return `<select data-n="${i.name}">${i.options.map(o => `<option>${esc(o)}</option>`).join("")}</select>`;
    };
    $("#tlBody").innerHTML = `<div class="small muted">${esc(t.category)}</div><h1 class="page-title">${esc(t.name)}</h1><p>${esc(t.desc)}</p>
      <div class="col">${t.inputs.map(i => `<label class="col" style="gap:3px"><span class="small muted">${esc(i.label)}</span>${inp(i)}</label>`).join("")}</div>
      <div class="row" style="margin:10px 0"><button class="btn primary" id="tlRun">Run</button><span class="small muted">Ctrl+Enter</span><span class="spacer"></span><button class="btn small" id="tlCopy">Copy result</button><button class="btn small" id="tlNote">→ Notes</button></div>
      <div id="tlOut" class="card" style="min-height:60px"></div>`;
    $("#tlRun").onclick = () => this.run();
    $("#tlBody").onkeydown = e => { if (e.key === "Enter" && e.ctrlKey) this.run(); };
    $("#tlCopy").onclick = () => App.copy($("#tlOut").innerText, $("#tlOut").innerHTML);
    $("#tlNote").onclick = () => Notes.openWithHtml(t.name, $("#tlOut").innerHTML);
    const first = $("[data-n]", $("#tlBody")); if (first) first.focus();
    if (!t.inputs.length) this.run();
  },
  async run() {
    const args = {}; $$("#tlBody [data-n]").forEach(e => args[e.dataset.n] = e.type === "checkbox" ? e.checked : e.value);
    const r = (await App.api("tool_run", { id: this.cur.id, args })).result;
    $("#tlOut").innerHTML = this.fmt(r);
  },
  fmt(r) {
    if (r == null) return "";
    if (typeof r === "string") return `<div dir="auto" style="white-space:pre-wrap;font-size:18px;font-family:${isHeb(r) ? "var(--he-font)" : "inherit"}">${esc(r)}</div>`;
    if (r.html) return r.html;
    if (r.table) return `<table class="data">${r.headers && r.headers.some(Boolean) ? `<tr>${r.headers.map(h => `<th>${esc(h)}</th>`).join("")}</tr>` : ""}${r.table.map(row => `<tr>${row.map(c => `<td dir="auto" class="${isHeb(String(c)) ? "he" : ""}" style="${isHeb(String(c)) ? "font-size:17px" : ""}">${esc(c)}</td>`).join("")}</tr>`).join("")}</table>`;
    return `<pre>${esc(JSON.stringify(r, null, 1))}</pre>`;
  }
};
App.register("tools", { title: "Tools", icon: "🧰", render(el) { Tools.render(el); } });

const Cal = {
  date: new Date(),
  render(el) {
    el.innerHTML = `<div class="row"><h1 class="page-title" style="margin:0">📅 <span id="cT"></span> <small class="he" id="cHT" style="font-size:20px"></small></h1><span class="spacer"></span>
      <button class="btn" id="cP">‹</button><button class="btn" id="cTd">Today</button><button class="btn" id="cN">›</button>
      <button class="btn" id="cTools">Yahrzeit / birthday / molad…</button><button class="btn" id="cPrint">🖨</button></div><div id="cGrid" class="card print-target" style="margin-top:10px"></div>`;
    $("#cP", el).onclick = () => { this.date.setMonth(this.date.getMonth() - 1); this.draw(); };
    $("#cN", el).onclick = () => { this.date.setMonth(this.date.getMonth() + 1); this.draw(); };
    $("#cTd", el).onclick = () => { this.date = new Date(); this.draw(); };
    $("#cTools", el).onclick = () => { App.show("tools"); $("#tlF").value = "calendar"; Tools.drawList(); };
    $("#cPrint", el).onclick = () => { const g = $("#cGrid"); g.classList.add("print-area"); window.print(); setTimeout(() => g.classList.remove("print-area"), 400); };
    this.draw();
  },
  async draw() {
    const d = new Date(this.date.getFullYear(), this.date.getMonth(), 1, 12);
    const r = await App.api("month", { date: d.toISOString().slice(0, 10) });
    $("#cT").textContent = r.title; $("#cHT").textContent = r.heb_title;
    const today = new Date().toISOString().slice(0, 10);
    const weeks = []; for (let i = 0; i < 42; i += 7) weeks.push(r.days.slice(i, i + 7));
    $("#cGrid").innerHTML = `<table class="grid" style="width:100%;border-collapse:collapse"><tr>${["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Shabbos"].map(x => `<th>${x}</th>`).join("")}</tr>
      ${weeks.filter(w => w.some(x => x.in_month)).map(w => `<tr>${w.map(x => `<td style="${x.in_month ? "" : "opacity:.35"};${x.date === today ? "outline:2px solid var(--accent2)" : ""};height:96px">
        <div class="row"><b>${x.day}</b><span class="spacer"></span><span class="he" style="font-size:17px">${esc(x.heb_day)}${x.heb_first ? " " + esc(x.heb_month) : ""}</span></div>
        ${x.holidays.map(hh => `<div class="small" style="color:var(--accent2)">${esc(hh[0])}</div>`).join("")}
        ${x.parasha ? `<div class="small" style="color:var(--accent)">${esc(x.parasha)}</div>` : ""}<div class="small muted he" style="font-size:12px">${esc(x.daf)}</div></td>`).join("")}</tr>`).join("")}</table>`;
  }
};
App.register("calendar", { title: "Calendar", icon: "📅", render(el) { Cal.render(el); } });
