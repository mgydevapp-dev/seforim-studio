/* Gematria (18 methods; words, passages and multi-word phrases with the same value), Roshei/Sofei Teivos, ELS */
const Gematria = {
  render(el) {
    el.innerHTML = `<h1 class="page-title">🔢 Gematria <small>Type letters (or a number) — see every method, then find every place in your library with that value.</small></h1>
    <div class="grid g2">
      <div class="card"><div class="searchbox"><input id="gIn" class="he-input" placeholder="הקלד מילה או מספר — e.g. משיח or 358"><button class="btn primary" id="gGo">Find</button></div>
        <div class="row" style="margin-top:8px"><label>Method <select id="gM"></select></label><label class="small"><input type="checkbox" id="gPh"> also find phrases of <input type="number" id="gMin" value="2" min="2" max="8" style="width:46px">–<input type="number" id="gMax" value="4" min="2" max="10" style="width:46px"> words</label></div>
        <div class="row" style="margin-top:10px;align-items:flex-end"><div class="bigvalue" id="gVal">0</div><div class="muted" id="gWords" style="margin-bottom:10px"></div></div>
        <table class="data" id="gTable" style="margin-top:6px"></table></div>
      <div class="card"><b>Words in your library with this value</b> <span class="small muted" id="gWc"></span><div id="gList" class="row" style="margin-top:8px;max-height:260px;overflow:auto"></div>
        <div class="row" style="margin-top:8px"><button class="btn small" id="gAll">Show all passages containing these words</button><button class="btn small" id="gCopy">Copy list</button></div></div>
    </div>
    <div class="progress hidden" id="gProg" style="margin-top:12px"><div></div></div>
    <div id="gPhr"></div><div id="gRes" style="margin-top:12px"></div><div class="row" style="justify-content:center"><button class="btn hidden" id="gMore">Load more</button></div>`;
    const sel = $("#gM", el);
    App.api("gematria_value", { text: "" }).then(r => { Object.keys(r.methods).forEach(m => sel.add(new Option(m, m))); });
    $("#gIn", el).oninput = () => this.calc();
    $("#gIn", el).onkeydown = e => { if (e.key === "Enter") this.find(); };
    $("#gGo", el).onclick = () => this.find();
    sel.onchange = () => this.calc();
    $("#gAll", el).onclick = () => this.passages(0);
    $("#gMore", el).onclick = () => this.passages(this.off);
    $("#gCopy", el).onclick = () => App.copy((this.words || []).map(w => w.word).join(" "));
  },
  async calc() {
    const t = $("#gIn").value.trim();
    if (/^\d+$/.test(t)) { $("#gVal").textContent = t; $("#gTable").innerHTML = `<tr><td>Number</td><td>${App.heNum(+t)}</td></tr>`; $("#gWords").textContent = ""; return; }
    const r = await App.api("gematria_value", { text: t });
    $("#gVal").textContent = r.methods[$("#gM").value] ?? 0;
    $("#gWords").innerHTML = r.words.length > 1 ? r.words.map(w => `${esc(w[0])}=${w[1]}`).join(" + ") : "";
    $("#gTable").innerHTML = Object.entries(r.methods).map(([m, v]) => `<tr class="${m === $("#gM").value ? "sel" : ""}"><td>${esc(m)}</td><td style="text-align:right;font-weight:600">${v}</td></tr>`).join("");
  },
  async find() {
    await this.calc();
    const t = $("#gIn").value.trim(), m = $("#gM").value;
    const r = await App.api("gematria_words", /^\d+$/.test(t) ? { value: +t, method: m } : { text: t, method: m });
    this.value = r.value; this.words = r.words;
    $("#gWc").textContent = `= ${r.value} · ${r.words.length} words`;
    $("#gList").innerHTML = r.words.map(w => `<button class="btn he" style="font-size:18px;padding:3px 9px" data-w="${esc(w.word)}">${esc(w.word)} <span class="small muted">${w.freq}</span></button>`).join("") || "<span class='muted'>No single words with this value in the downloaded seforim.</span>";
    $$("#gList [data-w]").forEach(b => b.onclick = () => { App.show("search"); Search.run(b.dataset.w); });
    this.passages(0);
    $("#gPhr").innerHTML = "";
    if ($("#gPh").checked) this.phrases();
  },
  async passages(off) {
    if (!this.words || !this.words.length) { $("#gRes").innerHTML = ""; return; }
    const r = await App.api("gematria_passages", { words: this.words.map(w => w.word), offset: off, limit: 40 });
    const html = `${off ? "" : `<h2>${r.total.toLocaleString()} passages contain a word = ${this.value}</h2>`}` + r.results.map(x => Search.resultHtml(x)).join("");
    if (off) $("#gRes").insertAdjacentHTML("beforeend", html); else $("#gRes").innerHTML = html;
    this.off = off + r.results.length; $("#gMore").classList.toggle("hidden", this.off >= r.total);
    $("#gRes").onclick = e => { const a = e.target.closest("[data-open]"); if (a) { e.preventDefault(); Search.openResult(+a.dataset.open); } };
  },
  async phrases() {
    const pr = $("#gProg"); pr.classList.remove("hidden");
    const { job } = await App.api("gematria_phrases", { value: this.value, method: $("#gM").value, min_words: +$("#gMin").value, max_words: +$("#gMax").value });
    const res = await App.job(job, s => { $("div", pr).style.width = (s.total ? 100 * s.progress / s.total : 5) + "%"; });
    pr.classList.add("hidden");
    $("#gPhr").innerHTML = `<h2>Phrases (consecutive words) = ${this.value}: ${res.length}${res.length >= 500 ? "+" : ""}</h2>` + res.map(x => `<div class="result"><a class="ref" href="#" data-open="${x.id}">${esc(x.ref)}</a> <b class="he" style="font-size:18px">${esc(x.phrase)}</b><div class="he" style="font-size:18px">${x.he_html}</div></div>`).join("");
    $("#gPhr").onclick = e => { const a = e.target.closest("[data-open]"); if (a) { e.preventDefault(); Search.openResult(+a.dataset.open); } };
  }
};
App.register("gematria", { title: "Gematria", icon: "🔢", render(el) { Gematria.render(el); } });

