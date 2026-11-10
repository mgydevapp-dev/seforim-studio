/* My Library (personal notes, documents, bookmarks, tags, own seforim, import/export) and Source Sheets */
const Personal = {
  render(el) {
    el.innerHTML = `<h1 class="page-title">🗂 My Library <small>Your notes, documents, bookmarks and your own seforim — import & export in many formats.</small>
      <span class="spacer"></span><button class="btn" id="pmUnlock">🔓 Unlock private</button><button class="btn primary" id="pmImport">📥 Import files…</button></h1>
      <div class="tabs" id="pmTabs">${[["docs", "📝 Documents"], ["notes", "💬 Notes on passages"], ["bm", "🔖 Bookmarks"], ["tags", "🏷 Tags & highlights"], ["seforim", "📚 My seforim"], ["sheets", "📄 Source sheets"], ["covers", "📕 Covers"], ["links", "🔗 My links"], ["hist", "🕘 History"]].map(([k, t]) => `<button data-t="${k}">${t}</button>`).join("")}</div><div id="pmBody"></div>`;
    $$("#pmTabs button", el).forEach(b => b.onclick = () => this.tab(b.dataset.t));
    $("#pmImport", el).onclick = () => this.importDialog();
    $("#pmUnlock", el).onclick = () => this.unlock();
    this.tab("docs");
  },
  async unlock() {
    if (!App.state.status.pin_set) return App.toast("No PIN set yet — set one in Settings → Privacy");
    const pin = await App.prompt("Enter your PIN to show private notes:", "", { type: "password" }); if (pin == null) return;
    const r = await App.api("pin", { pin }); if (!r.ok) return App.toast("Wrong PIN", true);
    App.state.unlocked = true; App.state.pin = pin; App.toast("Private notes visible for this session"); this.tab(this.cur);
  },
  async tab(t) {
    this.cur = t; $$("#pmTabs button").forEach(b => b.classList.toggle("active", b.dataset.t === t));
    const el = $("#pmBody"); el.innerHTML = "<p class='muted'>Loading…</p>";
    const L = (table, extra = {}) => App.api("ud_list", { table, unlocked: App.state.unlocked, ...extra });
    if (t === "docs") {
      const docs = await L("docs", { order: "folder, updated DESC" });
      const folders = {}; docs.forEach(d => (folders[d.folder] = folders[d.folder] || []).push(d));
      el.innerHTML = `<div class="row"><button class="btn primary" id="pmNew">+ New document</button><button class="btn" id="pmExpSel">⤓ Export selected…</button><button class="btn" id="pmSefer">→ Add selected to library as seforim</button></div>` +
        (Object.entries(folders).map(([f, ds]) => `<h2>📁 ${esc(f)} <span class="small muted">(${ds.length})</span></h2>${ds.map(d => `<div class="list-item row"><input type="checkbox" data-sel="${d.id}"><div style="flex:1" data-open="${d.id}"><b>${d.private ? "🔒 " : ""}${esc(d.title)}</b> ${String(d.tags || "").split(",").filter(Boolean).map(x => `<span class="tag">${esc(x.trim())}</span>`).join("")}
          <div class="small muted">${esc(d.updated)} · ${esc(String(d.html || "").replace(/<[^>]+>/g, " ").slice(0, 120))}</div></div><button class="btn small danger" data-del="${d.id}">🗑</button></div>`).join("")}`).join("") || "<p class='muted'>No documents yet — write in Notes or import files.</p>");
      $("#pmNew").onclick = () => { App.show("notes"); Notes.action("new"); };
      $$("[data-open]", el).forEach(x => x.onclick = () => Notes.openDoc(+x.dataset.open));
      $$("[data-del]", el).forEach(x => x.onclick = async () => { if (await App.confirm("Delete this document?")) { await App.api("ud_delete", { table: "docs", value: +x.dataset.del }); this.tab("docs"); } });
      const sel = () => $$("[data-sel]:checked", el).map(x => +x.dataset.sel);
      $("#pmExpSel").onclick = () => this.exportDocs(sel());
      $("#pmSefer").onclick = async () => { for (const id of sel()) { const d = await App.api("ud_get", { table: "docs", id, pin: App.state.pin }); if (!d.locked) await App.api("import_as_sefer", { title: d.title, html: d.html }); } App.toast("Added to library"); Library.loadTree(); };
    }
    if (t === "notes") {
      const notes = await L("notes");
      el.innerHTML = `<div class="row"><input id="pmNF" placeholder="filter notes / tags…"><span class="spacer"></span><button class="btn" id="pmNExp">⤓ Export all notes (Word / CSV / HTML)</button></div><div id="pmNL"></div>`;
      const draw = () => { const f = $("#pmNF").value.toLowerCase(); $("#pmNL").innerHTML = notes.filter(n => !f || (n.text + n.tags + n.ref).toLowerCase().includes(f)).map(n => `<div class="list-item" data-pid="${n.passage_id}"><b>${esc(n.ref)}</b> ${n.private ? "🔒" : ""} ${n.tags ? `<span class="tag">${esc(n.tags)}</span>` : ""} ${n.shared_with ? `<span class="pill">shared: ${esc(n.shared_with)}</span>` : ""}<div dir="auto" style="border-right:4px solid ${esc(n.color || "#fff3a0")};padding-right:8px">${esc(n.text)}</div><div class="small muted">${esc(n.updated)}</div></div>`).join("") || "<p class='muted'>No notes yet — hover a passage in the Library and click 📝.</p>"; $$("[data-pid]", el).forEach(x => x.onclick = () => Search.openResult(+x.dataset.pid)); };
      $("#pmNF").oninput = draw; draw();
      $("#pmNExp").onclick = () => {
        const html = notes.map(n => `<h3>${esc(n.ref)}</h3><p>${esc(n.text)}</p>${n.tags ? `<p style="color:#888">${esc(n.tags)}</p>` : ""}`).join("");
        App.modal(`<h3>Export notes</h3><div class="row"><button class="btn" data-f="docx">Word</button><button class="btn" data-f="html">HTML</button><button class="btn" data-f="txt">Text</button><button class="btn" data-f="md">Markdown</button><button class="btn" data-f="csv">CSV</button></div><div class="row" style="justify-content:flex-end;margin-top:10px"><button class="btn" data-close>Close</button></div>`, m => {
          m.onclick = async e => { const f = e.target.dataset.f; if (!f) return;
            if (f === "csv") { const csv = "﻿ref,note,tags,updated\n" + notes.map(n => [n.ref, n.text, n.tags, n.updated].map(x => `"${String(x || "").replace(/"/g, '""')}"`).join(",")).join("\n"); App.saveData(csv, "my-notes.csv"); return; }
            const r = await App.api("export_doc", { format: f, title: "My notes", html, title_in_doc: true }); App.download(r.url); };
        });
      };
    }
    if (t === "bm") {
      const bms = await L("bookmarks", { order: "folder, created DESC" });
      const folders = {}; bms.forEach(b => (folders[b.folder] = folders[b.folder] || []).push(b));
      el.innerHTML = Object.entries(folders).map(([f, bs]) => `<h2>📁 ${esc(f)}</h2>${bs.map(b => `<div class="list-item row"><div style="flex:1" data-pid="${b.passage_id}"><b>${esc(b.ref)}</b> <span class="small muted">${esc(b.created)}</span></div><button class="btn small" data-mv="${b.id}">Move</button><button class="btn small danger" data-del="${b.id}">🗑</button></div>`).join("")}`).join("") || "<p class='muted'>No bookmarks yet.</p>";
      $$("[data-pid]", el).forEach(x => x.onclick = () => Search.openResult(+x.dataset.pid));
      $$("[data-del]", el).forEach(x => x.onclick = async () => { await App.api("ud_delete", { table: "bookmarks", value: +x.dataset.del }); this.tab("bm"); });
      $$("[data-mv]", el).forEach(x => x.onclick = async () => { const f = await App.prompt("Move to folder:"); if (!f) return; const b = bms.find(y => y.id == x.dataset.mv); await App.api("ud_save", { table: "bookmarks", row: { ...b, folder: f } }); this.tab("bm"); });
    }
    if (t === "tags") {
      const tags = await L("tags"), hls = await L("highlights");
      const by = {}; tags.forEach(x => (by[x.tag] = by[x.tag] || []).push(x));
      el.innerHTML = `<div class="grid g2"><div class="card"><b>Tags</b>${Object.entries(by).map(([tg, xs]) => `<h2>#${esc(tg)} <span class="small muted">${xs.length}</span></h2>${xs.map(x => `<div class="list-item" data-pid="${x.passage_id}">${esc(x.ref)}</div>`).join("")}`).join("") || "<p class='muted'>No tags.</p>"}</div>
        <div class="card"><b>Highlights</b>${hls.map(x => `<div class="list-item" data-pid="${x.passage_id}"><span class="pill" style="background:${{ yellow: "#ffe58a", green: "#b9e4c9", blue: "#bcd6f5", pink: "#f7c3d6" }[x.color]};color:#222">${x.color}</span> ${esc(x.ref)}</div>`).join("") || "<p class='muted'>No highlights.</p>"}</div></div>`;
      $$("[data-pid]", el).forEach(x => x.onclick = () => Search.openResult(+x.dataset.pid));
    }
    if (t === "seforim") {
      const works = (await App.api("lib_works")).filter(w => w.source === "user");
      el.innerHTML = `<div class="row"><button class="btn primary" id="pmAddS">+ Add files as seforim (Word, PDF, text, HTML, EPUB)</button></div><p class="small muted">Your own seforim become fully searchable (Hebrew, gematria, roshei teivos) right away. Lines starting with “# ”, “פרק ”, “סימן ” become chapters.</p>
        ${works.map(w => `<div class="list-item row"><div style="flex:1" data-w="${w.id}"><b>${esc(w.title)}</b> <span class="small muted">${w.n_passages} paragraphs · ${w.n_words} words · ${esc(w.category_path)}</span></div>
          <button class="btn small" data-x="${w.id}" data-t="${esc(w.title)}">⤓ Export</button><button class="btn small" data-sh="${w.id}" data-t="${esc(w.title)}">📡 Share</button><button class="btn small danger" data-del="${w.id}">🗑</button></div>`).join("") || "<p class='muted'>None yet.</p>"}`;
      $("#pmAddS").onclick = async () => { const ups = await App.uploadPicked(".docx,.pdf,.txt,.md,.html,.htm,.epub"); for (const u of ups) { const r = await App.api("import_as_sefer", { upload: u.upload, title: u.name.replace(/\.[^.]+$/, "") }); App.toast(`${u.name}: ${r.passages} paragraphs`); } Library.loadTree(); this.tab("seforim"); };
      $$("[data-w]", el).forEach(x => x.onclick = () => Library.open(+x.dataset.w));
      $$("[data-x]", el).forEach(x => x.onclick = () => Library.exportDialog({ work_id: +x.dataset.x, whole: true, title: x.dataset.t }));
      $$("[data-sh]", el).forEach(x => x.onclick = () => { App.show("share"); Share.preselect("works", +x.dataset.sh, x.dataset.t); });
      $$("[data-del]", el).forEach(x => x.onclick = async () => { if (await App.confirm("Remove this sefer from your library?")) { await App.api("delete_work", { work_id: +x.dataset.del }); this.tab("seforim"); Library.loadTree(); } });
    }
    if (t === "sheets") return Sheets.list(el);
    if (t === "covers") {
      const cs = await L("covers");
      el.innerHTML = `<div class="row"><button class="btn primary" id="pmCov">+ New cover</button></div>` + cs.map(c => `<div class="list-item row"><b style="flex:1" data-c="${c.id}">${esc(c.title)}</b><span class="small muted">${esc(c.updated)}</span><button class="btn small danger" data-del="${c.id}">🗑</button></div>`).join("");
      $("#pmCov").onclick = () => App.show("cover");
      $$("[data-c]", el).forEach(x => x.onclick = () => { App.show("cover"); Cover.load(+x.dataset.c); });
      $$("[data-del]", el).forEach(x => x.onclick = async () => { await App.api("ud_delete", { table: "covers", value: +x.dataset.del }); this.tab("covers"); });
    }
    if (t === "links") {
      const ls = await L("user_links");
      el.innerHTML = ls.map(l => `<div class="list-item row"><span style="flex:1"><a href="#" data-r="${esc(l.ref_a)}">${esc(l.ref_a)}</a> ↔ <a href="#" data-r="${esc(l.ref_b)}">${esc(l.ref_b)}</a> <span class="small muted">${esc(l.label)}</span></span><button class="btn small danger" data-del="${l.id}">🗑</button></div>`).join("") || "<p class='muted'>Link two sources from the reader with 🔗.</p>";
      $$("[data-r]", el).forEach(a => a.onclick = e => { e.preventDefault(); App.quickGo(a.dataset.r); });
      $$("[data-del]", el).forEach(x => x.onclick = async () => { await App.api("ud_delete", { table: "user_links", value: +x.dataset.del }); this.tab("links"); });
    }
    if (t === "hist") {
      const hs = await L("history", { limit: 300 });
      el.innerHTML = hs.map(x => `<div class="list-item" data-r="${esc(x.ref)}">${esc(x.ref)} <span class="small muted">${esc(x.ts)}</span></div>`).join("") || "<p class='muted'>Empty.</p>";
      $$("[data-r]", el).forEach(x => x.onclick = () => App.quickGo(x.dataset.r));
    }
  },
  async exportDocs(ids) {
    if (!ids.length) return App.toast("Tick some documents first");
    App.modal(`<h3>Export ${ids.length} document(s)</h3><div class="row">${["docx", "html", "txt", "md", "epub", "tei", "json"].map(f => `<button class="btn" data-f="${f}">${f.toUpperCase()}</button>`).join("")}<button class="btn" data-f="pkg">📦 .seforim package</button></div><div class="row" style="justify-content:flex-end;margin-top:10px"><button class="btn" data-close>Close</button></div>`, m => {
      m.onclick = async e => {
        const f = e.target.dataset.f; if (!f) return;
        if (f === "pkg") { const r = await App.api("package_export", { kind: "docs", ids, name: "my-documents" }); return App.download(r.url); }
        for (const id of ids) { const d = await App.api("ud_get", { table: "docs", id, pin: App.state.pin }); if (d.locked) continue; const r = await App.api("export_doc", { format: f, title: d.title, html: d.html, title_in_doc: true }); App.download(r.url); }
      };
    });
  },
  importDialog() {
    App.modal(`<h3>📥 Import</h3><p>Choose files (Word .docx, PDF, .txt, .md, .html, .epub, .json, .seforim packages, backup .zip).</p>
      <div class="col"><button class="btn" data-k="doc">As editable documents (Notes)</button><button class="btn" data-k="sefer">As searchable seforim (My Library)</button>
      <button class="btn" data-k="pkg">A .seforim package from another computer</button><button class="btn" data-k="json">My data file (.json from “Export all my data”)</button></div>
      <div class="row" style="justify-content:flex-end;margin-top:10px"><button class="btn" data-close>Close</button></div>`, m => {
      m.onclick = async e => {
        const k = e.target.dataset.k; if (!k) return; App.closeModal();
        const ups = await App.uploadPicked(k === "pkg" ? ".seforim,.zip" : k === "json" ? ".json" : ".docx,.pdf,.txt,.md,.html,.htm,.epub,.json");
        for (const u of ups) {
          if (k === "doc") { const r = await App.api("import_file", { upload: u.upload }); await App.api("ud_save", { table: "docs", row: { title: r.title, html: r.html, folder: "Imported" } }); }
          if (k === "sefer") await App.api("import_as_sefer", { upload: u.upload, title: u.name.replace(/\.[^.]+$/, "") });
          if (k === "pkg") { const r = await App.api("package_import", { upload: u.upload }); App.toast(`Imported ${r.count} ${r.kind}`); }
          if (k === "json") { const r = await App.api("import_user", { upload: u.upload }); App.toast(`Imported ${r.imported} items`); }
        }
        App.toast(`Imported ${ups.length} file(s)`); Library.loadTree(); this.tab(k === "sefer" ? "seforim" : "docs");
      };
    });
  }
};
App.register("mylib", { title: "My Library", icon: "🗂", render(el) { Personal.render(el); } });

const Sheets = {
  sheet: null,
  async list(el) {
    const ss = await App.api("ud_list", { table: "sheets", order: "updated DESC" });
    el.innerHTML = `<div class="row"><button class="btn primary" id="shNew">+ New source sheet</button></div>` + ss.map(s => `<div class="list-item row"><b style="flex:1" data-s="${s.id}">${esc(s.title)}</b><span class="small muted">${JSON.parse(s.items || "[]").length} items · ${esc(s.updated)}</span><button class="btn small danger" data-del="${s.id}">🗑</button></div>`).join("");
    $("#shNew").onclick = () => this.edit({ title: "New source sheet", items: [] });
    $$("[data-s]", el).forEach(x => x.onclick = () => this.open(+x.dataset.s));
    $$("[data-del]", el).forEach(x => x.onclick = async () => { await App.api("ud_delete", { table: "sheets", value: +x.dataset.del }); this.list(el); });
  },
  async open(id) { const s = await App.api("ud_get", { table: "sheets", id }); s.items = JSON.parse(s.items || "[]"); App.show("mylib"); Personal.tab("sheets").then(() => this.edit(s)); },
  async addSource(p) {
    const ss = await App.api("ud_list", { table: "sheets", order: "updated DESC" });
    App.modal(`<h3>Add ${esc(p.ref)} to a source sheet</h3><div class="col">${ss.map(s => `<button class="btn" data-s="${s.id}">${esc(s.title)}</button>`).join("")}<button class="btn primary" data-s="new">+ New sheet</button></div>`, m => {
      m.onclick = async e => {
        const id = e.target.dataset.s; if (!id) return;
        let s = id === "new" ? { title: (await App.prompt("Sheet title:", "Source sheet")) || "Source sheet", items: [] } : await App.api("ud_get", { table: "sheets", id: +id });
        if (typeof s.items === "string") s.items = JSON.parse(s.items || "[]");
        s.items.push({ type: "source", ref: p.ref, he: p.he, en: p.en });
        const r = await App.api("ud_save", { table: "sheets", row: { ...s, items: s.items } }); App.closeModal(); App.toast("Added to " + s.title);
      };
    });
  },
  edit(s) {
    this.sheet = s; const el = $("#pmBody");
    el.innerHTML = `<div class="row"><input id="shT" value="${esc(s.title)}" style="font-size:18px;flex:1"><button class="btn" id="shAddSrc">+ Source</button><button class="btn" id="shAddTxt">+ My text</button><button class="btn" id="shAddH">+ Header</button>
      <button class="btn primary" id="shSave">💾 Save</button><button class="btn" id="shExp">⤓ Word</button><button class="btn" id="shPrint">🖨</button></div>
      <p class="small muted">Drag items to reorder. Add sources from the Library with 📄 on any passage.</p><div id="shItems" class="card print-target"></div>`;
    const draw = () => {
      $("#shItems").innerHTML = `<h1 style="text-align:center">${esc($("#shT").value)}</h1>` + s.items.map((it, i) => `<div class="list-item" draggable="true" data-i="${i}" style="cursor:grab">
        ${it.type === "source" ? `<div class="small" style="color:var(--accent2)">${esc(it.ref)}</div><div class="he" style="font-size:20px">${esc(it.he || "")}</div>${it.en ? `<div class="en">${esc(it.en)}</div>` : ""}`
          : it.type === "header" ? `<h2 contenteditable data-e="${i}">${esc(it.text)}</h2>` : `<div contenteditable dir="auto" data-e="${i}" style="min-height:30px;border-left:3px solid var(--accent2);padding:4px 8px">${it.html || ""}</div>`}
        <div class="row small"><span class="spacer"></span><a href="#" data-up="${i}">↑</a><a href="#" data-dn="${i}">↓</a><a href="#" data-rm="${i}">remove</a></div></div>`).join("");
      $$("[data-e]").forEach(x => x.oninput = () => { const it = s.items[+x.dataset.e]; if (it.type === "header") it.text = x.textContent; else it.html = x.innerHTML; });
      $$("[data-rm]").forEach(a => a.onclick = e => { e.preventDefault(); s.items.splice(+a.dataset.rm, 1); draw(); });
      $$("[data-up]").forEach(a => a.onclick = e => { e.preventDefault(); const i = +a.dataset.up; if (i > 0) [s.items[i - 1], s.items[i]] = [s.items[i], s.items[i - 1]]; draw(); });
      $$("[data-dn]").forEach(a => a.onclick = e => { e.preventDefault(); const i = +a.dataset.dn; if (i < s.items.length - 1) [s.items[i + 1], s.items[i]] = [s.items[i], s.items[i + 1]]; draw(); });
      let from = null; $$("[draggable]").forEach(x => { x.ondragstart = () => from = +x.dataset.i; x.ondragover = e => e.preventDefault(); x.ondrop = e => { e.preventDefault(); const to = +x.dataset.i; const [m] = s.items.splice(from, 1); s.items.splice(to, 0, m); draw(); }; });
    };
    draw();
    $("#shT").oninput = () => draw();
    $("#shAddSrc").onclick = async () => { const ref = await App.prompt("Reference:"); if (!ref) return; const hit = await App.api("find_ref", { ref }); if (!hit) return App.toast("Not in library", true); const p = await App.api("passage", { id: hit.id }); s.items.push({ type: "source", ref: p.ref, he: p.he, en: p.en }); draw(); };
    $("#shAddTxt").onclick = () => { s.items.push({ type: "text", html: "" }); draw(); };
    $("#shAddH").onclick = () => { s.items.push({ type: "header", text: "כותרת" }); draw(); };
    $("#shSave").onclick = async () => { s.title = $("#shT").value; const r = await App.api("ud_save", { table: "sheets", row: { id: s.id, title: s.title, items: s.items } }); s.id = r.id; App.toast("Saved"); };
    const html = () => `${s.items.map(it => it.type === "source" ? `<blockquote dir="rtl"><span style="color:#8a6d3b;font-size:10pt">${esc(it.ref)}</span><br>${esc(it.he || "")}${it.en ? `<br><span dir="ltr">${esc(it.en)}</span>` : ""}</blockquote>` : it.type === "header" ? `<h2>${esc(it.text)}</h2>` : `<p>${it.html}</p>`).join("")}`;
    $("#shExp").onclick = async () => { const r = await App.api("export_doc", { format: "docx", title: $("#shT").value, html: html(), title_in_doc: true }); App.download(r.url); };
    $("#shPrint").onclick = () => { const x = $("#shItems"); x.classList.add("print-area"); window.print(); setTimeout(() => x.classList.remove("print-area"), 400); };
  }
};
