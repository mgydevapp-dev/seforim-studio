/* Notes: full Hebrew word processor — fonts, nikud shortcuts, abbreviation suggestions, auto gershayim & final letters,
   structure headings (Chelek/Siman/Seif/Seif Katan) with outline, two-lane footnotes, source insertion with citation,
   placeholders [???], style macros, bracket colouring, find/replace, transcription desk, autosave, import/export */
const NIKUD_KEYS = { "1": "ָ", "2": "ַ", "3": "ֵ", "4": "ֶ", "5": "ְ", "6": "ִ", "7": "ֹ", "8": "ֻ", "9": "ּ", "0": "ֲ", "-": "ֱ", "=": "ֳ", q: "ׁ", w: "ׂ", e: "ֿ", r: "ֽ", t: "־", y: "׳", u: "״" };
const TAAMIM_LIST = ["֑", "֒", "֓", "֔", "֕", "֖", "֗", "֘", "֙", "֚", "֛", "֜", "֝", "֞", "֟", "֠", "֡", "֣", "֤", "֥", "֦", "֧", "֨", "֩", "֪", "֫", "֬", "֭", "֮", "ֽ", "׀", "׃"];
const Notes = {
  doc: { id: null, title: "Untitled", folder: "My Notes", tags: "", private: 0 }, dirty: false, abbrevs: null,
  render(el) {
    const fonts = App.fontList();
    el.innerHTML = `<div class="editor-wrap">
      <div class="ed-toolbar" id="edTb">
        <button data-a="new" title="New">🗋</button><button data-a="open" title="Open">📂</button><button data-a="save" title="Save (Ctrl+S)">💾</button><button data-a="import" title="Import Word/PDF/text/HTML/EPUB">📥</button><button data-a="export" title="Export">📤</button><button data-a="print" title="Print / PDF">🖨</button>
        <span class="sep"></span>
        <select id="edFont" title="Font" style="width:150px">${fonts.map(f => `<option style="font-family:'${esc(f)}'">${esc(f)}</option>`).join("")}</select>
        <select id="edSize" title="Size">${[10, 12, 14, 16, 18, 20, 22, 24, 28, 32, 40, 48, 60].map(s => `<option ${s === 20 ? "selected" : ""}>${s}</option>`).join("")}</select>
        <button data-c="bold" title="Bold (Ctrl+B)"><b>B</b></button><button data-c="italic" title="Italic"><i>I</i></button><button data-c="underline" title="Underline"><u>U</u></button><button data-c="strikeThrough" title="Strike"><s>S</s></button>
        <input type="color" id="edColor" title="Text colour" value="#1b1b1b" style="width:30px;padding:0;border:0"><input type="color" id="edBg" title="Highlight" value="#ffe58a" style="width:30px;padding:0;border:0">
        <span class="sep"></span>
        <button data-c="justifyRight" title="Align right">⇥</button><button data-c="justifyCenter" title="Center">≡</button><button data-c="justifyLeft" title="Align left">⇤</button><button data-c="justifyFull" title="Justify">☰</button>
        <button data-a="rtl" title="Right-to-left paragraph">ע←</button><button data-a="ltr" title="Left-to-right paragraph">→E</button>
        <span class="sep"></span>
        <select id="edBlock" title="Structure"><option value="p">Paragraph</option><option value="h1">חלק / Chelek (H1)</option><option value="h2">סימן / Siman (H2)</option><option value="h3">סעיף / Seif (H3)</option><option value="h4">ס״ק / Seif Katan (H4)</option><option value="blockquote">Quote</option></select>
        <button data-c="insertUnorderedList" title="Bullets">•</button><button data-c="insertOrderedList" title="Numbers">1.</button><button data-c="insertHorizontalRule" title="Divider">―</button>
        <span class="sep"></span>
        <button data-a="nikud" title="Nikud & ta'amim (Alt+1…)">אָ</button><button data-a="chars" title="Special characters">״</button><button data-a="fn" title="Footnote">¹</button><button data-a="src" title="Insert a source from the library">📖</button>
        <button data-a="date" title="Insert Hebrew date">📅</button><button data-a="gem" title="Gematria of selection">🔢</button><button data-a="ph" title="Mark unreadable [???] (Ctrl+Shift+?)">[?]</button>
        <button data-a="srcStyle" title="Source style (Ctrl+1)">מקור</button><button data-a="commStyle" title="Commentary style (Ctrl+2)">פירוש</button><button data-a="brackets" title="Colour (brackets) and [insertions]">( )</button>
        <button data-a="clean" title="Clean pasted formatting / Unicode">🧹</button><button data-a="find" title="Find & replace (Ctrl+H)">🔍</button><button data-a="desk" title="Transcription desk: image beside text">🖼</button>
        <span class="spacer"></span><span class="small muted" id="edCount"></span>
      </div>
      <div class="ed-body">
        <div class="ed-outline" id="edOutline"></div>
        <div class="img-pane hidden" id="edImgs" style="width:45%"><div class="row" style="justify-content:center"><button class="btn small" id="edAddImg">Add images / PDF</button><label class="small" style="color:#ddd"><input type="checkbox" id="edSync" checked> lock scroll</label></div><div id="edImgList"></div></div>
        <div class="ed-page-wrap" id="edWrap"><div class="ed-page" id="edPage" contenteditable="true" spellcheck="false"><h1 data-ph="כותרת"><br></h1><p data-ph="התחל לכתוב כאן…"><br></p></div></div>
        <div class="ed-side"><b>Document</b>
          <label class="small muted">Title</label><input id="edTitle" style="width:100%">
          <label class="small muted">Folder</label><input id="edFolder" style="width:100%">
          <label class="small muted">Tags</label><input id="edTags" style="width:100%" placeholder="Halacha, Pesach 2026">
          <div class="row small" style="margin-top:6px"><label><input type="checkbox" id="edPriv"> 🔒 Private</label><label><input type="checkbox" id="edAuto" checked> Autosave</label></div>
          <div class="row small"><label><input type="checkbox" id="edGer" checked> Auto ״ ׳</label><label><input type="checkbox" id="edFin" checked> Auto final letters</label><label><input type="checkbox" id="edAb" checked> Abbreviation hints</label></div>
          <p class="small muted" id="edSaved"></p>
          <div class="row"><button class="btn small" id="edAsSefer">Add to My Library as a sefer</button><button class="btn small" id="edShare">📡 Share</button></div>
          <h2>My documents</h2><input id="edDocF" placeholder="filter…" style="width:100%"><div id="edDocs"></div></div>
      </div></div>`;
    const page = $("#edPage", el);
    $("#edTb", el).addEventListener("mousedown", e => { if (e.target.closest("button")) e.preventDefault(); });
    $("#edTb", el).onclick = e => { const b = e.target.closest("button"); if (!b) return; if (b.dataset.c) { document.execCommand(b.dataset.c); this.changed(); } else if (b.dataset.a) this.action(b.dataset.a); };
    $("#edFont", el).onchange = e => this.applyStyle("font-family", `'${e.target.value}'`);
    $("#edSize", el).onchange = e => this.applyStyle("font-size", e.target.value + "px");
    $("#edColor", el).oninput = e => { page.focus(); document.execCommand("foreColor", false, e.target.value); };
    $("#edBg", el).oninput = e => { page.focus(); document.execCommand("hiliteColor", false, e.target.value); };
    $("#edBlock", el).onchange = e => { page.focus(); document.execCommand("formatBlock", false, e.target.value); this.changed(); };
    page.addEventListener("input", e => { this.changed(); this.typingAids(e); });
    page.addEventListener("keydown", e => this.keys(e));
    page.addEventListener("paste", e => this.paste(e));
    page.addEventListener("click", e => { const fn = e.target.closest("sup.fn"); if (fn) this.editFootnote(fn); });
    ["edTitle", "edFolder", "edTags"].forEach(id => $("#" + id, el).oninput = () => this.changed());
    $("#edPriv", el).onchange = () => this.changed();
    $("#edDocF", el).oninput = () => this.listDocs();
    $("#edAsSefer", el).onclick = async () => { const r = await App.api("import_as_sefer", { title: $("#edTitle").value, html: page.innerHTML }); App.toast(`Added to My Library (${r.passages} paragraphs) — searchable now`); Library.loadTree(); };
    $("#edShare", el).onclick = async () => { await this.save(); App.show("share"); Share.preselect("docs", this.doc.id, this.doc.title); };
    $("#edAddImg", el).onclick = () => this.addImages();
    $("#edWrap", el).addEventListener("scroll", () => this.syncScroll("text"));
    $("#edImgs", el).addEventListener("scroll", () => this.syncScroll("img"));
    setInterval(() => { if (this.dirty && $("#edAuto") && $("#edAuto").checked && this.doc.id) this.save(true); }, 15000);
    this.setDoc(this.doc, page.innerHTML); this.listDocs(); this.outline();
    App.api("abbrevs").then(a => this.abbrevs = a);
  },
  page() { return $("#edPage"); },
  changed() { this.dirty = true; clearTimeout(this._ol); this._ol = setTimeout(() => { this.outline(); this.count(); }, 400); $("#edSaved").textContent = "Unsaved changes"; },
  applyStyle(prop, val) {
    const sel = window.getSelection(); if (!sel.rangeCount) return;
    const r = sel.getRangeAt(0);
    if (r.collapsed) { this.page().style.setProperty(prop, val); return this.changed(); }
    const span = document.createElement("span"); span.style.setProperty(prop, val);
    try { r.surroundContents(span); } catch (e) { span.appendChild(r.extractContents()); r.insertNode(span); }
    this.changed();
  },
  setDoc(d, html) {
    this.doc = { id: d.id || null, title: d.title || "Untitled", folder: d.folder || "My Notes", tags: d.tags || "", private: d.private || 0 };
    $("#edTitle").value = this.doc.title; $("#edFolder").value = this.doc.folder; $("#edTags").value = this.doc.tags; $("#edPriv").checked = !!this.doc.private;
    if (html != null) this.page().innerHTML = html;
    this.dirty = false; this.outline(); this.count(); $("#edSaved").textContent = d.updated ? "Saved " + d.updated : "";
  },
  async save(silent) {
    const row = { id: this.doc.id, title: $("#edTitle").value || "Untitled", folder: $("#edFolder").value || "My Notes", tags: $("#edTags").value, private: $("#edPriv").checked ? 1 : 0, html: this.page().innerHTML, kind: "note" };
    const r = await App.api("ud_save", { table: "docs", row });
    this.doc.id = r.id; this.doc.title = row.title; this.dirty = false;
    $("#edSaved").textContent = "Saved " + new Date().toLocaleTimeString(); if (!silent) App.toast("Saved"); this.listDocs();
  },
  async listDocs() {
    const docs = await App.api("ud_list", { table: "docs", order: "updated DESC" });
    const f = ($("#edDocF")?.value || "").toLowerCase();
    $("#edDocs").innerHTML = docs.filter(d => !f || (d.title + d.tags + d.folder).toLowerCase().includes(f)).map(d => `<div class="list-item small" data-id="${d.id}"><b>${d.private ? "🔒 " : ""}${esc(d.title)}</b><div class="muted">${esc(d.folder)} · ${esc(d.updated)}</div></div>`).join("") || "<p class='small muted'>No documents yet.</p>";
    $$("#edDocs [data-id]").forEach(x => x.onclick = () => this.openDoc(+x.dataset.id));
  },
  async openDoc(id) {
    App.show("notes");
    let d = await App.api("ud_get", { table: "docs", id, pin: App.state.pin });
    if (d && d.locked) { const pin = await App.prompt("This document is private. Enter your PIN:", "", { type: "password" }); if (pin == null) return; App.state.pin = pin; d = await App.api("ud_get", { table: "docs", id, pin }); if (d.locked) return App.toast("Wrong PIN", true); App.state.unlocked = true; }
    this.setDoc(d, d.html);
  },
  openWithHtml(title, html) { App.show("notes"); this.setDoc({ title }, html); this.dirty = true; },
  outline() {
    const hs = $$("h1,h2,h3,h4", this.page());
    $("#edOutline").innerHTML = `<b class="small">Outline</b>` + (hs.map((x, i) => `<div class="list-item small" data-i="${i}" style="padding-right:${(+x.tagName[1] - 1) * 12}px;direction:rtl;font-family:var(--he-font);font-size:15px">${esc(x.textContent.slice(0, 50) || "—")}</div>`).join("") || `<p class="small muted">Use the Structure menu (חלק / סימן / סעיף) to build a navigation tree.</p>`);
    $$("#edOutline [data-i]").forEach(x => x.onclick = () => hs[+x.dataset.i].scrollIntoView({ behavior: "smooth", block: "start" }));
    this.renumberFootnotes();
  },
  count() { const t = this.page().innerText; const words = (t.match(/\S+/g) || []).length; $("#edCount").textContent = `${words} words · ${t.replace(/\s/g, "").length} chars`; },

  /* --- typing aids --- */
  typingAids(e) {
    if (e.inputType !== "insertText" || !e.data) return;
    const sel = window.getSelection(); const node = sel.anchorNode; if (!node || node.nodeType !== 3) return;
    const off = sel.anchorOffset, txt = node.textContent;
    if ($("#edGer").checked && (e.data === '"' || e.data === "'") && /[א-ת]/.test(txt[off - 2] || "")) {
      const rep = e.data === '"' ? "״" : "׳";
      node.textContent = txt.slice(0, off - 1) + rep + txt.slice(off); this.caret(node, off);
    }
    if ($("#edFin").checked && /[\s.,:;!?)]/.test(e.data)) {
      const before = node.textContent.slice(0, off - 1); const m = before.match(/([א-ת][ְ-ׇ]*)+$/);
      if (m) { const fin = { "כ": "ך", "מ": "ם", "נ": "ן", "פ": "ף", "צ": "ץ" }; const w = m[0]; const letters = w.replace(/[ְ-ׇ]/g, "");
        if (letters.length > 1) { const last = [...w].reverse().findIndex(c => fin[c]); const li = w.length - 1 - last;
          if (last >= 0 && /^[ְ-ׇ]*$/.test(w.slice(li + 1))) { const nw = w.slice(0, li) + fin[w[li]] + w.slice(li + 1); node.textContent = before.slice(0, before.length - w.length) + nw + node.textContent.slice(off - 1); this.caret(node, off); } } }
    }
    if ($("#edAb").checked && this.abbrevs) {
      const before = node.textContent.slice(0, sel.anchorOffset); const m = before.match(/([א-ת]+[״"׳'][א-ת]*)$/);
      if (m) { const key = m[1].replace(/[^א-ת]/g, "").replace(/[ךםןףץ]/g, c => ({ "ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ" }[c])); const full = this.abbrevs[key]; if (full) this.suggest(full, m[1], node); else this.hideSuggest(); }
      else this.hideSuggest();
    }
  },
  caret(node, off) { const r = document.createRange(); r.setStart(node, Math.min(off, node.textContent.length)); r.collapse(true); const s = window.getSelection(); s.removeAllRanges(); s.addRange(r); },
  suggest(full, abbr, node) {
    let s = $("#edSuggest"); if (!s) { s = h(`<div class="suggest" id="edSuggest"></div>`); document.body.appendChild(s); }
    const rect = window.getSelection().getRangeAt(0).getBoundingClientRect();
    s.style.left = Math.max(10, rect.left - 220) + "px"; s.style.top = (rect.bottom + 6) + "px";
    s.innerHTML = `<div class="sel" data-v="${esc(full)}">${esc(full)} <span class="small muted">Tab ↹ to expand</span></div><div data-keep="1" class="small">keep ${esc(abbr)}</div>`;
    this._sugg = { full, abbr, node };
    s.onmousedown = e => { e.preventDefault(); if (e.target.closest("[data-v]")) this.acceptSuggest(); else this.hideSuggest(); };
  },
  hideSuggest() { const s = $("#edSuggest"); if (s) s.remove(); this._sugg = null; },
  acceptSuggest() {
    const g = this._sugg; if (!g) return; const sel = window.getSelection(); const node = sel.anchorNode, off = sel.anchorOffset;
    const t = node.textContent; const start = t.lastIndexOf(g.abbr, off);
    if (start >= 0) { node.textContent = t.slice(0, start) + g.full + t.slice(start + g.abbr.length); this.caret(node, start + g.full.length); }
    this.hideSuggest(); this.changed();
  },
  keys(e) {
    if (this._sugg && e.key === "Tab") { e.preventDefault(); return this.acceptSuggest(); }
    if (e.key === "Escape") this.hideSuggest();
    if (e.altKey && !e.ctrlKey && NIKUD_KEYS[e.key.toLowerCase()]) { e.preventDefault(); App.insertText(NIKUD_KEYS[e.key.toLowerCase()]); return; }
    if (e.ctrlKey && e.key.toLowerCase() === "s") { e.preventDefault(); this.save(); }
    if (e.ctrlKey && e.key === "1") { e.preventDefault(); this.action("srcStyle"); }
    if (e.ctrlKey && e.key === "2") { e.preventDefault(); this.action("commStyle"); }
    if (e.ctrlKey && e.key.toLowerCase() === "h") { e.preventDefault(); this.action("find"); }
    if (e.ctrlKey && e.shiftKey && (e.key === "?" || e.key === "/")) { e.preventDefault(); this.action("ph"); }
  },
  paste(e) {
    const html = e.clipboardData.getData("text/html");
    if (!html || App.state.settings.keep_paste_format) return;
    e.preventDefault();
    const d = document.createElement("div"); d.innerHTML = html;
    d.querySelectorAll("style,script,meta,link,o\\:p,xml").forEach(x => x.remove());
    d.querySelectorAll("*").forEach(x => { [...x.attributes].forEach(a => { if (!["href", "dir"].includes(a.name)) x.removeAttribute(a.name); }); if (/^(SPAN|FONT)$/.test(x.tagName)) x.replaceWith(...x.childNodes); });
    document.execCommand("insertHTML", false, d.innerHTML.replace(/[​-‍﻿‪-‮]/g, ""));
  },
  wrapSel(cls) {
    const sel = window.getSelection(); if (!sel.rangeCount) return;
    let blk = sel.anchorNode; while (blk && blk !== this.page() && !/^(P|H\d|LI|BLOCKQUOTE|DIV)$/.test(blk.nodeName)) blk = blk.parentNode;
    if (blk && blk !== this.page()) { blk.classList.remove("src-style", "comm-style"); blk.classList.add(cls); this.changed(); }
  },
  async action(a) {
    const page = this.page();
    const act = {
      new: async () => { if (this.dirty && !await App.confirm("Discard unsaved changes?")) return; this.setDoc({}, "<h1></h1><p><br></p>"); },
      open: () => this.listDocs() && $("#edDocF").focus(),
      save: () => this.save(),
      import: async () => { const ups = await App.uploadPicked(".docx,.txt,.md,.html,.htm,.pdf,.epub,.json", false); if (!ups.length) return; const r = await App.api("import_file", { upload: ups[0].upload }); this.setDoc({ title: r.title }, r.html); this.dirty = true; App.toast("Imported " + r.title); },
      export: () => this.exportDialog(),
      print: () => { page.classList.add("print-area"); window.print(); setTimeout(() => page.classList.remove("print-area"), 400); },
      rtl: () => this.setDir("rtl"), ltr: () => this.setDir("ltr"),
      nikud: () => this.nikudPalette(),
      chars: () => this.charsPalette(),
      fn: () => this.addFootnote(),
      src: async () => {
        const ref = await App.prompt("Source reference (e.g. Genesis 1:1, Berakhot 2a:1):"); if (!ref) return;
        const hit = await App.api("find_ref", { ref }); if (!hit) return App.toast("Not found in your library", true);
        const p = await App.api("passage", { id: hit.id }); page.focus();
        document.execCommand("insertHTML", false, `<blockquote class="src-style" dir="rtl">${esc(p.he)}${p.en ? `<br><span dir="ltr" style="font-size:.8em">${esc(p.en)}</span>` : ""}<br><span style="font-size:.7em;color:#8a6d3b">— ${esc(p.ref)}</span></blockquote><p><br></p>`);
      },
      date: async () => { const d = await App.api("dashboard"); page.focus(); App.insertText(d.hebrew); },
      gem: async () => { const s = String(window.getSelection()); if (!s) return App.toast("Select some Hebrew first"); const r = await App.api("gematria_value", { text: s }); App.toast(`${s} = ${r.methods["Standard (Mispar Hechrachi)"]} (gadol ${r.methods["Gadol (finals 500-900)"]}, katan ${r.methods["Katan (small, no zeros)"]})`); },
      ph: () => { page.focus(); document.execCommand("insertHTML", false, `<span class="placeholder-mark">[???]</span>&nbsp;`); },
      srcStyle: () => this.wrapSel("src-style"), commStyle: () => this.wrapSel("comm-style"),
      brackets: () => { page.classList.toggle("color-brackets"); this.colorBrackets(page.classList.contains("color-brackets")); },
      clean: async () => { const r = await App.api("tool_run", { id: "clean_unicode", args: { text: page.innerHTML } }); page.innerHTML = r.result; this.changed(); App.toast("Cleaned hidden characters"); },
      find: () => this.findReplace(),
      desk: () => $("#edImgs").classList.toggle("hidden"),
    }[a];
    if (act) await act();
  },
  setDir(d) { const sel = window.getSelection(); let n = sel.anchorNode; while (n && n !== this.page() && !/^(P|H\d|LI|BLOCKQUOTE|DIV)$/.test(n.nodeName)) n = n.parentNode; if (n && n !== this.page()) { n.dir = d; n.style.textAlign = d === "rtl" ? "right" : "left"; this.changed(); } },
  colorBrackets(on) {
    const page = this.page();
    $$("span.br-round,span.br-square", page).forEach(s => s.replaceWith(...s.childNodes));
    if (!on) return;
    const walker = document.createTreeWalker(page, NodeFilter.SHOW_TEXT); const nodes = []; while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const n of nodes) { if (!/[()\[\]]/.test(n.textContent)) continue; const span = document.createElement("span");
      span.innerHTML = esc(n.textContent).replace(/\(([^()]*)\)/g, '<span class="br-round">($1)</span>').replace(/\[([^\[\]]*)\]/g, '<span class="br-square">[$1]</span>'); n.replaceWith(...span.childNodes); }
  },
  nikudPalette() {
    const names = ["Kamatz", "Patach", "Tzere", "Segol", "Sheva", "Chirik", "Cholam", "Kubutz", "Dagesh", "Chataf Patach", "Chataf Segol", "Chataf Kamatz", "Shin dot", "Sin dot", "Rafe", "Meteg", "Maqaf", "Geresh", "Gershayim"];
    App.modal(`<h3>Nikud & ta'amim</h3><p class="small muted">Click to insert after the letter before the cursor — or use Alt + key while typing.</p>
      <div class="row">${Object.entries(NIKUD_KEYS).map(([k, m], i) => `<button class="btn" data-m="${m}" title="${names[i]} — Alt+${k}" style="font-family:var(--he-font);font-size:22px">ב${m}<div class="small muted" style="font-family:var(--ui-font)">Alt+${k}</div></button>`).join("")}</div>
      <h3 style="margin-top:12px">Ta'amim (cantillation)</h3><div class="row">${TAAMIM_LIST.map(m => `<button class="btn" data-m="${m}" style="font-family:var(--he-font);font-size:22px">א${m}</button>`).join("")}</div>
      <div class="row" style="justify-content:flex-end;margin-top:10px"><button class="btn" data-close>Close</button></div>`, m => {
      m.addEventListener("mousedown", e => e.preventDefault());
      m.onclick = e => { const b = e.target.closest("[data-m]"); if (b) { this.page().focus(); App.insertText(b.dataset.m); } };
    });
  },
  charsPalette() {
    const ch = ["״", "׳", "־", "׃", "׀", "₪", "§", "¶", "†", "•", "…", "–", "—", "«", "»", "„", "“", "”", "‹", "›", "{פ}", "{ס}", "ﬠ", "ﭏ", "יְהוָה", "ה׳", "ד׳", "אלקים", "ב״ה", "בס״ד", "זצ״ל", "שליט״א", "ע״ה", "ז״ל"];
    App.modal(`<h3>Special characters & phrases</h3><div class="row">${ch.map(c => `<button class="btn" data-m="${esc(c)}" style="font-family:var(--he-font);font-size:20px">${esc(c)}</button>`).join("")}</div><div class="row" style="justify-content:flex-end;margin-top:10px"><button class="btn" data-close>Close</button></div>`, m => {
      m.addEventListener("mousedown", e => e.preventDefault());
      m.onclick = e => { const b = e.target.closest("[data-m]"); if (b) { this.page().focus(); App.insertText(b.dataset.m); } };
    });
  },
  async addFootnote() {
    const sel = window.getSelection(); const range = sel.rangeCount ? sel.getRangeAt(0).cloneRange() : null;
    App.modal(`<h3>Footnote</h3><label>Lane <select id="fnL"><option value="src">Sources (מקורות)</option><option value="note">Notes (הערות)</option></select></label><textarea id="fnT" class="he-input" dir="auto"></textarea>
      <div class="row" style="justify-content:flex-end"><button class="btn" data-close>Cancel</button><button class="btn primary" id="fnOk">Insert</button></div>`, m => {
      $("#fnT", m).focus();
      $("#fnOk", m).onclick = () => {
        const sup = document.createElement("sup"); sup.className = "fn"; sup.dataset.lane = $("#fnL", m).value; sup.dataset.text = $("#fnT", m).value; sup.textContent = "*";
        App.closeModal(); if (range) { range.collapse(false); range.insertNode(sup); } else this.page().appendChild(sup);
        this.renumberFootnotes(); this.changed();
      };
    });
  },
  editFootnote(sup) {
    App.modal(`<h3>Edit footnote</h3><textarea id="fnT" class="he-input" dir="auto">${esc(sup.dataset.text)}</textarea><div class="row"><button class="btn danger" id="fnDel">Delete</button><span class="spacer"></span><button class="btn" data-close>Cancel</button><button class="btn primary" id="fnOk">Save</button></div>`, m => {
      $("#fnOk", m).onclick = () => { sup.dataset.text = $("#fnT", m).value; App.closeModal(); this.renumberFootnotes(); this.changed(); };
      $("#fnDel", m).onclick = () => { sup.remove(); App.closeModal(); this.renumberFootnotes(); this.changed(); };
    });
  },
  renumberFootnotes() {
    const page = this.page(); if (!page) return;
    $$(".footnotes", page).forEach(x => x.remove());
    const sups = $$("sup.fn", page); if (!sups.length) return;
    const lanes = { src: [], note: [] };
    sups.forEach(s => { const L = lanes[s.dataset.lane] || lanes.note; L.push(s); s.textContent = s.dataset.lane === "src" ? App.heNum(L.length).replace(/[״׳]/g, "") : String(L.length); });
    const block = (title, L, src) => L.length ? `<div><b>${title}</b>${L.map((s, i) => `<div>${src ? App.heNum(i + 1).replace(/[״׳]/g, "") : i + 1}. ${esc(s.dataset.text)}</div>`).join("")}</div>` : "";
    page.insertAdjacentHTML("beforeend", `<div class="footnotes" contenteditable="false">${block("מקורות", lanes.src, true)}${block("הערות", lanes.note, false)}</div>`);
  },
  findReplace() {
    App.modal(`<h3>Find & replace</h3><div class="col"><input id="frF" placeholder="Find (ignores nikud)" dir="auto"><input id="frR" placeholder="Replace with" dir="auto"><label class="small"><input type="checkbox" id="frN" checked> Ignore nikud</label></div>
      <div class="row" style="margin-top:10px"><span id="frC" class="small muted"></span><span class="spacer"></span><button class="btn" id="frFind">Count</button><button class="btn primary" id="frAll">Replace all</button><button class="btn" data-close>Close</button></div>`, m => {
      const run = replace => {
        const f = $("#frF", m).value; if (!f) return;
        const ign = $("#frN", m).checked; const pat = [...f].map(c => c.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + (ign && /[א-ת]/.test(c) ? "[\\u0591-\\u05C7]*" : "")).join("");
        const rx = new RegExp(pat, "g"); let n = 0;
        const walker = document.createTreeWalker(this.page(), NodeFilter.SHOW_TEXT); const nodes = []; while (walker.nextNode()) nodes.push(walker.currentNode);
        for (const node of nodes) { const t = node.textContent; const c = (t.match(rx) || []).length; n += c; if (replace && c) node.textContent = t.replace(rx, $("#frR", m).value); }
        $("#frC", m).textContent = `${n} found${replace ? " and replaced" : ""}`; if (replace) this.changed();
      };
      $("#frFind", m).onclick = () => run(false); $("#frAll", m).onclick = () => run(true);
    });
  },
  exportDialog() {
    App.modal(`<h3>Export “${esc($("#edTitle").value)}”</h3><div class="row">${["docx", "html", "txt", "md", "epub", "tei", "json"].map(f => `<button class="btn" data-f="${f}">${f.toUpperCase()}</button>`).join("")}<button class="btn gold" data-f="print">🖨 PDF / Print</button></div>
      <div class="row small" style="margin-top:8px"><label>Word font <select id="exF">${App.fontList().map(f => `<option ${f === "David" ? "selected" : ""}>${esc(f)}</option>`).join("")}</select></label><label>Size <input type="number" id="exS" value="14" style="width:60px"></label><label><input type="checkbox" id="exT"> Title at top</label></div>
      <div class="row" style="justify-content:flex-end;margin-top:10px"><button class="btn" data-close>Close</button></div>`, m => {
      m.onclick = async e => {
        const f = e.target.dataset.f; if (!f) return;
        if (f === "print") { App.closeModal(); return this.action("print"); }
        const r = await App.api("export_doc", { format: f, title: $("#edTitle").value || "document", html: this.page().innerHTML, font: $("#exF", m).value, size: +$("#exS", m).value, title_in_doc: $("#exT", m).checked });
        App.download(r.url); App.toast("Exported " + r.name);
      };
    });
  },
  async addImages(urls) {
    if (!urls) {
      const ups = await App.uploadPicked("image/*,.pdf");
      if (!ups.length) return;
      const { job } = await App.api("scan_start", { uploads: ups.map(u => u.upload), opts: { crop: false, deskew: false, shadows: false, faint: false, denoise: false, specks: false, lines: false } });
      const res = await App.job(job); urls = res.pages.map(p => p.urls.original);
    }
    $("#edImgs").classList.remove("hidden");
    $("#edImgList").innerHTML += urls.map(u => `<img src="${App.fileUrl(u)}">`).join("");
  },
  syncScroll(src) {
    if (!$("#edSync").checked || $("#edImgs").classList.contains("hidden") || this._syncing) return;
    const a = $("#edWrap"), b = $("#edImgs"); const [from, to] = src === "text" ? [a, b] : [b, a];
    this._syncing = true; to.scrollTop = (from.scrollTop / Math.max(1, from.scrollHeight - from.clientHeight)) * (to.scrollHeight - to.clientHeight);
    requestAnimationFrame(() => this._syncing = false);
  }
};
App.register("notes", { title: "Notes", icon: "✍️", full: true, render(el) { Notes.render(el); } });
