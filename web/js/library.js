/* Library: catalog tree, multi-tab reader, TOC, view modes, nikud toggle, commentary pane with sync, Daf layout,
   annotations (notes, highlights, tags, bookmarks, links), copy with citation, export, print */
const NIKUD_ALL = /[֑-ֽֿ-ׂׄ-ׇ]/g, TAAMIM = /[֑-ֽ֯׀׃׆]/g;
const Library = {
  tabs: [], activeIdx: -1, tree: null, imported: new Set(), favorites: new Set(), hidden: new Set(), selected: null,
  view: { mode: "side", nikud: "full", comm: true, sync: true, infinite: false },

  render(el) {
    Object.assign(this.view, App.state.settings.reader_view || {});
    el.innerHTML = `<div class="lib-wrap">
      <aside class="lib-side"><div class="side-head">
        <input id="libFilter" placeholder="Filter titles (English or עברית)…">
        <div class="row small"><label><input type="checkbox" id="libDl"> Downloaded only</label><label><input type="checkbox" id="libHid"> Show hidden</label></div>
      </div><div id="libHealth"></div><div class="tree" id="libTree"><p class="muted" style="padding:10px">Loading catalog…</p></div></aside>
      <div class="reader-area">
        <div class="book-tabs" id="bookTabs"></div>
        <div class="reader-toolbar" id="rTool">
          <button class="btn small" id="rPrev" title="Previous chapter (←)">‹ Prev</button><button class="btn small" id="rNext" title="Next chapter (→)">Next ›</button>
          <select id="rMode" title="Layout"><option value="side">Hebrew | English</option><option value="stacked">Stacked</option><option value="he">Hebrew only</option><option value="en">English only</option><option value="daf">Daf layout</option></select>
          <select id="rNikud" title="Vowels"><option value="full">Nikud + ta'amim</option><option value="nikud">Nikud only</option><option value="none">No nikud</option></select>
          <button class="btn small" id="rSmall" title="Smaller text">A−</button><button class="btn small" id="rBig" title="Bigger text">A+</button>
          <label class="small" title="Text margins">↔ <input type="range" id="rMargin" min="0" max="220" style="width:80px"></label>
          <label class="small"><input type="checkbox" id="rInf"> Infinite scroll</label>
          <label class="small"><input type="checkbox" id="rComm"> Commentary</label><label class="small"><input type="checkbox" id="rSync"> Sync</label>
          <span class="spacer"></span>
          <input id="rFind" placeholder="Find in chapter" style="width:130px">
          <button class="btn small" id="rBm" title="Bookmark this chapter">🔖</button>
          <button class="btn small" id="rExport" title="Export / print">⤓</button>
        </div>
        <div class="reader-body">
          <div class="toc" id="rToc"></div>
          <div class="text-pane" id="rText"><div class="muted" style="padding:40px;text-align:center">Choose a sefer from the list on the left.<br><br>
            <span class="small">Grey titles are in the catalog but not downloaded yet — click one to download it once (needs internet that one time).</span></div></div>
          <div class="divider" id="rDiv"></div>
          <div class="comm-pane" id="rComm2"><p class="muted small">Click a passage (or scroll with Sync on) to see its commentaries and cross-references.</p></div>
        </div>
      </div></div>`;
    $("#libFilter", el).oninput = () => this.drawTree();
    $("#libDl", el).onchange = $("#libHid", el).onchange = () => this.drawTree();
    $("#rPrev", el).onclick = () => this.step(-1); $("#rNext", el).onclick = () => this.step(1);
    const v = this.view;
    $("#rMode", el).value = v.mode; $("#rNikud", el).value = v.nikud; $("#rComm", el).checked = v.comm; $("#rSync", el).checked = v.sync; $("#rInf", el).checked = v.infinite;
    $("#rMargin", el).value = App.state.settings.read_margin ?? 48;
    $("#rMode", el).onchange = e => { v.mode = e.target.value; this.saveView(); this.redraw(); };
    $("#rNikud", el).onchange = e => { v.nikud = e.target.value; this.saveView(); this.redraw(); };
    $("#rComm", el).onchange = e => { v.comm = e.target.checked; this.saveView(); this.layoutPanes(); };
    $("#rSync", el).onchange = e => { v.sync = e.target.checked; this.saveView(); };
    $("#rInf", el).onchange = e => { v.infinite = e.target.checked; this.saveView(); const t = this.tab(); if (t) this.loadChapter(); };
    $("#rSmall", el).onclick = () => this.fontStep(-2); $("#rBig", el).onclick = () => this.fontStep(2);
    $("#rMargin", el).oninput = e => { document.documentElement.style.setProperty("--read-margin", e.target.value + "px"); App.setSetting("read_margin", +e.target.value); };
    $("#rFind", el).oninput = e => this.find(e.target.value);
    $("#rBm", el).onclick = () => { const t = this.tab(); if (t && t.passages[0]) this.bookmark(t.passages[0]); };
    $("#rExport", el).onclick = () => this.exportDialog();
    this.dragDivider($("#rDiv", el), $("#rComm2", el));
    $("#rText", el).addEventListener("scroll", () => this.onScroll());
    document.addEventListener("keydown", e => {
      if (App.current !== "library" || App.isTypingTarget(e.target)) return;
      if (e.key === "ArrowLeft" || e.key === "PageDown") { this.step(1); e.preventDefault(); }
      if (e.key === "ArrowRight" || e.key === "PageUp") { this.step(-1); e.preventDefault(); }
    });
    this.layoutPanes();
    setInterval(() => this.logReading(), 60000);
  },
  saveView() { App.setSetting("reader_view", this.view); },
  fontStep(d) { const s = (App.state.settings.he_size || 22) + d; App.setSetting("he_size", s); App.setSetting("en_size", Math.round(s * 0.73)); App.applySettings(); },
  layoutPanes() { const show = this.view.comm && this.view.mode !== "daf"; $("#rComm2").classList.toggle("hidden", !show); $("#rDiv").classList.toggle("hidden", !show); },
  dragDivider(div, pane) {
    let x0 = null, w0 = 0;
    div.onmousedown = e => { x0 = e.clientX; w0 = pane.offsetWidth; e.preventDefault(); };
    document.addEventListener("mousemove", e => { if (x0 != null) pane.style.width = Math.max(180, w0 - (e.clientX - x0)) + "px"; });
    document.addEventListener("mouseup", () => x0 = null);
  },

  /* ---------- catalog tree ---------- */
  async loadTree() {
    const r = await App.api("catalog_tree");
    this.tree = r.tree; this.imported = new Set(r.imported); this.favorites = new Set(r.favorites); this.hidden = new Set(r.hidden);
    this.userWorks = (await App.api("lib_works")).filter(w => w.source === "user" || !this.inCatalog(w.id));
    this.drawTree();
    this.drawHealth();
  },
  /* ---------- "is the whole library installed?" ---------- */
  async drawHealth() {
    const el = $("#libHealth"); if (!el) return;
    const h = await App.api("library_health").catch(() => null);
    if (!h || !h.total || h.have >= h.total * 0.95) { el.innerHTML = ""; return; }
    const st = h.install || {}, miss = h.rows.filter(r => r.have < r.total);
    const running = st.state === "running";
    el.innerHTML = `<div class="lib-health">
      <b>📚 ${h.have.toLocaleString()} of ${h.total.toLocaleString()} seforim are installed</b>
      <div class="small">Missing: ${miss.map(r => `${esc(r.name)} <span class="heb">${esc(r.he || "")}</span> (${r.have}/${r.total})`).join(" · ")}</div>
      ${running ? `<div class="progress" style="height:10px;margin:6px 0"><div style="width:${st.progress || 0}%"></div></div>
        <div class="small">Installing the complete library… ${Math.round(st.progress || 0)}% — keep the app open.</div>`
      : `<div class="small lh-msg">${esc(st.message || "")}</div>
      <div class="small">To get <b>everything</b> (Talmud, all seforim): download <b>both</b> files
        <code>SeforimLibrary.sqlite.xz.part1of2</code> (1.99 GB) and <code>…part2of2</code> (0.35 GB) from the download page into your
        <b>Downloads</b> folder (or onto the USB stick next to SeforimStudio-Setup.exe), then press <b>Install now</b>. About 11 GB of free disk space is needed.</div>
      <div class="row" style="gap:6px;margin-top:6px;flex-wrap:wrap">
        <button class="btn small primary" id="lhFind">Install now</button>
        <input id="lhDir" class="small" placeholder="…or the folder with the files, e.g. E:\\" style="flex:1;min-width:140px">
        <button class="btn small" id="lhNet" title="Needs internet (about 4 GB, roughly an hour)">Download missing from the internet</button>
      </div>`}
    </div>`;
    if (running) { clearTimeout(this._lh); this._lh = setTimeout(() => this.drawHealth(), 2000); this._wasInstalling = true; return; }
    if (this._wasInstalling) { this._wasInstalling = false; if (st.state === "done") { App.toast(st.message); return this.loadTree(); } }
    $("#lhFind").onclick = async () => {
      const r = await App.api("install_check", { folder: $("#lhDir").value.trim() || null });
      if (r.state === "running") return this.drawHealth();
      App.toast(r.message || "Library files not found", true); this.drawHealth();
    };
    $("#lhNet").onclick = async () => {
      if (!await App.confirm(`Download the ${(h.total - h.have).toLocaleString()} missing seforim from Sefaria now? This needs internet, about 4 GB and roughly an hour. You can keep using the app meanwhile.`)) return;
      const cats = miss.map(r => r.name);
      const r = await App.api("dl_start", { categories: cats, english: true, missing_only: true });
      App.toast(r.started ? `Downloading ${r.count.toLocaleString()} seforim… (see Settings → Library for progress)` : (r.error || "A download is already running"));
    };
  },
  haveIn(n) { return n.works.filter(w => this.imported.has(w.id)).length + n.children.reduce((a, c) => a + this.haveIn(c), 0); },
  inCatalog(id) { const walk = ns => ns.some(n => n.works.some(w => w.id === id) || walk(n.children)); return this.tree ? walk(this.tree) : false; },
  drawTree() {
    const el = $("#libTree"); if (!el) return;
    const f = ($("#libFilter").value || "").trim().toLowerCase(), dlOnly = $("#libDl").checked, showHid = $("#libHid").checked;
    const match = w => (!f || w.title.toLowerCase().includes(f) || (w.he || "").includes(f)) && (!dlOnly || this.imported.has(w.id)) && (showHid || !this.hidden.has(w.id));
    const allWorks = [];
    const walk = (ns, depth) => ns.map(n => {
      const works = n.works.filter(match); works.forEach(w => allWorks.push(w));
      const kids = walk(n.children, depth + 1).filter(Boolean);
      if (!works.length && !kids.length) return "";
      return `<details ${f || depth < 1 && this.tree.length < 3 ? "open" : ""}><summary>${esc(n.name)} <span class="heb-cat">${esc(n.he || "")}</span><span class="count" title="installed / in catalog">${this.haveIn(n) < n.count ? this.haveIn(n) + "/" : ""}${n.count}</span></summary>
        ${kids.join("")}${works.map(w => this.workRow(w)).join("")}</details>`;
    });
    const favs = [];
    const collect = ns => ns.forEach(n => { n.works.forEach(w => { if (this.favorites.has(w.id)) favs.push(w); }); collect(n.children); });
    if (this.tree) collect(this.tree);
    const mine = (this.userWorks || []).filter(w => !f || w.title.toLowerCase().includes(f));
    el.innerHTML = (favs.length ? `<details open><summary>★ Favorites</summary>${favs.map(w => this.workRow(w)).join("")}</details>` : "")
      + (mine.length ? `<details open><summary>🗂 Personal Library</summary>${mine.map(w => this.workRow({ id: w.id, title: w.title, he: w.he_title })).join("")}</details>` : "")
      + (this.tree && this.tree.length ? walk(this.tree, 0).join("") : `<p class="muted" style="padding:10px">No catalog loaded. Open Settings → Library to load your seforim DB.</p>`);
    $$(".work", el).forEach(w => {
      w.onclick = () => this.clickWork(+w.dataset.id, w.dataset.title);
      w.oncontextmenu = e => { e.preventDefault(); this.workMenu(+w.dataset.id, w.dataset.title); };
    });
  },
  workRow(w) {
    const on = this.imported.has(w.id);
    return `<div class="work ${on ? "" : "off"}" data-id="${w.id}" data-title="${esc(w.title)}" title="${esc(w.title)}${w.he ? " — " + esc(w.he) : ""} · ${on ? "click to open" : "not downloaded — click to download once"} · right-click for more"><span class="en-t">${this.favorites.has(w.id) ? "★ " : ""}${esc(w.title)}</span><span class="heb">${esc(w.he || "")}</span></div>`;
  },
  async clickWork(id, title) {
    if (this.imported.has(id)) return this.open(id);
    if (await App.confirm(`"${title}" is not downloaded yet. Download it now? (Needs internet this one time; afterwards it works offline.)`)) {
      await App.api("dl_start", { work_ids: [id], english: true });
      App.toast("Downloading " + title + "…");
      const iv = setInterval(async () => { const s = await App.api("dl_status"); if (!s.running) { clearInterval(iv); if (s.errors.length) App.toast(s.errors[0], true); await this.loadTree(); if (this.imported.has(id)) this.open(id); } }, 1500);
    }
  },
  workMenu(id, title) {
    const fav = this.favorites.has(id), hid = this.hidden.has(id), on = this.imported.has(id);
    const wEl = $(`.work[data-id="${id}"] .heb`);
    App.modal(`<h3>${App.both(title, wEl ? wEl.textContent : "")}</h3><div class="col">
      ${on ? `<button class="btn" data-a="open">📖 Open</button><button class="btn" data-a="newtab">➕ Open in new tab</button>` : `<button class="btn" data-a="dl">⬇ Download (one time)</button>`}
      <button class="btn" data-a="fav">${fav ? "☆ Remove from favorites" : "★ Add to favorites"}</button>
      <button class="btn" data-a="hide">${hid ? "👁 Unhide" : "🙈 Hide this title (exclude from lists & search)"}</button>
      ${on ? `<button class="btn" data-a="stats">📊 Statistics</button><button class="btn" data-a="export">⤓ Export whole sefer…</button><button class="btn" data-a="share">📡 Share this sefer…</button><button class="btn danger" data-a="del">🗑 Remove downloaded text</button>` : ""}
      </div><div class="row" style="justify-content:flex-end;margin-top:10px"><button class="btn" data-close>Close</button></div>`, m => {
      m.onclick = async e => {
        const a = e.target.dataset.a; if (!a) return; App.closeModal();
        if (a === "open") this.open(id);
        if (a === "newtab") this.open(id, undefined, undefined, undefined, true);
        if (a === "dl") this.clickWork(id, title);
        if (a === "fav") { if (fav) await App.api("ud_delete", { table: "favorites", key: "work_id", value: id }); else await App.api("ud_save", { table: "favorites", row: { work_id: id, title } }); this.loadTree(); }
        if (a === "hide") { if (hid) await App.api("ud_delete", { table: "hidden", key: "work_id", value: id }); else await App.api("ud_save", { table: "hidden", row: { work_id: id, title } }); this.loadTree(); }
        if (a === "stats") { App.show("analysis"); Analysis.workStats(id); }
        if (a === "export") this.exportDialog({ work_id: id, whole: true, title });
        if (a === "share") { App.show("share"); Share.preselect("works", id, title); }
        if (a === "del" && await App.confirm(`Remove the downloaded text of ${title}? (You can download it again.)`)) { await App.api("delete_work", { work_id: id }); this.loadTree(); }
      };
    });
  },

  /* ---------- tabs ---------- */
  tab() { return this.tabs[this.activeIdx]; },
  drawTabs() {
    const el = $("#bookTabs");
    el.innerHTML = this.tabs.map((t, i) => `<div class="bt ${i === this.activeIdx ? "active" : ""}" data-i="${i}">${App.both(t.title, t.he_title)} <span class="small muted">${esc(t.chapter || "")}</span><span class="x" data-x="${i}">✕</span></div>`).join("")
      + `<div class="bt" id="tabNew" title="Open another sefer side by side">＋</div>`;
    $$(".bt[data-i]", el).forEach(b => b.onclick = e => { if (e.target.dataset.x) { this.tabs.splice(+e.target.dataset.x, 1); this.activeIdx = Math.min(this.activeIdx, this.tabs.length - 1); this.drawTabs(); this.redraw(true); App.saveSession(); return; } this.activeIdx = +b.dataset.i; this.drawTabs(); this.redraw(true); });
    $("#tabNew", el).onclick = () => { $("#libFilter").focus(); App.toast("Pick a sefer on the left — right-click → Open in new tab"); };
  },
  async open(work_id, node, chapter, passageId, newTab) {
    App.show("library");
    const r = await App.api("lib_toc", { work_id });
    let idx = this.tabs.findIndex(t => t.work_id === work_id);
    const t = { work_id, title: r.work.title, he_title: r.work.he_title, toc: r.toc, node: node ?? r.toc[0]?.node ?? "", chapter: chapter ?? r.toc[0]?.chapter ?? "", focus: passageId, sections: JSON.parse(r.work.section_names || "[]") };
    if (idx >= 0 && !newTab) this.tabs[idx] = t; else if (this.tabs.length && !newTab && this.activeIdx >= 0) { idx = this.activeIdx; this.tabs[idx] = t; } else { this.tabs.push(t); idx = this.tabs.length - 1; }
    this.activeIdx = idx; this.drawTabs(); await this.loadChapter(); App.saveSession();
  },
  async restore(sess) {
    for (const s of sess.tabs) { try { const r = await App.api("lib_toc", { work_id: s.work_id }); if (r.work) this.tabs.push({ ...s, he_title: r.work.he_title, toc: r.toc, sections: JSON.parse(r.work.section_names || "[]") }); } catch (e) { } }
    this.activeIdx = Math.min(sess.active || 0, this.tabs.length - 1);
    if (this.tabs.length && $("#bookTabs")) { this.drawTabs(); this.loadChapter(); }
  },
  async loadChapter() {
    const t = this.tab(); if (!t) return;
    const args = { work_id: t.work_id, node: t.node, chapter: t.chapter, unlocked: App.state.unlocked };
    if (this.view.infinite) { const cur = t.toc.find(x => x.node === t.node && x.chapter === t.chapter); Object.assign(args, { all: true, from_seq: cur ? cur.first_seq : 1, count: 600 }); }
    const r = await App.api("lib_chapter", args);
    t.passages = r.passages; t.ann = r.annotations; t.links = r.links;
    this.readStart = this.readStart || Date.now(); this.readCount = (this.readCount || 0) + r.passages.length; this.readWork = t.work_id;
    this.redraw(true);
    if (t.focus) { const p = $(`.psg[data-id="${t.focus}"]`); if (p) { p.scrollIntoView({ block: "center" }); this.select(+t.focus); } t.focus = null; }
    else $("#rText").scrollTop = 0;
  },
  step(d) {
    const t = this.tab(); if (!t) return;
    const i = t.toc.findIndex(x => x.node === t.node && x.chapter === t.chapter) + d;
    if (i < 0 || i >= t.toc.length) return App.toast(d > 0 ? "End of sefer" : "Beginning of sefer");
    t.node = t.toc[i].node; t.chapter = t.toc[i].chapter; this.drawTabs(); this.loadChapter(); App.saveSession();
  },
  chapterLabel(t, c) {
    const sec = t.sections[0] || "Chapter";
    if (/^\d+[ab]$/.test(c.chapter)) return `Daf ${c.chapter} · דף ${App.heNum(parseInt(c.chapter))} ${c.chapter.endsWith("a") ? "ע״א" : "ע״ב"}`;
    if (/^\d+$/.test(c.chapter)) return `${sec} ${c.chapter} · ${App.heNum(+c.chapter)}`;
    return c.chapter || c.node || t.title;
  },
  drawToc() {
    const t = this.tab(), el = $("#rToc"); if (!t) { el.innerHTML = ""; return; }
    let lastNode = null;
    el.innerHTML = `<div class="node">${esc(t.title)}</div><div class="node he" style="font-size:19px;color:var(--accent2)">${esc(t.he_title || "")}</div>` + t.toc.map((c, i) => {
      let s = "";
      if (c.node !== lastNode && c.node) s += `<div class="node">${esc(c.node)}</div>`;
      lastNode = c.node;
      return s + `<div class="ti ${c.node === t.node && c.chapter === t.chapter ? "cur" : ""}" data-i="${i}">${esc(this.chapterLabel(t, c))} <span class="small muted">(${c.n})</span></div>`;
    }).join("");
    $$(".ti", el).forEach(x => x.onclick = () => { const c = t.toc[+x.dataset.i]; t.node = c.node; t.chapter = c.chapter; this.drawTabs(); this.loadChapter(); App.saveSession(); });
    const cur = $(".ti.cur", el); if (cur) cur.scrollIntoView({ block: "nearest" });
  },
  nk(s) { if (!s) return ""; if (this.view.nikud === "none") return s.replace(NIKUD_ALL, ""); if (this.view.nikud === "nikud") return s.replace(TAAMIM, ""); return s; },
  psgHtml(p, t) {
    const a = (t.ann || {})[p.id] || { notes: [], highlights: [], tags: [] };
    const hl = a.highlights[0] ? "hl-" + a.highlights[0].color : "";
    const m = this.view.mode; const cls = m === "he" ? "he-only" : m === "en" ? "en-only" : m === "stacked" ? "stacked" : "";
    const he = (m !== "en" && p.he) ? `<div class="he">${esc(this.nk(p.he))}</div>` : (m === "side" ? "<div></div>" : "");
    const en = (m !== "he" && p.en) ? `<div class="en">${esc(p.en)}</div>` : "";
    const nl = (t.links || {})[p.id];
    return `<div class="psg ${cls} ${hl}" data-id="${p.id}" data-ref="${esc(p.ref)}">
      <span class="vnum">${esc(/^\d+$/.test(p.verse) ? App.heNum(+p.verse) : p.verse)}</span>
      <div class="badges">${nl ? `<span class="badge" data-act="comm" title="${nl} connections">🔗${nl}</span>` : ""}${a.bookmarked ? `<span class="badge">🔖</span>` : ""}</div>
      <div class="tools"><button data-act="note" title="Note">📝</button><button data-act="hl" title="Highlight">🖍</button><button data-act="bm" title="Bookmark">🔖</button>
        <button data-act="tag" title="Tag">🏷</button><button data-act="link" title="Link to another source">🔗</button><button data-act="sheet" title="Add to source sheet">📄</button>
        <button data-act="clip" title="Clipboard catcher">📋</button><button data-act="copy" title="Copy with citation">⧉</button><button data-act="chz" title="Add to Chazara review cards">🔁</button><button data-act="comm" title="Commentaries">💬</button></div>
      ${m === "en" ? en : he + en}
      ${a.tags.length ? `<div style="grid-column:1/-1">${a.tags.map(x => `<span class="tag">#${esc(x)}</span>`).join("")}</div>` : ""}
      ${a.notes.map(n => `<div class="note" data-note="${n.id}" style="background:${n.color || ""}">📝 ${esc(n.text)} ${n.tags ? `<span class="tag">${esc(n.tags)}</span>` : ""}</div>`).join("")}
    </div>`;
  },
  redraw(full) {
    const t = this.tab(), el = $("#rText"); this.layoutPanes();
    if (!t) { el.innerHTML = `<div class="muted" style="padding:40px;text-align:center">Choose a sefer from the list on the left.</div>`; $("#rToc").innerHTML = ""; return; }
    if (full) this.drawToc();
    const cur = t.toc.find(x => x.node === t.node && x.chapter === t.chapter);
    if (this.view.mode === "daf") return this.drawDaf(t, cur);
    let html = "", lastCh = null;
    for (const p of t.passages || []) {
      const key = p.node + "|" + p.chapter;
      if (key !== lastCh) { html += `<div class="chapter-title">${t.he_title ? `<span class="he">${esc(t.he_title)}</span> · ` : ""}${esc(t.title)} · ${esc(this.chapterLabel(t, { chapter: p.chapter, node: p.node }))}${p.node ? ` <div class="small muted">${esc(p.node)}</div>` : ""}</div>`; lastCh = key; }
      html += this.psgHtml(p, t);
    }
    el.innerHTML = html + `<div class="row" style="justify-content:center;margin-top:30px"><button class="btn" id="rNext2">Next ›</button></div>`;
    $("#rNext2").onclick = () => this.step(1);
    this.bindPassages(el, t);
    if (this.selected) { const s = $(`.psg[data-id="${this.selected}"]`, el); if (s) s.classList.add("sel"); }
  },
  bindPassages(el, t) {
    el.onclick = e => {
      const ps = e.target.closest(".psg"); if (!ps) return;
      const p = t.passages.find(x => x.id == ps.dataset.id);
      const act = e.target.dataset.act;
      if (e.target.closest(".note")) return this.editNote(p, +e.target.closest(".note").dataset.note);
      if (!act) { if (!String(window.getSelection())) this.select(p.id); return; }
      ({ note: () => this.editNote(p), hl: () => this.highlight(p), bm: () => this.bookmark(p), tag: () => this.tagPassage(p), link: () => this.userLink(p),
        sheet: () => Sheets.addSource(p), clip: () => App.addClip((this.nk(p.he) || "") + (p.en ? "\n" + p.en : ""), p.ref),
        chz: async () => { if (!App.pages.chazara) return App.toast("Turn on the Chazara plugin (Plugins screen)", true);
          const r = await App.api("plugin_call", { id: "chazara", fn: "add", args: { ref: p.ref } }); App.toast(r.added ? "Added to Chazara — review it on the Chazara screen" : "Already in Chazara"); },
        copy: () => App.copy(`${p.he || ""}\n${p.en || ""}\n— ${p.ref}\n${App.sefariaLink(p.ref)}`.replace(/\n\n/g, "\n"), `<p dir="rtl">${esc(p.he)}</p><p>${esc(p.en)}</p><p style="color:#8a6d3b">— ${esc(p.ref)}</p>`),
        comm: () => { this.view.comm = true; $("#rComm").checked = true; this.layoutPanes(); this.select(p.id, true); } })[act]?.();
    };
  },
  select(id, force) {
    this.selected = id; $$(".psg.sel").forEach(x => x.classList.remove("sel")); const el = $(`.psg[data-id="${id}"]`); if (el) el.classList.add("sel");
    const t = this.tab(); const p = t && (t.passages || []).find(x => x.id == id); if (!p) return;
    App.status(p.ref);
    if (this.view.comm || force) this.loadConnections(p);
  },
  onScroll() {
    if (!this.view.sync || !this.view.comm) return;
    clearTimeout(this._sc); this._sc = setTimeout(() => {
      const pane = $("#rText"), top = pane.getBoundingClientRect().top + 40;
      const first = $$(".psg", pane).find(p => p.getBoundingClientRect().bottom > top);
      if (first && first.dataset.id != this.selected) this.select(+first.dataset.id);
    }, 250);
  },
  async loadConnections(p) {
    const el = $("#rComm2"); el.innerHTML = `<p class="muted small">Loading connections for ${esc(p.ref)}…</p>`;
    const groups = await App.api("connections", { ref: p.ref });
    if (this.selected !== p.id) return;
    el.innerHTML = `<div class="row"><b>${esc(p.ref)}</b> <span class="he-name">${esc(App.heRef(p.ref, this.tab().he_title, this.tab().title))}</span><span class="spacer"></span><button class="btn small" id="cLink">+ My link</button></div>` + (groups.length ? groups.map(g => `<div class="comm-group"><h4><span>${App.both(g.title, g.he_title)}</span><span class="small muted">${g.items.length}${g.local ? "" : " · not downloaded"}</span></h4>
      ${g.items.map(i => i.texts.length ? i.texts.map(x => `<div class="comm-item" data-ref="${esc(x.ref)}"><div class="small"><a href="#" data-open="${x.id}">${esc(x.ref)}</a> <span class="muted">${esc(i.type || "")}</span></div>${x.he ? `<div class="he">${esc(this.nk(x.he))}</div>` : ""}${x.en ? `<div class="en">${esc(x.en)}</div>` : ""}</div>`).join("")
        : `<div class="comm-item small muted">${esc(i.ref)} (${esc(i.type || "")})</div>`).join("")}</div>`).join("")
      : `<p class="muted small">No connections found. Download the cross-reference pack in Settings → Library, or add your own link.</p>`);
    $("#cLink", el).onclick = () => this.userLink(p);
    $$("[data-open]", el).forEach(a => a.onclick = async e => { e.preventDefault(); const r = await App.api("passage", { id: +a.dataset.open }); this.open(r.work_id, r.node, r.chapter, r.id, e.ctrlKey || App.state.settings.comm_new_tab); });
  },
  async drawDaf(t, cur) {
    const el = $("#rText");
    el.innerHTML = `<p class="muted small" style="text-align:center">Building Daf layout…</p>`;
    const side = {};
    for (const p of (t.passages || []).slice(0, 80)) {
      const gs = await App.api("connections", { ref: p.ref });
      for (const g of gs) for (const i of g.items) for (const x of i.texts) (side[g.title] = side[g.title] || []).push(x);
    }
    const titles = Object.keys(side).sort((a, b) => side[b].length - side[a].length);
    const col = name => name ? `<div class="daf-side"><div style="text-align:center;font-weight:700;color:var(--accent)">${esc(name)}</div>${side[name].map(x => `<span class="he" data-ref="${esc(x.ref)}">${esc(this.nk(x.he || x.en))} </span>`).join("")}</div>` : `<div class="daf-side muted small">No commentary downloaded for this ${esc(t.sections[0] || "page")}.</div>`;
    el.innerHTML = `<div class="chapter-title">${esc(t.he_title || t.title)} · ${esc(this.chapterLabel(t, cur || {}))}</div>
      <div class="daf-layout">${col(titles[0])}<div class="daf-main">${(t.passages || []).map(p => `<span class="he" data-ref="${esc(p.ref)}" data-id="${p.id}">${esc(this.nk(p.he))} </span>`).join("")}</div>${col(titles[1])}</div>
      ${titles.slice(2).map(n => `<h2>${esc(n)}</h2>${side[n].map(x => `<p class="he" data-ref="${esc(x.ref)}" style="font-size:16px">${esc(this.nk(x.he || x.en))}</p>`).join("")}`).join("")}`;
  },
  find(q) {
    $$(".psg").forEach(p => p.style.display = "");
    if (!q) return;
    const plain = s => (s || "").replace(NIKUD_ALL, "").toLowerCase();
    const t = this.tab(); let n = 0;
    $$(".psg").forEach(el => { const p = t.passages.find(x => x.id == el.dataset.id); const hit = plain(p.he).includes(plain(q)) || (p.en || "").toLowerCase().includes(q.toLowerCase()); el.style.display = hit ? "" : "none"; n += hit; });
    App.status(`${n} passages contain “${q}”`);
  },

  /* ---------- annotations ---------- */
  async editNote(p, noteId) {
    const t = this.tab(), ann = (t.ann[p.id] || { notes: [] }); const n = noteId ? ann.notes.find(x => x.id === noteId) : null;
    App.modal(`<h3>📝 Note on ${esc(p.ref)}</h3>
      <textarea id="nTxt" class="he-input" style="min-height:140px" dir="auto">${esc(n && n.text !== "🔒 private note" ? n.text : "")}</textarea>
      <div class="row"><label>Tags <input id="nTags" value="${esc(n?.tags || "")}" placeholder="Halacha, Pesach 2026"></label>
      <label>Lane <select id="nLane"><option value="#fff3a0">💡 Chiddush</option><option value="#dbeafe">📚 Source</option><option value="#dcfce7">✔ Halacha</option><option value="#fde2e2">❓ Question</option></select></label>
      <label><input type="checkbox" id="nPriv" ${n?.private ? "checked" : ""}> 🔒 Private</label>
      <label>Share with <input id="nShare" value="${esc(n?.shared_with || "")}" placeholder="chavrusa name" style="width:120px"></label></div>
      <div class="row" style="margin-top:10px">${n ? `<button class="btn danger" id="nDel">Delete</button>` : ""}<span class="spacer"></span><button class="btn" data-close>Cancel</button><button class="btn primary" id="nOk">Save</button></div>`, m => {
      if (n?.color) $("#nLane", m).value = n.color;
      $("#nTxt", m).focus();
      $("#nOk", m).onclick = async () => {
        await App.api("ud_save", { table: "notes", row: { id: n?.id, passage_id: p.id, ref: p.ref, text: $("#nTxt", m).value, tags: $("#nTags", m).value, color: $("#nLane", m).value, private: $("#nPriv", m).checked ? 1 : 0, shared_with: $("#nShare", m).value } });
        App.closeModal(); this.loadChapter();
      };
      if (n) $("#nDel", m).onclick = async () => { await App.api("ud_delete", { table: "notes", value: n.id }); App.closeModal(); this.loadChapter(); };
    });
  },
  highlight(p) {
    App.modal(`<h3>🖍 Highlight ${esc(p.ref)}</h3><div class="row">${["yellow", "green", "blue", "pink"].map(c => `<button class="btn" data-c="${c}" style="background:${{ yellow: "#ffe58a", green: "#b9e4c9", blue: "#bcd6f5", pink: "#f7c3d6" }[c]};color:#222">${c}</button>`).join("")}<button class="btn" data-c="">Remove</button></div>`, m => {
      m.onclick = async e => {
        if (!("c" in e.target.dataset)) return;
        const t = this.tab(); for (const x of (t.ann[p.id]?.highlights || [])) await App.api("ud_delete", { table: "highlights", value: x.id });
        if (e.target.dataset.c) await App.api("ud_save", { table: "highlights", row: { passage_id: p.id, ref: p.ref, color: e.target.dataset.c } });
        App.closeModal(); this.loadChapter();
      };
    });
  },
  async bookmark(p) {
    const folders = [...new Set((await App.api("ud_list", { table: "bookmarks" })).map(b => b.folder))];
    const folder = await App.prompt(`Bookmark ${p.ref} — folder:`, folders[0] || "General", { help: "Existing folders: " + (folders.join(", ") || "none yet") });
    if (folder == null) return;
    const t = this.tab();
    await App.api("ud_save", { table: "bookmarks", row: { folder: folder || "General", ref: p.ref, passage_id: p.id, work_id: t.work_id, title: t.title } });
    App.toast("Bookmarked in " + folder); this.loadChapter();
  },
  async tagPassage(p) {
    const tag = await App.prompt("Add a tag to " + p.ref, "", { help: "e.g. Pesach 2026, Aggadah, Hilchos Shabbos" }); if (!tag) return;
    await App.api("ud_save", { table: "tags", row: { passage_id: p.id, ref: p.ref, tag } }); this.loadChapter();
  },
  async userLink(p) {
    const ref = await App.prompt(`Link ${p.ref} to another source (e.g. Berakhot 2a:1):`); if (!ref) return;
    const label = await App.prompt("Label for this link (optional)", "my link");
    await App.api("ud_save", { table: "user_links", row: { ref_a: p.ref, ref_b: ref, label: label || "" } }); App.toast("Linked"); this.loadConnections(p);
  },
  exportDialog(opt) {
    const t = this.tab(); opt = opt || (t ? { work_id: t.work_id, node: t.node, chapter: t.chapter, title: `${t.title} ${t.chapter}` } : null); if (!opt) return;
    App.modal(`<h3>⤓ Export ${esc(opt.title)}</h3>
      <div class="row"><label><input type="radio" name="xr" value="ch" ${opt.whole ? "" : "checked"}> This chapter</label><label><input type="radio" name="xr" value="all" ${opt.whole ? "checked" : ""}> Whole sefer</label><label><input type="checkbox" id="xEn" checked> Include English</label></div>
      <div class="row" style="margin-top:10px">${["docx", "html", "txt", "md", "epub", "json", "csv", "tei", "sqlite"].map(f => `<button class="btn" data-f="${f}">${f.toUpperCase()}</button>`).join("")}<button class="btn gold" data-f="print">🖨 Print / PDF</button></div>
      <p class="small muted">Word files are right-to-left with Hebrew fonts. PDF: choose “Save as PDF” in the print window.</p><div class="row" style="justify-content:flex-end"><button class="btn" data-close>Close</button></div>`, m => {
      m.onclick = async e => {
        const f = e.target.dataset.f; if (!f) return;
        const whole = $("input[name=xr]:checked", m).value === "all";
        if (f === "print") { App.closeModal(); return this.print(); }
        const r = await App.api("export_passages", { ...opt, whole, format: f, english: $("#xEn", m).checked, title: whole ? (opt.title || "").replace(/ \S+$/, "") || opt.title : opt.title, font: App.state.settings.export_font });
        App.download(r.url); App.toast(`Exported ${r.count} passages → ${r.name}`);
      };
    });
  },
  print() { const el = $("#rText"); el.classList.add("print-area"); window.print(); setTimeout(() => el.classList.remove("print-area"), 500); },
  logReading() {
    if (App.current !== "library" || !this.readStart || document.hidden) return;
    const secs = Math.round((Date.now() - this.readStart) / 1000);
    if (secs > 20) App.api("reading_log", { work_id: this.readWork, passages: this.readCount || 0, seconds: secs }).catch(() => {});
    this.readStart = Date.now(); this.readCount = 0;
  }
};
App.heNum = n => { if (!n || n < 1) return String(n); let s = ""; const v = [[400, "ת"], [300, "ש"], [200, "ר"], [100, "ק"]]; for (const [a, c] of v) while (n >= a) { s += c; n -= a; }
  if (n === 15) s += "טו"; else if (n === 16) s += "טז"; else { const t = [[90, "צ"], [80, "פ"], [70, "ע"], [60, "ס"], [50, "נ"], [40, "מ"], [30, "ל"], [20, "כ"], [10, "י"]]; for (const [a, c] of t) if (n >= a) { s += c; n -= a; } if (n) s += "אבגדהוזחט"[n - 1]; }
  return s.length === 1 ? s + "׳" : s.slice(0, -1) + "״" + s.slice(-1); };
App.register("library", { title: "Library", icon: "📚", full: true, render(el) { Library.render(el); Library.loadTree(); }, onShow() { if (Library.tabs.length && !$("#rText .psg") && Library.view.mode !== "daf") { Library.drawTabs(); Library.loadChapter(); } } });