const Roshei = {
  render(el) {
    el.innerHTML = `<h1 class="page-title">🔤 Roshei Teivos <small>Find every place where consecutive words start (or end) with your letters.</small></h1>
    <div class="card"><div class="searchbox"><input id="rtIn" class="he-input" placeholder="e.g. באה or רמבם or אמת"><button class="btn primary" id="rtGo">Find</button></div>
      <div class="row small" style="margin-top:8px"><label><input type="radio" name="rtm" value="roshei" checked> Roshei teivos (first letters)</label><label><input type="radio" name="rtm" value="sofei"> Sofei teivos (last letters)</label>
      <label>Scope <select id="rtCat"><option value="">All</option></select></label><span class="spacer"></span><button class="btn small" id="rtEls">ELS / Dilugim…</button></div></div>
    <div id="rtExp" style="margin-top:10px"></div><div id="rtRes"></div><div class="row" style="justify-content:center"><button class="btn hidden" id="rtMore">Load more</button></div>`;
    $("#rtIn", el).onkeydown = e => { if (e.key === "Enter") this.run(); };
    $("#rtGo", el).onclick = () => this.run();
    $("#rtMore", el).onclick = () => this.run(null, true);
    $("#rtEls", el).onclick = () => this.els();
    $("#rtRes", el).onclick = e => { const a = e.target.closest("[data-open]"); if (a) { e.preventDefault(); Search.openResult(+a.dataset.open); } };
  },
  onShow() { const s = $("#rtCat"); if (s.options.length < 2) for (const c of Search.cats()) s.add(new Option(c, c)); },
  async run(q, more) {
    if (q != null) $("#rtIn").value = q;
    const letters = $("#rtIn").value.trim(); if (!letters) return;
    if (!more) this.off = 0;
    const scope = $("#rtCat").value ? { categories: [$("#rtCat").value] } : {};
    $("#rtRes").innerHTML = more ? $("#rtRes").innerHTML : "<p class='muted'>Searching the whole library…</p>";
    const r = await App.api("roshei", { letters, mode: $("input[name=rtm]:checked").value, scope, offset: this.off, limit: 60 });
    if (!$("#rtRes")) return;  // the user went to another screen meanwhile
    if (!more) {
      const exp = await App.api("tool_run", { id: "expand_abbrev", args: { text: letters } });
      $("#rtExp").innerHTML = `<div class="card"><b>${r.total.toLocaleString()}${r.approx ? "+" : ""}</b> places in the library. ${typeof exp.result === "string" && !exp.result.startsWith("Not in") ? `<span class="he" style="font-size:18px">Dictionary: <b>${esc(exp.result)}</b></span>` : ""}</div>`;
    }
    const html = r.results.map(x => `<div class="result"><a class="ref" href="#" data-open="${x.id}">${esc(x.ref)}</a> ${x.phrases.map(p => `<span class="pill he" style="font-size:15px">${esc(p)}</span>`).join(" ")}
      <div class="cols"><div class="he">${x.he_html}</div><div class="en">${x.en_html}</div></div></div>`).join("");
    if (more) $("#rtRes").insertAdjacentHTML("beforeend", html); else $("#rtRes").innerHTML = html || "<p class='muted'>Not found.</p>";
    this.off += r.results.length; $("#rtMore").classList.toggle("hidden", !r.approx && this.off >= r.total);
  },
  async els() {
    const works = await App.api("lib_works");
    App.modal(`<h3>Equidistant letter sequences (Dilugim)</h3><div class="row"><input id="eW" class="he-input" placeholder="word e.g. תורה"><select id="eB">${works.map(w => `<option value="${w.id}">${esc(w.title)}</option>`).join("")}</select>
      <label>skip <input type="number" id="e1" value="2" style="width:60px"> – <input type="number" id="e2" value="100" style="width:70px"></label><button class="btn primary" id="eGo">Search</button></div><div id="eOut" style="margin-top:10px;max-height:55vh;overflow:auto"></div>`, m => {
      $("#eGo", m).onclick = async () => {
        $("#eOut", m).innerHTML = "<p class='muted'>Searching…</p>";
        const { job } = await App.api("els", { word: $("#eW", m).value, work_id: +$("#eB", m).value, min: +$("#e1", m).value, max: +$("#e2", m).value });
        const r = await App.job(job);
        $("#eOut", m).innerHTML = `<p><b>${r.length}</b> sequences</p><table class="data"><tr><th>Skip</th><th>Starts</th><th>Ends</th></tr>${r.map(x => `<tr><td>${x.skip}</td><td>${esc(x.start_ref)}</td><td>${esc(x.end_ref)}</td></tr>`).join("")}</table>`;
      };
    });
  }
};
App.register("roshei", { title: "Roshei Teivos", icon: "🔤", render(el) { Roshei.render(el); }, onShow() { Roshei.onShow(); } });
