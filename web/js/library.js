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
          <select id="rNikud" title="Vowels (nikud) and cantillation (trop)"><option value="full">Nikud + trop</option><option value="nikud">Nikud only</option><option value="taamim">Trop only</option><option value="none">No nikud, no trop</option></select>
          <select id="rTr" title="Translation"><option value="full">English: explanatory</option><option value="basic">English: basic</option><option value="inter">Interlinear</option></select>
          <select id="rPunct" title="Punctuation"><option value="asis">Punctuation: as written</option><option value="add">Punctuation: add (from trop)</option><option value="remove">Punctuation: none</option></select>
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
    $("#rTr", el).value = v.tr || "full";
    $("#rTr", el).onchange = e => { v.tr = e.target.value; this.saveView(); this.redraw(); };
    $("#rPunct", el).value = v.punct || "asis";
    $("#rPunct", el).onchange = e => { v.punct = e.target.value; this.saveView(); this.redraw(); };
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
    this.userWorks = (await App.api("lib_works")).filter(w => w.source === "user" || (w.source !== "otzaria" && !this.inCatalog(w.id)));
    this.drawTree();
    this.drawHealth();
  },
  /* ---------- "is the whole library installed?" ---------- */
  async drawHealth() {
    const el = $("#libHealth"); if (!el) return;
    const h = await App.api("library_health").catch(() => null);
    if (h && h.more && h.more.state === "running") {
      el.innerHTML = `<div class="lib-health"><b>📚 Adding thousands of extra seforim…</b><div class="progress" style="height:10px;margin:6px 0"><div style="width:${h.more.progress || 0}%"></div></div><div class="small">${Math.round(h.more.progress || 0)}% — keep the app open.</div></div>`;
      clearTimeout(this._lh); this._lh = setTimeout(() => this.drawHealth(), 3000); this._wasMore = true; return;
    }
    if (this._wasMore) { this._wasMore = false; App.toast(h.more.message || "Extra seforim added"); return this.loadTree(); }
    if (!h || h.library_ok) { el.innerHTML = ""; return; }
    const st = h.install || {}, running = st.state === "running";
    el.innerHTML = `<details class="lib-health" ${running || this._lhOpen ? "open" : ""}>
      <summary><b>📚 The complete library is not installed yet</b> <span class="small">— ${running ? "installing…" : "install it ›"}</span></summary>
      ${running ? `<div class="progress" style="height:10px;margin:6px 0"><div style="width:${st.progress || 0}%"></div></div>
        <div class="small">Installing the complete library… ${Math.round(st.progress || 0)}% — keep the app open.</div>`
      : `<div class="small lh-msg">${esc(st.message || "")}</div>
      <div class="small">Download <b>both</b> library files <code>SeforimLibrary.sqlite.xz.part1of2</code> and <code>…part2of2</code> into <b>Downloads</b>
        (or onto the USB stick next to SeforimStudio-Setup.exe), then press <b>Install now</b>. About 15 GB of free disk space is needed.</div>
      <div class="row" style="gap:6px;margin-top:6px;flex-wrap:wrap">
        <button class="btn small primary" id="lhFind">Install now</button>
        <input id="lhDir" data-pick="folder" class="small" placeholder="…or the folder with the files, e.g. E:\\" style="flex:1;min-width:140px"></div>`}
    </details>`;
    $("details", el).ontoggle = e => { this._lhOpen = e.target.open; };
    if (running) { clearTimeout(this._lh); this._lh = setTimeout(() => this.drawHealth(), 2000); this._wasInstalling = true; return; }
    if (this._wasInstalling) { this._wasInstalling = false; if (st.state === "done") { App.toast(st.message); return this.loadTree(); } }
    $("#lhFind").onclick = async () => {
      const r = await App.api("install_check", { folder: $("#lhDir").value.trim() || null });
      if (r.state === "running") return this.drawHealth();
      App.toast(r.message || "Library files not found", true); this.drawHealth();
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
    App.toast(`"${title}" is part of the complete library — install it from Library → "install it" (offline, from the downloaded files).`, true);
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
    const t = { work_id, title: r.work.title, he_title: r.work.he_title, toc: r.toc, node: node ?? r.toc[0]?.node ?? "", chapter: chapter ?? r.toc[0]?.chapter ?? "", focus: passageId, sections: JSON.parse(r.work.section_names || "[]"), has_en: r.work.has_en, has_basic: r.work.has_basic, en_approx: r.work.en_approx };
    if (idx >= 0 && !newTab) this.tabs[idx] = t; else if (this.tabs.length && !newTab && this.activeIdx >= 0) { idx = this.activeIdx; this.tabs[idx] = t; } else { this.tabs.push(t); idx = this.tabs.length - 1; }
    this.activeIdx = idx; this.drawTabs(); await this.loadChapter(); App.saveSession();
  },
  async restore(sess) {
    for (const s of sess.tabs) { try { const r = await App.api("lib_toc", { work_id: s.work_id }); if (r.work) this.tabs.push({ ...s, he_title: r.work.he_title, toc: r.toc, sections: JSON.parse(r.work.section_names || "[]"), has_en: r.work.has_en, has_basic: r.work.has_basic, en_approx: r.work.en_approx }); } catch (e) { } }
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
  nk(s) {
    if (!s) return "";
    const pu = this.view.punct || "asis";
    if (pu === "add") {
      // the trop is the original punctuation: sof pasuk = full stop, etnachta / zakef / segolta = comma
      s = s.split(/(\s+)/).map(w => {
        if (/^\s+$/.test(w) || !w) return w;
        if (/\u05C3/.test(w)) return w.replace(/\u05C3/g, "") + ".";
        if (/[\u0591\u0592\u0594\u0595]/.test(w) && !/[.,;:]$/.test(w)) return w + ",";
        return w;
      }).join("");
    }
    if (pu === "remove") s = s.replace(/[\u05C3\u05C0\u05C6.,:;!?"'״׳()\[\]{}–—]/g, "").replace(/\u05BE/g, " ");
    const n = this.view.nikud;
    if (n === "none") s = s.replace(NIKUD_ALL, "").replace(/[\u05C0\u05C3\u05C6]/g, pu === "add" ? "" : "");
    else if (n === "nikud") s = s.replace(TAAMIM, "");
    else if (n === "taamim") s = s.replace(VOWELS, "");
    return s;
  },
  psgHtml(p, t) {
    const a = (t.ann || {})[p.id] || { notes: [], highlights: [], tags: [] };
    const hl = a.highlights[0] ? "hl-" + a.highlights[0].color : "";
    const m = this.view.mode; const cls = m === "he" ? "he-only" : m === "en" ? "en-only" : m === "stacked" ? "stacked" : "";
    const he = (m !== "en" && p.he) ? `<div class="he">${esc(this.nk(p.he))}</div>` : (m === "side" ? "<div></div>" : "");
    const enText = this.view.tr === "basic" && p.en_basic ? p.en_basic : p.en;
    const en = (m !== "he" && enText) ? `<div class="en">${esc(enText)}</div>` : "";
    if (this.view.tr === "inter" && p.he) return `<div class="psg inter ${hl}" data-id="${p.id}" data-ref="${esc(p.ref)}"><div class="vnum">${esc(p.verse || "")}</div><div class="inter-words" data-inter="${esc(p.ref)}">${esc(this.nk(p.he))}</div>${en}</div>`;
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
    el.innerHTML = this.translationNote(t) + `<div class="comm-bar" id="rChips"></div>` + html + `<div class="row" style="justify-content:center;margin-top:30px"><button class="btn" id="rNext2">Next ›</button></div>`;
    $("#rNext2").onclick = () => this.step(1);
    this.drawCommChips(t, cur);
    if (this.view.tr === "inter") this.fillInter(el);
    this.bindPassages(el, t);
    if (this.selected) { const s = $(`.psg[data-id="${this.selected}"]`, el); if (s) s.classList.add("sel"); }
  },
  /* say plainly what translation this sefer has */
  translationNote(t) {
    const tr = this.view.tr || "full", m = this.view.mode;
    if (m === "he") return "";
    let msg = "";
    if (t.has_en === false && tr !== "inter") msg = "ⓘ This sefer has no English translation (none exists in the free libraries). For help reading it, choose <b>Interlinear</b> (each word's meaning) or use 🌐 Translate.";
    else if (t.has_en && tr === "basic" && !t.has_basic) msg = "ⓘ This sefer's translation is not divided into literal words and explanation, so <b>basic</b> shows the full translation.";
    else if (t.has_en && t.en_approx && tr !== "inter") msg = "ⓘ This translation was made for a differently divided text: it is placed beside the Hebrew by length, so it can be a line or two off.";
    return msg ? `<div class="tr-note small">${msg}</div>` : "";
  },
  /* interlinear: every Hebrew word with its English meaning under it */
  async fillInter(el) {
    const boxes = $$("[data-inter]", el); if (!boxes.length) return;
    const r = await App.api("interlinear", { refs: boxes.map(b => b.dataset.inter), texts: boxes.map(b => b.textContent) }).catch(() => null);
    if (!r) return;
    boxes.forEach((b, i) => { const ws = r.verses[i] || []; if (!ws.length) return;
      b.innerHTML = ws.map(w => `<span class="iw" title="${esc(w.lemma || "")}${w.strong ? " · Strong's " + esc(w.strong) : ""}"><span class="iw-he">${esc(this.nk(w.w))}</span><span class="iw-en">${esc(w.g || "·")}</span></span>`).join(""); });
    if (r.note) { const n = h(`<p class="small muted inter-note">${esc(r.note)}</p>`); el.prepend(n); }
  },
  /* buttons for every commentary on this chapter / daf: click one to read it beside the text */
  async drawCommChips(t, cur) {
    const ch = (cur && cur.chapter) || (t.passages[0] || {}).chapter; if (!ch) return;
    const d = await App.api("daf", { work_id: t.work_id, node: (cur && cur.node) || "", chapter: ch, names_only: true }).catch(() => null);
    const box = $("#rChips"); if (!box || !d || this.tab() !== t) return;
    const isDaf = /^\d+[ab]$/.test(ch);
    box.innerHTML = (isDaf ? `<button class="chip on" id="rDafBtn">📜 Daf layout (Vilna)</button>` : "") +
      (d.commentaries.length ? `<span class="small muted">Commentaries:</span> ` + d.commentaries.map(c => `<button class="chip ${this.commFilter === c.title ? "on" : ""}" data-cf="${esc(c.title)}" title="${esc(c.title)} · ${c.n}">${esc(c.he_title)} <small>${c.n}</small></button>`).join("")
        + (this.commFilter ? ` <button class="chip" data-cf="">✕ all</button>` : "") : "");
    const db = $("#rDafBtn", box); if (db) db.onclick = () => { this.view.mode = "daf"; $("#rMode").value = "daf"; this.redraw(); };
    $$("[data-cf]", box).forEach(b => b.onclick = () => {
      this.commFilter = b.dataset.cf || null; this.view.comm = true; $("#rComm").checked = true; this.layoutPanes();
      this.drawCommChips(t, cur);
      const p = t.passages.find(x => x.id === this.selected) || t.passages[0]; if (p) this.select(p.id, true);
    });
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
        copy: () => App.copy(`${p.he || ""}\n${p.en || ""}\n— ${p.ref}`.replace(/\n\n/g, "\n"), `<p dir="rtl">${esc(p.he)}</p><p>${esc(p.en)}</p><p style="color:#8a6d3b">— ${esc(p.ref)}</p>`),
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
    let groups = await App.api("connections", { ref: p.ref });
    if (this.selected !== p.id) return;
    if (this.commFilter) { const f = groups.filter(g => g.title === this.commFilter || g.title.startsWith(this.commFilter + " on")); if (f.length) groups = f; }
    const st = App.state.settings, showEn = st.comm_en !== "0", open = this.commOpen = this.commOpen || {};
    const local = groups.filter(g => g.local), missing = groups.filter(g => !g.local);
    const cat = g => { const c = (g.items[0] || {}).cat || ""; return c || "Other"; };
    const cats = [...new Set(local.map(cat))];
    el.innerHTML = `<div class="comm-head"><div><b>${esc(p.ref)}</b> <span class="he-name">${esc(App.heRef(p.ref, this.tab().he_title, this.tab().title))}</span></div>
        <div class="row small" style="gap:6px;flex-wrap:wrap">
          <label class="tgl"><input type="checkbox" id="cEn" ${showEn ? "checked" : ""}> Translation</label>
          ${this.fontPicker("comm_pane_font", "Font", "regular")}
          <button class="btn small" id="cAll">${Object.values(open).some(v => v === false) ? "Open all" : "Close all"}</button>
          <button class="btn small" id="cPrint" title="Print these commentaries">🖨</button><button class="btn small" id="cLink">+ My link</button></div>
        ${cats.length > 1 ? `<div class="comm-cats">${["All", ...cats].map(c => `<button class="chip ${(this.commCat || "All") === c ? "on" : ""}" data-cc="${esc(c)}">${esc(c)}</button>`).join("")}</div>` : ""}</div>
      <div id="cBody">` + (local.length ? local.filter(g => !this.commCat || this.commCat === "All" || cat(g) === this.commCat).map(g => {
        const n = g.items.reduce((k, i) => k + i.texts.length, 0);
        return `<details class="comm-group" data-g="${esc(g.title)}" ${open[g.title] === false ? "" : "open"}><summary><span class="cg-he">${esc(g.he_title && g.he_title !== g.title ? g.he_title : "")}</span> <span class="cg-en">${esc(g.title)}</span><span class="spacer"></span><span class="badge">${n}</span></summary>
        ${g.items.filter(i => i.texts.length).map(i => i.texts.map(x => `<div class="comm-item" data-ref="${esc(x.ref)}">${x.he ? `<div class="he">${esc(this.nk(x.he))}</div>` : ""}${x.en && showEn ? `<div class="en">${esc(x.en)}</div>` : ""}
          <div class="small comm-ref"><a href="#" data-open="${x.id}">${esc(x.ref)} ›</a></div></div>`).join("")).join("")}</details>`; }).join("")
      : `<p class="muted small">No commentaries found for this passage.</p>`)
      + (missing.length ? `<details class="comm-missing"><summary class="small muted">${missing.length} more not in your library</summary><div class="small muted">${missing.map(g => esc(g.title)).join(" · ")}</div><p class="small">Get them: Library → “get the rest”, or Settings → Library.</p></details>` : "") + `</div>`;
    $("#cEn", el).onchange = async e => { await App.setSetting("comm_en", e.target.checked ? "1" : "0"); this.loadConnections(p); };
    $$("[data-cc]", el).forEach(b => b.onclick = () => { this.commCat = b.dataset.cc; this.loadConnections(p); });
    $$("details.comm-group", el).forEach(d => d.ontoggle = () => { open[d.dataset.g] = d.open; });
    $("#cAll", el).onclick = () => { const anyClosed = $$("details.comm-group", el).some(d => !d.open); $$("details.comm-group", el).forEach(d => { d.open = anyClosed; open[d.dataset.g] = anyClosed; }); $("#cAll", el).textContent = anyClosed ? "Close all" : "Open all"; };
    $("#cPrint", el).onclick = () => this.printHtml(`<h2>${esc(p.ref)}</h2>` + $$("details.comm-group", el).filter(d => d.open).map(d => `<h3>${d.querySelector("summary").innerText}</h3>` + $$(".comm-item", d).map(x => x.outerHTML).join("")).join(""), p.ref + " - commentaries");
    $("#cLink", el).onclick = () => this.userLink(p);
    el.style.setProperty("--comm-pane-font", this.fontCss(App.state.settings.comm_pane_font, "regular"));
    $$("[data-fp]", el).forEach(sel => sel.onchange = async () => { await App.setSetting(sel.dataset.fp, sel.value); el.style.setProperty("--comm-pane-font", this.fontCss(sel.value, "regular")); });
    $$("[data-open]", el).forEach(a => a.onclick = async e => { e.preventDefault(); const r = await App.api("passage", { id: +a.dataset.open }); this.open(r.work_id, r.node, r.chapter, r.id, e.ctrlKey || App.state.settings.comm_new_tab); });
  },
  /* ---------- Daf layout (like a Vilna Shas page) ----------
     amud a: Rashi on the inner (right) side, Tosafos outer (left), Mesores HaShas in the right margin, Ein Mishpat /
     Torah Ohr in the left margin. Amud b is the mirror image. Any commentary can be switched on or off; the later
     commentaries (printed at the back of the volume) can be shown as links on the Gemara. */
  async drawDaf(t, cur) {
    const el = $("#rText");
    el.innerHTML = `<p class="muted small" style="text-align:center">Building the daf…</p>`;
    const ch = (cur && cur.chapter) || (t.passages[0] || {}).chapter || "";
    const d = await App.api("daf", { work_id: t.work_id || t.id, node: (cur && cur.node) || (t.passages[0] || {}).node || "", chapter: ch });
    if (this.tab() !== t || this.view.mode !== "daf") return;
    this.dafData = d;
    const MARG_IN = ["Mesorat HaShas"], MARG_OUT = ["Ein Mishpat Ner Mitzvah", "Torah Ohr", "Hagahot HaBach", "Gilyon HaShas"];
    const on = this.dafOn = this.dafOn || { Rashi: true, Tosafot: true, "Mesorat HaShas": true, "Ein Mishpat Ner Mitzvah": true, "Torah Ohr": true, _links: true };
    const amudB = /b$/.test(ch), dafNum = parseInt(ch);
    const dh = s => { const m = (s || "").match(/^(.{2,70}?)(\s[-–]\s|[.:]\s)/); return m ? `<b>${esc(m[1])}</b>${esc(m[2])}${esc(s.slice(m[0].length))}` : esc(s); };
    const C = name => d.commentaries.find(c => c.title === name);
    const cspans = c => c ? c.passages.map(x => `<span class="cm" data-a="${esc(x.anchor)}" data-ref="${esc(x.ref)}">${dh(this.nk(x.he || x.en))} </span>`).join("") : "";
    const head = c => `<div class="v-head">${esc(c.he_title)}</div>`;
    const col = (name, cls) => { const c = C(name); return on[name] && c ? `<div class="v-side ${cls}">${head(c)}${cspans(c)}</div>` : `<div class="v-side v-empty ${cls}"></div>`; };
    const marg = names => { const cs = names.map(C).filter(c => c && on[c.title]); return `<div class="v-marg">${cs.map(c => `<div class="v-mh">${esc(c.he_title)}</div>${c.passages.map(x => `<div class="cm" data-a="${esc(x.anchor)}" data-ref="${esc(x.ref)}">${esc(this.nk(x.he || x.en))}</div>`).join("")}`).join("")}</div>`; };
    const placed = new Set(["Rashi", "Tosafot", ...MARG_IN, ...MARG_OUT]);
    const later = d.commentaries.filter(c => !placed.has(c.title));          // printed at the back of the volume
    const extras = later.filter(c => on[c.title]);
    // links on the Gemara to the later commentaries (like the little letters that send you to the back of the volume)
    const linkMap = {};
    if (on._links) for (const c of later) for (const x of c.passages) (linkMap[x.anchor] = linkMap[x.anchor] || new Set()).add(c.title);
    const abbr = c => (C(c).he_title || c).replace(/^(רבינו|ר׳|רבי)\s/, "").split(/\s/)[0].slice(0, 6);
    const gem = t.passages.map((p, i) => { const seg = (p.verse || String(i + 1)).split(":")[0];
      const lk = linkMap[seg] ? [...linkMap[seg]].map(c => `<sup class="v-link" data-lc="${esc(c)}" data-a="${esc(seg)}" title="${esc(c)}">${esc(abbr(c))}</sup>`).join("") : "";
      return `<span class="gs" data-seg="${esc(seg)}" data-id="${p.id}" data-ref="${esc(p.ref)}">${i === 0 && dafNum === 2 && !amudB ? this.bigFirst(this.nk(p.he)) : esc(this.nk(p.he))}${lk} </span>`; }).join("");
    el.innerHTML = `<div class="v-bar">
        <span class="v-title he">${esc(d.he_title || d.title)} · דף ${App.heNum(dafNum)}${amudB ? ":" : "."}</span><span class="small muted">${esc(d.title)} ${esc(ch)}</span><span class="spacer"></span>
        <span class="v-fonts small">${this.fontPicker("daf_gem_font", "Gemara", "Frank Ruhl Libre")}${this.fontPicker("daf_comm_font", "Rashi / Tosafos", "rashi")}
          <select id="vSize" title="Size">${[80, 90, 100, 110, 125, 140].map(z => `<option value="${z}" ${String(App.state.settings.daf_size || 100) === String(z) ? "selected" : ""}>${z}%</option>`).join("")}</select></span>
        <button class="btn small" id="vEdit" title="Change words on this page before printing (does not change the sefer)">✏️ Edit page</button>
        <button class="btn small" id="vPrint">🖨 Print daf</button><button class="btn small" id="vPrintC">🖨 Print commentaries only</button></div>
      <div class="v-chips">${d.commentaries.map(c => `<button class="chip ${on[c.title] ? "on" : ""}" data-cm="${esc(c.title)}" title="${esc(c.title)} · ${c.passages.length}">${esc(c.he_title)}</button>`).join("") || `<span class="small muted">No commentaries downloaded for this masechta</span>`}
        ${later.length ? `<button class="chip ${on._links ? "on" : ""}" data-cm="_links" title="Marks on the Gemara that lead to the later commentaries (printed at the back of the volume)">🔗 Links to more commentaries</button>` : ""}
        <button class="chip" id="vOnly" title="Show just one commentary at a time">☝ one at a time</button>
        <button class="chip ${on._en ? "on" : ""}" data-cm="_en" title="The English translation of this amud, under the page">English translation</button></div>
      <div class="vilna ${amudB ? "amud-b" : "amud-a"}" id="vPage">
        <div class="v-hdr"><span>${amudB ? `${App.heNum(dafNum)}` : esc(d.he_title || d.title)}</span><span>${amudB ? esc(d.he_title || d.title) : `${App.heNum(dafNum)}`}</span></div>
        <div class="v-top">${amudB ? marg(MARG_OUT) + col("Tosafot", "v-tos") : marg(MARG_IN) + col("Rashi", "v-rashi")}<div class="v-gem">${gem}</div>${amudB ? col("Rashi", "v-rashi") + marg(MARG_IN) : col("Tosafot", "v-tos") + marg(MARG_OUT)}</div>
        <div class="v-bottom">${amudB ? `<div class="v-more v-tos"></div><div class="v-more v-rashi"></div>` : `<div class="v-more v-rashi"></div><div class="v-more v-tos"></div>`}</div>
      </div>
      ${on._en ? `<div class="vilna v-trans"><div class="v-hdr"><span>Translation</span><span class="small">${this.view.tr === "basic" ? "basic" : "explanatory"}</span></div>${t.passages.map((p, i) => `<p class="v-tr" data-seg="${esc((p.verse || String(i + 1)).split(":")[0])}">${esc(this.view.tr === "basic" && p.en_basic ? p.en_basic : p.en || "")}</p>`).join("")}</div>` : ""}
      ${extras.length ? `<div class="vilna v-back" id="vBack"><div class="v-hdr"><span>מפרשים · ${esc(d.he_title)} ${App.heNum(dafNum)}${amudB ? ":" : "."}</span></div>${extras.map(c => `<div class="v-extra" data-ex="${esc(c.title)}"><div class="v-head">${esc(c.he_title)} <small class="muted">${esc(c.title)}</small></div><div class="v-cols">${cspans(c)}</div></div>`).join("")}</div>` : ""}`;
    this.applyDafFonts(el);
    $$("[data-fp]", el).forEach(sel => sel.onchange = async () => { await App.setSetting(sel.dataset.fp, sel.value); this.drawDaf(t, cur); });
    $("#vSize", el).onchange = async e => { await App.setSetting("daf_size", e.target.value); this.drawDaf(t, cur); };
    // Rashi and Tosafos run beside the Gemara; what does not fit continues underneath, like the printed page
    const gemH = $(".v-gem", el).offsetHeight + 30;
    for (const cls of ["v-rashi", "v-tos"]) {
      const side = $(".v-top ." + cls, el), more = $(".v-bottom ." + cls, el);
      if (!side || !more) continue;
      const spans = $$(".cm", side);
      while (side.offsetHeight > gemH && spans.length) more.prepend(spans.pop());
    }
    $$("[data-cm]", el).forEach(b => b.onclick = () => { if (this._solo && !b.dataset.cm.startsWith("_")) { for (const k of Object.keys(on)) if (!k.startsWith("_")) on[k] = false; on[b.dataset.cm] = true; } else on[b.dataset.cm] = !on[b.dataset.cm]; this.drawDaf(t, cur); });
    const solo = $("#vOnly", el); solo.classList.toggle("on", !!this._solo);
    solo.onclick = () => { this._solo = !this._solo; if (this._solo) { const first = d.commentaries.find(c => on[c.title]); for (const k of Object.keys(on)) if (k !== "_links") on[k] = false; if (first) on[first.title] = true; } this.drawDaf(t, cur); };
    const light = seg => { $$(".hl-on", el).forEach(x => x.classList.remove("hl-on")); $$(`.gs[data-seg="${seg}"], .cm[data-a="${seg}"], .v-tr[data-seg="${seg}"]`, el).forEach(x => x.classList.add("hl-on")); };
    $$(".gs", el).forEach(g => g.onclick = e => { if (this._editing || e.target.closest(".v-link")) return; light(g.dataset.seg); const c = $(`.cm[data-a="${g.dataset.seg}"]`, el); if (c) c.scrollIntoView({ block: "nearest", behavior: "smooth" }); });
    $$(".cm", el).forEach(c => c.onclick = () => { if (this._editing) return; light(c.dataset.a); const g = $(`.gs[data-seg="${c.dataset.a}"]`, el); if (g) g.scrollIntoView({ block: "nearest", behavior: "smooth" }); });
    $$(".v-link", el).forEach(l => l.onclick = e => { e.stopPropagation(); const c = C(l.dataset.lc); const xs = c.passages.filter(x => x.anchor === l.dataset.a);
      App.modal(`<h3>${esc(c.he_title)} <small class="muted">${esc(c.title)}</small></h3><div style="max-height:60vh;overflow:auto">${xs.map(x => `<p class="he" style="font-size:19px;line-height:1.7">${dh(this.nk(x.he || x.en))}</p><div class="small muted">${esc(x.ref)}</div>`).join("")}</div>
        <div class="row" style="justify-content:flex-end"><button class="btn" id="vShowAll">Show ${esc(c.he_title)} on the page</button><button class="btn primary" data-close>Close</button></div>`, m => {
        $("#vShowAll", m).onclick = () => { on[c.title] = true; App.closeModal(); this.drawDaf(t, cur); }; }); });
    $("#vEdit", el).onclick = () => { this._editing = !this._editing; $$("#vPage, #vBack", el).forEach(x => x.contentEditable = this._editing); $("#vEdit", el).classList.toggle("primary", this._editing);
      App.toast(this._editing ? "Edit the page, then print. (The sefer itself is not changed.)" : "Editing off"); };
    $("#vPrint", el).onclick = () => this.printHtml(`${$("#vPage", el).outerHTML}${$(".v-trans", el) ? $(".v-trans", el).outerHTML : ""}${$("#vBack", el) ? $("#vBack", el).outerHTML : ""}`, `${d.title} ${ch}`);
    $("#vPrintC", el).onclick = () => {
      const shown = d.commentaries.filter(c => on[c.title]);
      if (!shown.length) return App.toast("Switch on at least one commentary", true);
      // printed as it is on the screen (including your edits)
      const html = shown.map(c => { const nodes = $$(`#vPage .cm, #vBack .cm`, el).filter(x => (x.dataset.ref || "").startsWith(c.title + " on") || (x.closest("[data-ex]") || {}).dataset?.ex === c.title);
        return `<div class="v-extra"><div class="v-head">${esc(c.he_title)}</div><div class="v-cols">${nodes.map(n => n.innerHTML).join(" ") || cspans(c)}</div></div>`; }).join("");
      this.printHtml(`<div class="vilna"><div class="v-hdr"><span>${esc(d.he_title)} ${App.heNum(dafNum)}${amudB ? ":" : "."}</span></div>${html}</div>`, `${d.title} ${ch} - commentaries`);
    };
  },
  /* font choices: Rashi script or a regular (square) font, or any installed font */
  fontPicker(key, label, def) {
    const cur = App.state.settings[key] || def;
    const fams = (App.state.fonts || []).filter(f => !/^(Noto Rashi Hebrew)$/.test(f));
    return `<label title="${esc(label)} font">${esc(label)} <select data-fp="${key}">
      <option value="rashi" ${cur === "rashi" ? "selected" : ""}>כתב רש״י (Rashi script)</option>
      <option value="regular" ${cur === "regular" ? "selected" : ""}>Regular (square letters)</option>
      ${fams.map(f => `<option value="${esc(f)}" ${cur === f ? "selected" : ""} style="font-family:'${esc(f)}'">${esc(f)}</option>`).join("")}</select></label>`;
  },
  fontCss(v, def) {
    v = v || def;
    if (v === "rashi") return `"Noto Rashi Hebrew", "Guttman Rashi", var(--he-font)`;
    if (v === "regular") return `var(--he-font)`;
    return `"${v}", var(--he-font)`;
  },
  applyDafFonts(el) {
    const st = App.state.settings, z = (+st.daf_size || 100) / 100;
    const page = $("#vPage", el); if (!page) return;
    for (const x of [page, $("#vBack", el)].filter(Boolean)) {
      x.style.setProperty("--gem-font", this.fontCss(st.daf_gem_font, "Frank Ruhl Libre"));
      x.style.setProperty("--comm-font", this.fontCss(st.daf_comm_font, "rashi"));
      x.style.setProperty("--daf-zoom", z);
    }
  },
  bigFirst(s) { const m = (s || "").match(/^(\S+)\s?([\s\S]*)$/); return m ? `<span class="v-first">${esc(m[1])}</span> ${esc(m[2])}` : esc(s); },
  /* print just this html with the page styles (in a hidden frame) */
  printHtml(html, title) {
    const f = document.createElement("iframe"); f.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0"; document.body.appendChild(f);
    const css = [...document.querySelectorAll("style, link[rel=stylesheet]")].map(x => x.outerHTML).join("");
    f.contentDocument.open();
    f.contentDocument.write(`<!doctype html><html dir="rtl" style="${esc(document.documentElement.getAttribute("style") || "")}"><head><meta charset="utf-8"><title>${esc(title)}</title>${css}<style>html,body{width:auto}body{background:#fff!important;color:#000;margin:0;padding:6mm;min-width:900px}.vilna{box-shadow:none;border:0;max-width:none;background:#fff}.vilna .hl-on{background:none}@page{size:A4;margin:8mm}@media print{body *{visibility:visible!important}}
/* a printed daf always looks like a regular Vilna page, whatever size is set on the screen */
.vilna{max-width:none!important;padding:0!important;border:0!important}
.vilna .v-top{grid-template-columns:.34fr 1fr 1.55fr 1fr .34fr!important;gap:9pt!important}
.vilna .v-gem{font-size:11.5pt!important;line-height:1.55!important}
.vilna .v-side,.vilna .v-more,.vilna .v-cols{font-size:8.3pt!important;line-height:1.45!important}
.vilna .v-marg{font-size:6.3pt!important;line-height:1.3!important}
.vilna .v-head{font-size:9pt!important}.vilna .v-hdr{font-size:11pt!important}
.vilna .v-first{font-size:22pt!important}.v-trans{font-size:10pt!important}
.v-link{display:none!important}</style></head><body><div class="print-area" style="position:static">${html}</div></body></html>`);
    f.contentDocument.close();
    setTimeout(() => {
      // lay Rashi and Tosafos out again at the printed size: beside the Gemara first, the rest underneath
      const d = f.contentDocument, gem = d.querySelector(".v-gem");
      if (gem) {
        f.style.width = "1050px"; f.style.height = "1400px";
        for (const cls of ["v-rashi", "v-tos"]) {
          const side = d.querySelector(".v-top ." + cls), more = d.querySelector(".v-bottom ." + cls);
          if (!side || !more) continue;
          [...more.querySelectorAll(".cm")].forEach(c => side.appendChild(c));
          const h = gem.offsetHeight + 20, spans = [...side.querySelectorAll(".cm")];
          while (side.offsetHeight > h && spans.length) more.prepend(spans.pop());
        }
        // one daf = one sheet of paper: shrink the whole page to fit A4 (about 718 x 1060 px inside the margins)
        const body = d.body, w = body.scrollWidth, ht = body.scrollHeight;
        const scale = Math.min(1, 718 / w, 1060 / ht);
        body.style.zoom = scale.toFixed(3);
        body.style.minWidth = "0"; body.style.padding = "0";
        d.head.insertAdjacentHTML("beforeend", "<style>@page{size:A4;margin:8mm}html,body{height:auto;overflow:hidden}.vilna,.v-back,.v-trans{break-inside:avoid;page-break-inside:avoid}</style>");
      }
      if (window.SeforimAndroid) { SeforimAndroid.printHtml("<!doctype html>" + f.contentDocument.documentElement.outerHTML, title || "Seforim Studio"); setTimeout(() => f.remove(), 2000); return; }
      f.contentWindow.focus(); f.contentWindow.print(); setTimeout(() => f.remove(), 2000);
    }, 700);
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
  print() {
    // print exactly what is on the screen: in Daf layout the Vilna page with the commentaries that are switched on
    if (this.view.mode === "daf" && $("#vPage")) {
      return this.printHtml(`${$("#vPage").outerHTML}${$(".v-trans") ? $(".v-trans").outerHTML : ""}${$("#vBack") ? $("#vBack").outerHTML : ""}`, document.title);
    }
    const el = $("#rText"); el.classList.add("print-area"); window.print(); setTimeout(() => el.classList.remove("print-area"), 500);
  },
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
