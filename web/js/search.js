/* Search: Hebrew ⇄ English full text, boolean, phrase, wildcard, NEAR, root, prefixes, malei/chaser, fuzzy, regex,
   acronyms, scope filters, my-notes inclusion, cross-line phrases, compare two groups, history, export */
const Search = {
  offset: 0, last: null,
  cats() { return (Library.tree || []).map(n => n.name); },
  render(el) {
    const o = App.state.settings.search_opts || { prefixes: true, acronyms: true, notes: true };
    el.innerHTML = `<h1 class="page-title">🔎 Search <small>Type Hebrew or English — Hebrew finds the Hebrew text, English finds the translation; both are shown side by side.</small></h1>
    <div class="card">
      <div class="searchbox"><input id="sQ" placeholder='e.g.  אור   •   "יהי אור"   •   light   •   root:שמר   •   שבת NEAR/5 נר   •   מאימ*   •   אור -חשך'>
        <select id="sLang"><option value="auto">Auto</option><option value="he">Hebrew</option><option value="en">English</option></select><button class="btn primary" id="sGo">Search</button></div>
      <div class="opts row small" style="margin-top:8px">
        <label title="Also match ו ה ב כ ל מ ש in front"><input type="checkbox" id="oPre"> Prefixes (וה, ב, ל…)</label>
        <label title="Match with or without vav/yud"><input type="checkbox" id="oMc"> Malei / chaser</label>
        <label title="Allow one wrong/missing/extra letter"><input type="checkbox" id="oFz"> Fuzzy (typos)</label>
        <label title="רמב״ם also finds רבי משה בן מימון"><input type="checkbox" id="oAc"> Expand abbreviations</label>
        <label><input type="checkbox" id="oNotes"> Include my notes</label>
        <label title="Phrase split between two lines"><input type="checkbox" id="oCross"> Cross-line phrases</label>
        <label title="Regular expression on letters-only text"><input type="checkbox" id="oRx"> Regex</label>
        <span class="spacer"></span>
        <label>Sort <select id="sSort"><option value="book">Book order</option><option value="relevance">Relevance</option></select></label>
      </div>
      <div class="row small" style="margin-top:6px"><label>Scope</label><select id="sCat"><option value="">All categories</option></select>
        <input id="sBook" placeholder="Only in book… (optional)" style="width:180px"><input id="sAuthor" placeholder="Author (optional)" style="width:140px">
        <select id="sEra"><option value="">Any era</option>${["T", "A", "GN", "RI", "AH", "CO"].map((e, i) => `<option value="${e}">${["Tannaim", "Amoraim", "Geonim", "Rishonim", "Acharonim", "Contemporary"][i]}</option>`).join("")}</select>
        <span class="spacer"></span><button class="btn small" id="sCmp">⚖ Compare two groups</button><button class="btn small" id="sHist">🕘 History</button><button class="btn small" id="sHelp">? Syntax</button></div>
    </div>
    <div class="row" style="margin:10px 0"><b id="sCount"></b><span class="muted small" id="sInfo"></span><span class="spacer"></span>
      <button class="btn small hidden" id="sHeEq" title="Show the Hebrew words that translate your English term">🔁 Hebrew equivalents</button>
      <button class="btn small hidden" id="sCloud">☁ Word cloud</button><button class="btn small hidden" id="sExp">⤓ Export results</button></div>
    <div id="sExtra"></div><div id="sRes"></div><div class="row" style="justify-content:center;margin:14px"><button class="btn hidden" id="sMore">Load more</button></div>`;
    $("#oPre", el).checked = o.prefixes !== false; $("#oMc", el).checked = !!o.malei_chaser; $("#oFz", el).checked = !!o.fuzzy; $("#oAc", el).checked = o.acronyms !== false;
    $("#oNotes", el).checked = o.notes !== false; $("#oCross", el).checked = !!o.cross_line; $("#oRx", el).checked = !!o.regex;
    $("#sQ", el).onkeydown = e => { if (e.key === "Enter") this.run(); };
    $("#sGo", el).onclick = () => this.run();
    $("#sMore", el).onclick = () => this.run(null, true);
    $("#sHelp", el).onclick = () => this.help();
    $("#sHist", el).onclick = () => this.history();
    $("#sCmp", el).onclick = () => this.compare();
    $("#sExp", el).onclick = () => this.exportResults();
    $("#sCloud", el).onclick = () => { App.show("analysis"); Analysis.cloud($("#sQ").value); };
    $("#sHeEq", el).onclick = () => this.hebrewEquivalents();
    $("#sRes", el).onclick = e => { const r = e.target.closest("[data-open]"); if (r) { e.preventDefault(); this.openResult(+r.dataset.open); } };
  },
  onShow() {
    const s = $("#sCat"); if (s && s.options.length < 2) for (const c of this.cats()) s.add(new Option(c, c));
    $("#sQ").focus();
  },
  opts() { const v = id => $(id).checked; return { prefixes: v("#oPre"), malei_chaser: v("#oMc"), fuzzy: v("#oFz"), acronyms: v("#oAc"), notes: v("#oNotes"), cross_line: v("#oCross"), regex: v("#oRx") }; },
  async scope() {
    const s = {}; if ($("#sCat").value) s.categories = [$("#sCat").value];
    const b = $("#sBook").value.trim();
    if (b) { const w = (await App.api("lib_works")).filter(x => x.title.toLowerCase().includes(b.toLowerCase()) || (x.he_title || "").includes(b)); if (w.length) s.works = w.map(x => x.id); }
    if ($("#sAuthor").value.trim()) s.author = $("#sAuthor").value.trim();
    if ($("#sEra").value) s.era = [$("#sEra").value];
    return s;
  },
  async run(q, more) {
    if (!$("#sQ")) { App.show("search"); }
    if (q != null) $("#sQ").value = q;
    q = $("#sQ").value.trim(); if (!q) return;
    const opts = this.opts(); App.setSetting("search_opts", opts);
    if (!more) { this.offset = 0; $("#sRes").innerHTML = `<p class="muted">Searching…</p>`; $("#sExtra").innerHTML = ""; }
    const r = await App.api("search", { q, lang: $("#sLang").value, opts, scope: await this.scope(), offset: this.offset, limit: 50, sort: $("#sSort").value, unlocked: App.state.unlocked });
    this.last = { q, r, lang: r.lang };
    if (r.error) { $("#sRes").innerHTML = `<p class="muted">${esc(r.error)}</p>`; return; }
    $("#sCount").textContent = `${r.total.toLocaleString()} result${r.total === 1 ? "" : "s"}${r.approx ? "+" : ""}`;
    $("#sInfo").textContent = ` · ${r.lang === "he" ? "Hebrew" : "English"} search${r.ms != null ? ` · ${r.ms} ms` : ""}${r.terms && r.terms.length > 1 ? " · matching: " + r.terms.slice(0, 12).join(", ") + (r.terms.length > 12 ? "…" : "") : ""}`;
    const html = r.results.map(x => this.resultHtml(x)).join("");
    if (!more) {
      let extra = "";
      if (r.notes && r.notes.length) extra += `<div class="card" style="margin-bottom:10px"><b>📝 In your notes (${r.notes.length})</b>${r.notes.map(n => `<div class="list-item" data-kind="${n.kind}" data-id="${n.id}" data-pid="${n.passage_id || ""}"><span class="pill">${n.kind}</span> <b>${esc(n.ref || "")}</b> <span class="small">${esc(String(n.text || "").replace(/<[^>]+>/g, " ").slice(0, 160))}</span></div>`).join("")}</div>`;
      if (r.cross_line && r.cross_line.length) extra += `<div class="card" style="margin-bottom:10px"><b>↩ Phrase split across lines (${r.cross_line.length})</b>${r.cross_line.map(c => `<div class="list-item" data-open="${c.id}">${esc(c.from)} → ${esc(c.to)}</div>`).join("")}</div>`;
      $("#sExtra").innerHTML = extra;
      $$("#sExtra [data-kind]").forEach(x => x.onclick = () => { if (x.dataset.kind === "note" && x.dataset.pid) this.openResult(+x.dataset.pid); else if (x.dataset.kind === "doc") Notes.openDoc(+x.dataset.id); else Sheets.open(+x.dataset.id); });
      $$("#sExtra [data-open]").forEach(x => x.onclick = () => this.openResult(+x.dataset.open));
      $("#sRes").innerHTML = html || `<p class="muted">No results. Try turning on Prefixes, Malei/chaser or Fuzzy, or download more seforim.</p>`;
    } else $("#sRes").insertAdjacentHTML("beforeend", html);
    this.offset += r.results.length;
    $("#sMore").classList.toggle("hidden", this.offset >= r.total);
    ["#sExp", "#sCloud"].forEach(b => $(b).classList.toggle("hidden", !r.total));
    $("#sHeEq").classList.toggle("hidden", !(r.lang === "en" && r.total));
  },
  resultHtml(x) {
    return `<div class="result" data-ref="${esc(x.ref)}"><a class="ref" href="#" data-open="${x.id}">${esc(x.ref)}</a> <span class="he-name">${esc(App.heRef(x.ref, x.he_title, x.title))}</span> <span class="small muted">· ${esc((x.category_path || "").split(" > ")[0])}</span>
      <div class="cols"><div class="he">${x.he_html || ""}</div><div class="en">${x.en_html || ""}</div></div></div>`;
  },
  async openResult(id) { const p = await App.api("passage", { id }); Library.open(p.work_id, p.node, p.chapter, p.id); },
  async hebrewEquivalents() {
    const r = await App.api("cross_lingual", { q: $("#sQ").value });
    $("#sExtra").innerHTML = `<div class="card"><b>🔁 Hebrew words most tied to “${esc($("#sQ").value)}”</b><div class="row" style="margin-top:6px">${r.map(w => `<button class="btn he" style="font-size:18px" data-w="${esc(w[0])}">${esc(w[0])} <span class="small muted">${w[1]}</span></button>`).join("") || "<span class='muted'>None found</span>"}</div><p class="small muted">Click a word to search it in Hebrew.</p></div>`;
    $$("#sExtra [data-w]").forEach(b => b.onclick = () => { $("#sLang").value = "auto"; this.run(b.dataset.w); });
  },
  help() {
    App.modal(`<h3>Search syntax</h3><table class="data">
      <tr><td><code>אור חשך</code></td><td>both words (AND)</td></tr><tr><td><code>אור OR חשך</code> / <code>או</code></td><td>either word</td></tr>
      <tr><td><code>אור -חשך</code> / <code>NOT</code></td><td>exclude a word</td></tr><tr><td><code>"יהי אור"</code></td><td>exact phrase</td></tr>
      <tr><td><code>מאימ*</code></td><td>wildcard: any ending</td></tr><tr><td><code>א?ר</code></td><td>one unknown letter</td></tr>
      <tr><td><code>שבת NEAR/5 נר</code></td><td>within 5 words of each other</td></tr><tr><td><code>root:שמר</code> / <code>שורש:שמר</code></td><td>all words from the root (שומר, ישמרו, משמרת…)</td></tr>
      <tr><td><code>dark*</code>, <code>"seventh day"</code></td><td>English works the same way (with word stemming)</td></tr>
      <tr><td>Regex box</td><td><code>^ויאמר</code>, <code>ה.ה</code> — letters-only text, no nikud</td></tr></table>
      <p class="small muted">Nikud and ta'amim are ignored automatically. Prefixes adds ו ה ב כ ל מ ש. Malei/chaser ignores ו/י spelling. Fuzzy allows one typo. Scope limits by category, book, author or era.</p>
      <div class="row" style="justify-content:flex-end"><button class="btn" data-close>Close</button></div>`);
  },
  async history() {
    const h = await App.api("search_history");
    App.modal(`<h3>🕘 Search history</h3><div style="max-height:60vh;overflow:auto">${h.map(x => `<div class="list-item" data-q="${esc(x.query)}" data-k="${x.kind}"><span class="pill">${x.kind}</span> <b>${esc(x.query)}</b> <span class="small muted">${x.hits} hits · ${esc(x.ts)}</span></div>`).join("") || "<p class='muted'>Empty</p>"}</div><div class="row" style="justify-content:flex-end"><button class="btn" data-close>Close</button></div>`, m => {
      $$("[data-q]", m).forEach(x => x.onclick = () => { App.closeModal(); if (x.dataset.k === "roshei") { App.show("roshei"); Roshei.run(x.dataset.q); } else this.run(x.dataset.q); });
    });
  },
  compare() {
    const cats = this.cats();
    App.modal(`<h3>⚖ Compare how two groups of books use a term</h3><input id="cQ" style="width:100%" value="${esc($("#sQ").value)}" placeholder="term or phrase">
      <div class="row" style="margin-top:8px"><label>Group A <select id="cA">${cats.map(c => `<option>${esc(c)}</option>`).join("")}</select></label><label>Group B <select id="cB">${cats.map((c, i) => `<option ${i === 1 ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></label>
      <button class="btn primary" id="cGo">Compare</button></div><div id="cOut" class="grid g2" style="margin-top:10px"></div>`, m => {
      $("#cGo", m).onclick = async () => {
        const r = await App.api("search_compare", { q: $("#cQ", m).value, scope_a: { categories: [$("#cA", m).value] }, scope_b: { categories: [$("#cB", m).value] }, opts: this.opts() });
        const col = (name, x) => `<div><h2>${esc(name)} — ${x.total} results</h2>${x.results.map(y => this.resultHtml(y)).join("")}</div>`;
        $("#cOut", m).innerHTML = col($("#cA", m).value, r.a) + col($("#cB", m).value, r.b);
        $("#cOut", m).onclick = e => { const a = e.target.closest("[data-open]"); if (a) { e.preventDefault(); App.closeModal(); this.openResult(+a.dataset.open); } };
      };
    });
  },
  async exportResults() {
    const ids = [];
    let off = 0; const q = $("#sQ").value;
    while (off < Math.min(this.last.r.total, 2000)) { const r = await App.api("search", { q, lang: $("#sLang").value, opts: this.opts(), scope: await this.scope(), offset: off, limit: 200 }); ids.push(...r.results.map(x => x.id)); off += 200; if (!r.results.length) break; }
    App.modal(`<h3>Export ${ids.length} results</h3><div class="row">${["csv", "docx", "html", "txt", "json", "tei"].map(f => `<button class="btn" data-f="${f}">${f.toUpperCase()}</button>`).join("")}</div><div class="row" style="justify-content:flex-end;margin-top:10px"><button class="btn" data-close>Close</button></div>`, m => {
      m.onclick = async e => { const f = e.target.dataset.f; if (!f) return; const r = await App.api("export_passages", { ids, format: f, title: "search " + q }); App.download(r.url); };
    });
  }
};
App.register("search", { title: "Search", icon: "🔎", render(el) { Search.render(el); }, onShow() { Search.onShow(); } });
