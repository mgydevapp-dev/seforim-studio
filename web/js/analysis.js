/* Research analysis: book statistics, word cloud, co-occurrence, category/era heatmap, citation network graph,
   author timeline, places map, phrase comparison grid, reference tree */
const Analysis = {
  render(el) {
    el.innerHTML = `<h1 class="page-title">📊 Analysis</h1>
    <div class="tabs" id="anTabs">${[["stats", "Book statistics"], ["cloud", "Word cloud"], ["co", "Co-occurrence"], ["dist", "Spread by category & era"], ["net", "Citation network"],
      ["time", "Author timeline"], ["map", "Places map"], ["grid", "Compare passages"], ["tree", "Reference tree"]].map(([k, t]) => `<button data-t="${k}">${t}</button>`).join("")}</div><div id="anBody"></div>`;
    $$("#anTabs button", el).forEach(b => b.onclick = () => this.tab(b.dataset.t));
    this.tab("stats");
  },
  tab(t) { $$("#anTabs button").forEach(b => b.classList.toggle("active", b.dataset.t === t)); return this["t_" + t]($("#anBody")); },
  async workSelect() { const w = await App.api("lib_works"); return `<select id="anW">${w.map(x => `<option value="${x.id}">${esc(x.title)} ${x.he_title ? "— " + esc(x.he_title) : ""}</option>`).join("")}</select>`; },
  async t_stats(el) {
    el.innerHTML = `<div class="row">${await this.workSelect()}<button class="btn primary" id="anGo">Analyze</button></div><div id="anOut"></div>`;
    $("#anGo").onclick = () => this.workStats(+$("#anW").value);
  },
  async workStats(id) {
    if (!$("#anW") || !$("#anOut")) { await this.tab("stats"); }
    $("#anW").value = id;
    const s = await App.api("work_stats", { work_id: id });
    const maxL = Math.max(...s.letter_freq.map(x => x[1]), 1);
    $("#anOut").innerHTML = `<div class="kpi" style="margin:12px 0">${[["Passages", s.passages], ["Hebrew words", s.hebrew_words], ["Unique words", s.unique_words], ["Letters", s.letters], ["English words", s.english_words], ["Avg. word length", s.avg_word_len], ["Vocabulary density", s.lexical_density]].map(([k, v]) => `<div class="card stat"><b>${Number(v).toLocaleString()}</b><span class="small muted">${k}</span></div>`).join("")}</div>
      <div class="grid g2"><div class="card"><b>Letter frequency</b>${s.letter_freq.map(([l, n]) => `<div class="row"><span class="he" style="width:24px;font-size:18px">${l}</span><div class="bar" style="width:${100 * n / maxL}%"></div><span class="small">${n}</span></div>`).join("")}</div>
      <div class="card"><b>Most common words</b><div class="row" style="margin-top:6px">${s.top_words.map(([w, n]) => `<span class="pill he" style="font-size:${14 + 14 * n / s.top_words[0][1]}px">${esc(w)} <small>${n}</small></span>`).join(" ")}</div></div></div>`;
  },
  t_cloud(el) {
    el.innerHTML = `<div class="searchbox"><input id="clQ" placeholder="search term — shows the words that appear most around it"><button class="btn primary" id="clGo">Build cloud</button></div><div id="clOut" class="card" style="margin-top:12px;min-height:200px;text-align:center"></div>`;
    $("#clGo").onclick = () => this.cloud($("#clQ").value);
  },
  async cloud(q) {
    if (!$("#clQ")) this.tab("cloud");
    $("#clQ").value = q;
    const words = await App.api("word_cloud", { q, lang: "auto" });
    const max = words[0] ? words[0][1] : 1;
    $("#clOut").innerHTML = words.map(([w, n], i) => `<span style="display:inline-block;margin:4px 8px;font-size:${14 + 30 * n / max}px;color:hsl(${(i * 47) % 360},45%,${App.state.settings.theme === "dark" ? 70 : 35}%);cursor:pointer" class="${isHeb(w) ? "he" : ""}" data-w="${esc(w)}">${esc(w)}</span>`).join("") || "<p class='muted'>No results</p>";
    $$("#clOut [data-w]").forEach(s => s.onclick = () => { App.show("search"); Search.run(s.dataset.w); });
  },
  t_co(el) {
    el.innerHTML = `<div class="row"><input id="coA" class="he-input" placeholder="word A e.g. שבת"><input id="coB" class="he-input" placeholder="word B e.g. נר"><button class="btn primary" id="coGo">Analyze</button></div><div id="coOut" style="margin-top:12px"></div>`;
    $("#coGo").onclick = async () => {
      const r = await App.api("cooccurrence", { a: $("#coA").value, b: $("#coB").value });
      $("#coOut").innerHTML = `<div class="kpi">${[["Same passage", r.same_passage], ["Chapters with A", r.chapters_a], ["Chapters with B", r.chapters_b], ["Same chapter", r.same_chapter], ["Association (Jaccard)", r.jaccard]].map(([k, v]) => `<div class="card stat"><b>${v}</b><span class="small muted">${k}</span></div>`).join("")}</div>
        <div class="card" style="margin-top:10px"><b>Where they meet</b>${r.by_work.map(([t, n]) => `<div class="row"><span style="width:240px">${esc(t)}</span><div class="bar" style="width:${n * 100 / (r.by_work[0][1] || 1)}%"></div><span class="small">${n}</span></div>`).join("") || "<p class='muted'>Never in the same chapter.</p>"}</div>`;
    };
  },
  t_dist(el) {
    el.innerHTML = `<div class="searchbox"><input id="dQ" placeholder="term — see which categories & eras use it most"><button class="btn primary" id="dGo">Show</button></div><div id="dOut" class="grid g2" style="margin-top:12px"></div>`;
    $("#dGo").onclick = async () => {
      const r = await App.api("histogram", { q: $("#dQ").value });
      const block = (title, rows, key) => { const m = Math.max(1, ...rows.map(x => x.n)); return `<div class="card"><b>${title}</b>${rows.map(x => `<div class="row"><span style="width:150px">${esc(x[key])}</span><div class="bar" style="width:${70 * x.n / m}%;opacity:${.35 + .65 * x.n / m}"></div><span class="small">${x.n}</span></div>`).join("") || "<p class='muted'>none</p>"}</div>`; };
      $("#dOut").innerHTML = block("By category", r.categories, "cat") + block("By era (heat)", r.eras, "era");
    };
  },
  async t_net(el) {
    el.innerHTML = `<p class="muted small">Which seforim reference each other most (from the cross-reference pack). Drag nodes to rearrange.</p><svg id="netSvg" width="100%" height="560" class="card"></svg>`;
    const edges = await App.api("network", { limit: 50 });
    if (!$("#netSvg")) return;
    if (!edges.length) { el.innerHTML += "<p class='muted'>No cross-references imported yet (Settings → Library → include cross-references).</p>"; return; }
    const names = [...new Set(edges.flatMap(e => [e.a, e.b]))];
    const W = $("#netSvg").clientWidth || 900, H = 560;
    const nodes = names.map((n, i) => ({ n, x: W / 2 + 220 * Math.cos(i * 2 * Math.PI / names.length), y: H / 2 + 220 * Math.sin(i * 2 * Math.PI / names.length), vx: 0, vy: 0 }));
    const idx = Object.fromEntries(names.map((n, i) => [n, i]));
    const maxN = Math.max(...edges.map(e => e.n));
    for (let it = 0; it < 300; it++) {
      for (const a of nodes) for (const b of nodes) if (a !== b) { const dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy + 1; a.vx += 900 * dx / d2; a.vy += 900 * dy / d2; }
      for (const e of edges) { const a = nodes[idx[e.a]], b = nodes[idx[e.b]]; const dx = b.x - a.x, dy = b.y - a.y; a.vx += dx * .01; a.vy += dy * .01; b.vx -= dx * .01; b.vy -= dy * .01; }
      for (const a of nodes) { a.vx += (W / 2 - a.x) * .005; a.vy += (H / 2 - a.y) * .005; a.x = Math.max(60, Math.min(W - 60, a.x + a.vx * .5)); a.y = Math.max(20, Math.min(H - 20, a.y + a.vy * .5)); a.vx *= .5; a.vy *= .5; }
    }
    const svg = $("#netSvg");
    const draw = () => svg.innerHTML = edges.map(e => { const a = nodes[idx[e.a]], b = nodes[idx[e.b]]; return `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="var(--accent2)" stroke-opacity=".5" stroke-width="${1 + 6 * e.n / maxN}"><title>${esc(e.a)} ↔ ${esc(e.b)}: ${e.n}</title></line>`; }).join("")
      + nodes.map((a, i) => `<g data-i="${i}" style="cursor:move"><circle cx="${a.x}" cy="${a.y}" r="7" fill="var(--accent)"/><text x="${a.x + 10}" y="${a.y + 4}" font-size="12">${esc(a.n)}</text></g>`).join("");
    draw();
    let drag = null;
    svg.onmousedown = e => { const g = e.target.closest("g[data-i]"); if (g) drag = nodes[+g.dataset.i]; };
    svg.onmousemove = e => { if (!drag) return; const r = svg.getBoundingClientRect(); drag.x = e.clientX - r.left; drag.y = e.clientY - r.top; draw(); };
    svg.onmouseup = () => drag = null;
  },
  async t_time(el) {
    const r = await App.api("timeline");
    const eras = r.eras, minY = -1300, maxY = 2030, W = 1000;
    const x = y => 20 + (W - 40) * (y - minY) / (maxY - minY);
    el.innerHTML = `<div class="card" style="overflow:auto"><svg width="${W}" height="${120 + r.works.length * 16}">
      ${eras.map((e, i) => `<rect x="${x(e[1])}" y="10" width="${x(e[2]) - x(e[1])}" height="30" fill="hsl(${i * 36},45%,60%)" opacity=".5"/><text x="${x(e[1]) + 3}" y="30" font-size="11">${esc(e[0])}</text>`).join("")}
      ${[-1000, -500, 0, 500, 1000, 1500, 2000].map(y => `<line x1="${x(y)}" x2="${x(y)}" y1="40" y2="${80 + r.works.length * 16}" stroke="var(--line)"/><text x="${x(y) + 2}" y="54" font-size="10">${Math.abs(y)}${y < 0 ? " BCE" : ""}</text>`).join("")}
      ${r.works.map((w, i) => `<circle cx="${x(w.year)}" cy="${72 + i * 16}" r="4" fill="var(--accent)"/><text x="${x(w.year) + 8}" y="${76 + i * 16}" font-size="11">${esc(w.title)} (${w.year}${w.authors ? ", " + esc(w.authors) : ""})</text>`).join("")}
    </svg>${r.works.length ? "" : "<p class='muted'>Author dates come with the downloaded author/date info (Settings → Library). Era bands are shown for reference.</p>"}</div>`;
  },
  async t_map(el) {
    const r = await App.api("reference_data");
    const P = r.places, lat = [27, 38], lon = [28, 50], W = 900, H = 620;
    const px = p => [(p[3] - lon[0]) / (lon[1] - lon[0]) * W, H - (p[2] - lat[0]) / (lat[1] - lat[0]) * H];
    el.innerHTML = `<div class="grid" style="grid-template-columns:1fr 300px"><div class="card"><svg width="100%" viewBox="0 0 ${W} ${H}" style="background:linear-gradient(#dbeafe,#e8f1e2)">
      <path d="M ${px([0, 0, 31.3, 34.2])} L ${px([0, 0, 33.1, 35.1])} L ${px([0, 0, 36.2, 35.8])}" stroke="#7aa" fill="none" stroke-width="2"/>
      ${P.map(p => { const [a, b] = px(p); return `<g><circle cx="${a}" cy="${b}" r="5" fill="#b8892b"/><text x="${a + 7}" y="${b + 4}" font-size="12">${esc(p[0])}</text></g>`; }).join("")}
      ${[30, 32, 34, 36].map(l => `<text x="4" y="${H - (l - lat[0]) / (lat[1] - lat[0]) * H}" font-size="10" fill="#678">${l}°N</text>`).join("")}</svg>
      <p class="small muted">Schematic coordinate map (offline). Coordinates are approximate traditional identifications.</p></div>
      <div class="card" style="max-height:640px;overflow:auto">${P.map(p => `<div class="list-item"><b>${esc(p[0])}</b> <span class="he" style="font-size:16px">${esc(p[1])}</span><div class="small muted">${p[2]}, ${p[3]} · <a href="#" data-s="${esc(p[1])}">search texts</a></div></div>`).join("")}</div></div>`;
    $$("[data-s]", el).forEach(a => a.onclick = e => { e.preventDefault(); App.show("search"); Search.run(a.dataset.s); });
  },
  t_grid(el) {
    el.innerHTML = `<p class="muted small">Place the same verse or phrase from several seforim / versions side by side (one reference per line, up to 10).</p>
      <textarea id="grRefs" placeholder="Genesis 1:1&#10;Rashi on Genesis 1:1:1&#10;Onkelos Genesis 1:1"></textarea><button class="btn primary" id="grGo">Compare</button><div id="grOut" style="margin-top:12px"></div>`;
    $("#grGo").onclick = async () => {
      const refs = $("#grRefs").value.split("\n").map(s => s.trim()).filter(Boolean).slice(0, 10);
      const rows = await App.api("compare_refs", { refs });
      const words = rows.map(r => r ? (r.he || "").replace(NIKUD_ALL, "").split(/\s+/) : []);
      const common = new Set(words[0] || []);
      $("#grOut").innerHTML = `<table class="data">${rows.map((r, i) => `<tr><th style="width:200px">${esc(refs[i])}</th><td class="he" style="font-size:18px">${r ? words[i].map(w => common.has(w) || i === 0 ? esc(w) : `<mark>${esc(w)}</mark>`).join(" ") : "<span class='muted'>not in library</span>"}</td></tr>`).join("")}</table><p class="small muted">Highlighted = words that differ from the first line.</p>`;
    };
  },
  t_tree(el) {
    el.innerHTML = `<div class="row"><input id="trRef" placeholder="Reference e.g. Genesis 1:1"><label>Depth <select id="trD"><option>1</option><option selected>2</option><option>3</option></select></label><button class="btn primary" id="trGo">Build tree</button></div><div id="trOut" class="card" style="margin-top:12px"></div>`;
    $("#trGo").onclick = async () => {
      const seen = new Set();
      const build = async (ref, d) => {
        if (d === 0 || seen.has(ref)) return "";
        seen.add(ref);
        const gs = await App.api("connections", { ref });
        const kids = [];
        for (const g of gs.slice(0, 12)) for (const i of g.items.slice(0, 4)) kids.push(`<li><b>${esc(i.ref)}</b> <span class="small muted">${esc(g.title)} · ${esc(i.type || "")}</span>${await build(i.ref, d - 1)}</li>`);
        return kids.length ? `<ul>${kids.join("")}</ul>` : "";
      };
      const r = $("#trRef").value.trim();
      $("#trOut").innerHTML = `<b>${esc(r)}</b>` + (await build(r, +$("#trD").value) || "<p class='muted'>No references found.</p>");
    };
  }
};
App.register("analysis", { title: "Analysis", icon: "📊", render(el) { Analysis.render(el); } });
