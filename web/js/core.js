/* Seforim Studio — core: API, pages, i18n, Hebrew keyboard, on-screen keyboard, clipboard catcher, themes */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const h = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; };
const isHeb = s => /[א-ת]/.test(s || "");

// physical key (works whatever Windows keyboard language is active) -> Hebrew letter, standard Israeli layout
const CODE_TO_HE = { KeyQ: "/", KeyW: "'", KeyE: "ק", KeyR: "ר", KeyT: "א", KeyY: "ט", KeyU: "ו", KeyI: "ן", KeyO: "ם", KeyP: "פ",
  KeyA: "ש", KeyS: "ד", KeyD: "ג", KeyF: "כ", KeyG: "ע", KeyH: "י", KeyJ: "ח", KeyK: "ל", KeyL: "ך", Semicolon: "ף", Quote: ",",
  KeyZ: "ז", KeyX: "ס", KeyC: "ב", KeyV: "ה", KeyB: "נ", KeyN: "מ", KeyM: "צ", Comma: "ת", Period: "ץ", Slash: ".", Backquote: ";" };
const FINAL_OF = { "כ": "ך", "מ": "ם", "נ": "ן", "פ": "ף", "צ": "ץ" };
const EN_TO_HE = { q: "/", w: "'", e: "ק", r: "ר", t: "א", y: "ט", u: "ו", i: "ן", o: "ם", p: "פ", a: "ש", s: "ד", d: "ג", f: "כ", g: "ע", h: "י", j: "ח", k: "ל", l: "ך", ";": "ף", "'": ",", z: "ז", x: "ס", c: "ב", v: "ה", b: "נ", n: "מ", m: "צ", ",": "ת", ".": "ץ", "/": ".", "`": ";" };

const I18N = {
  he: { Home: "בית", Library: "ספרייה", Search: "חיפוש", Gematria: "גימטריה", "Roshei Teivos": "ראשי תיבות", Analysis: "ניתוח", Tools: "כלים", Calendar: "לוח שנה",
    Notes: "כתיבה", "My Library": "הספרייה שלי", Sheets: "דפי מקורות", Covers: "כריכות", Scanner: "סורק", Share: "שיתוף", Settings: "הגדרות", Search_: "חפש",
    "Quick search or go to (e.g. Genesis 1:1, בראשית, אור)…": "חיפוש מהיר או מעבר למקור…" },
  fr: { Home: "Accueil", Library: "Bibliothèque", Search: "Recherche", Gematria: "Guématria", "Roshei Teivos": "Acronymes", Analysis: "Analyse", Tools: "Outils",
    Calendar: "Calendrier", Notes: "Notes", "My Library": "Ma bibliothèque", Sheets: "Feuilles", Covers: "Couvertures", Scanner: "Scanner", Share: "Partager", Settings: "Réglages",
    "Quick search or go to (e.g. Genesis 1:1, בראשית, אור)…": "Recherche rapide ou référence…" }
};

const App = {
  pages: {}, order: [], current: null, state: { heb: false, settings: {}, status: {}, unlocked: false, pin: "" }, lastFocus: null,

  t(s) { const l = this.state.settings.ui_lang || "en"; return (I18N[l] && I18N[l][s]) || s; },

  async api(name, args = {}) {
    const r = await fetch("/api/" + name, { method: "POST", headers: { "Content-Type": "application/json", "X-Token": TOKEN }, body: JSON.stringify(args) });
    const js = await r.json().catch(() => ({ error: "Bad response" }));
    if (!r.ok || (js && js.error && typeof js === "object" && !Array.isArray(js) && Object.keys(js).length === 1)) {
      const msg = (js && js.error) || r.statusText; this.toast(msg, true); throw new Error(msg);
    }
    return js;
  },
  async upload(file) {
    const r = await fetch("/upload", { method: "POST", headers: { "X-Token": TOKEN, "X-Filename": encodeURIComponent(file.name) }, body: file });
    return r.json();
  },
  fileUrl(u, download) { if (!u) return u; return u + (u.includes("?") ? "&" : "?") + "t=" + TOKEN + (download ? "&dl=1" : ""); },
  download(u) { const a = document.createElement("a"); a.href = this.fileUrl(u, true); a.download = ""; document.body.appendChild(a); a.click(); a.remove(); },
  async job(id, onProgress) {
    while (true) {
      const s = await this.api("job", { id });
      if (onProgress) onProgress(s);
      if (s.done) { if (s.error) { this.toast(s.error, true); throw new Error(s.error); } return s.result; }
      await new Promise(r => setTimeout(r, 600));
    }
  },
  toast(msg, err) { const t = h(`<div class="toast ${err ? "err" : ""}">${esc(msg)}</div>`); $("#toasts").appendChild(t); setTimeout(() => t.remove(), err ? 6000 : 3200); },
  modal(html, onReady) {
    $("#modal").innerHTML = html; $("#modalWrap").classList.remove("hidden");
    $$("[data-close]", $("#modal")).forEach(b => b.onclick = () => this.closeModal());
    if (onReady) onReady($("#modal"));
  },
  closeModal() { $("#modalWrap").classList.add("hidden"); $("#modal").innerHTML = ""; },
  prompt(title, value = "", opts = {}) {
    return new Promise(res => {
      this.modal(`<h3>${esc(title)}</h3>${opts.textarea ? `<textarea id="pIn" class="${opts.he ? "he-input" : ""}" style="min-height:160px">${esc(value)}</textarea>`
        : `<input id="pIn" type="${opts.type || "text"}" style="width:100%" class="${opts.he ? "he-input" : ""}" value="${esc(value)}">`}
        ${opts.help ? `<p class="small muted">${opts.help}</p>` : ""}
        <div class="row" style="margin-top:12px;justify-content:flex-end"><button class="btn" id="pCancel">Cancel</button><button class="btn primary" id="pOk">OK</button></div>`, m => {
        const i = $("#pIn", m); i.focus(); i.select && i.select();
        $("#pOk", m).onclick = () => { const v = i.value; this.closeModal(); res(v); };
        $("#pCancel", m).onclick = () => { this.closeModal(); res(null); };
        i.onkeydown = e => { if (e.key === "Enter" && !opts.textarea) $("#pOk", m).click(); if (e.key === "Escape") $("#pCancel", m).click(); };
      });
    });
  },
  confirm(msg) { return new Promise(res => this.modal(`<h3>Please confirm</h3><p>${esc(msg)}</p><div class="row" style="justify-content:flex-end"><button class="btn" id="cN">Cancel</button><button class="btn primary" id="cY">Yes</button></div>`,
    m => { $("#cY", m).onclick = () => { this.closeModal(); res(true); }; $("#cN", m).onclick = () => { this.closeModal(); res(false); }; })); },
  pickFiles(accept, multiple = true) {
    return new Promise(res => { const i = document.createElement("input"); i.type = "file"; i.accept = accept || ""; i.multiple = multiple; i.onchange = () => res([...i.files]); i.click(); });
  },
  async uploadPicked(accept, multiple = true) { const files = await this.pickFiles(accept, multiple); const out = []; for (const f of files) out.push(await this.upload(f)); return out; },

  /* ---------------- pages ---------------- */
  register(id, def) { this.pages[id] = def; this.order.push(id); },
  show(id, arg) {
    const p = this.pages[id]; if (!p) return;
    if (!p.el) { p.el = h(`<div class="page ${p.full ? "full" : ""}" id="page-${id}"></div>`); $("#pages").appendChild(p.el); p.render(p.el); }
    $$(".page").forEach(e => e.classList.remove("active")); p.el.classList.add("active");
    $$("#rail button").forEach(b => b.classList.toggle("active", b.dataset.id === id));
    this.current = id; if (p.onShow) p.onShow(arg);
    this.saveSession();
  },
  buildRail() {
    const r = $("#rail"); r.innerHTML = "";
    const order = [...this.order.filter(i => i !== "plugins" && i !== "settings"), "plugins", "settings"].filter(i => this.pages[i]);
    for (const id of order) {
      const p = this.pages[id];
      const b = h(`<button data-id="${id}" title="${esc(p.title)}"><span class="ic">${p.icon}</span><span>${esc(this.t(p.title))}</span></button>`);
      b.onclick = () => this.show(id); r.appendChild(b);
    }
  },

  /* ---------------- Hebrew keyboard (English keys type Hebrew) ---------------- */
  setHeb(on) {
    this.state.heb = on; $("#kbToggle").classList.toggle("on", on);
    $("#kbToggle").textContent = on ? "⌨ עברית" : "⌨ EN → עב";
    this.status(on ? "Keyboard: Hebrew (English keys type Hebrew letters · Shift = English capital · Ctrl+Shift+K or Alt+Shift to switch)" : "Keyboard: normal");
    try { localStorage.setItem("heb_kb", on ? "1" : "0"); } catch (e) { }
  },
  isTypingTarget(el) {
    if (!el) return false;
    if (el.isContentEditable) return true;
    return (el.tagName === "TEXTAREA") || (el.tagName === "INPUT" && /^(text|search)$/.test(el.type || "text"));
  },
  insertText(text, target) {
    const el = target || document.activeElement;
    if (el && el.focus && document.activeElement !== el) el.focus();
    // execCommand keeps Ctrl+Z (undo) working; setRangeText is the fallback
    if (document.execCommand("insertText", false, text)) return;
    if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA")) {
      const s = el.selectionStart ?? el.value.length, e = el.selectionEnd ?? s; el.setRangeText(text, s, e, "end"); el.dispatchEvent(new Event("input", { bubbles: true }));
    }
  },
  /* the letter just before the caret (for automatic final letters) */
  prevChar(el) {
    if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") { const i = el.selectionStart; return i > 0 && i === el.selectionEnd ? el.value[i - 1] + (el.value[i - 2] || "") : ""; }
    const sel = getSelection(); if (!sel.rangeCount || !sel.isCollapsed) return "";
    const n = sel.anchorNode, o = sel.anchorOffset; return n && n.nodeType === 3 && o > 0 ? n.data[o - 1] + (n.data[o - 2] || "") : "";
  },
  fixFinal(el) {
    if (this.state.settings && this.state.settings.auto_finals === "0") return;
    const pc = this.prevChar(el), last = pc[0], before = pc[1];
    if (last && FINAL_OF[last] && before && /[\u05d0-\u05ea]/.test(before)) { document.execCommand("delete"); this.insertText(FINAL_OF[last], el); }
  },
  initKeyboard() {
    try { if (localStorage.getItem("heb_kb") === "1") setTimeout(() => this.setHeb(true), 0); } catch (e) { }
    document.addEventListener("keydown", e => {
      if (e.ctrlKey && e.shiftKey && (e.key === "K" || e.key === "k" || e.code === "KeyK")) { e.preventDefault(); this.setHeb(!this.state.heb); return; }
      if (e.altKey && e.shiftKey && !e.ctrlKey) { e.preventDefault(); this.setHeb(!this.state.heb); return; }  // Alt+Shift like Windows
      if (e.key === "Escape" && document.body.classList.contains("focus")) { document.body.classList.remove("focus"); return; }
      const t = e.target; if (!this.isTypingTarget(t) || t.classList.contains("no-heb")) return;
      const hebTyping = this.state.heb || /[\u05d0-\u05ea]/.test(e.key);
      // final letters: כ→ך מ→ם נ→ן פ→ף צ→ץ when a word ends
      const mapped = this.state.heb && !e.shiftKey ? CODE_TO_HE[e.code] : null;  // e.g. "," types ת in Hebrew mode - not the end of a word
      if (hebTyping && !e.ctrlKey && !e.altKey && !(mapped && /[\u05d0-\u05ea]/.test(mapped)) && (e.key === " " || e.key === "Enter" || /^[.,;:!?)\]"'״׳-]$/.test(e.key))) this.fixFinal(t);
      if (!this.state.heb || e.ctrlKey || e.altKey || e.metaKey || e.shiftKey) return;  // Shift+key still types English capitals
      const ch = CODE_TO_HE[e.code] || EN_TO_HE[(e.key || "").toLowerCase()];
      if (ch && e.key.length === 1) { e.preventDefault(); this.insertText(ch, t); }
    }, true);
    document.addEventListener("focusin", e => { if (this.isTypingTarget(e.target) && !e.target.closest("#osk")) this.lastFocus = e.target; });
    $("#kbToggle").onclick = () => this.setHeb(!this.state.heb);
    // top-bar buttons must not steal focus from the text you are typing in
    $$(".top-actions button").forEach(b => b.addEventListener("mousedown", e => e.preventDefault()));
  },
  initOSK() {
    const rows = [["/", "'", "ק", "ר", "א", "ט", "ו", "ן", "ם", "פ"], ["ש", "ד", "ג", "כ", "ע", "י", "ח", "ל", "ך", "ף"], ["ז", "ס", "ב", "ה", "נ", "מ", "צ", "ת", "ץ", "."]];
    const nikud = [["ְ", "Sheva"], ["ֱ", "Chataf segol"], ["ֲ", "Chataf patach"], ["ֳ", "Chataf kamatz"], ["ִ", "Chirik"], ["ֵ", "Tzeirei"], ["ֶ", "Segol"],
      ["ַ", "Patach"], ["ָ", "Kamatz"], ["ֹ", "Cholam"], ["ֻ", "Kubutz"], ["ּ", "Dagesh"], ["ׁ", "Shin dot"], ["ׂ", "Sin dot"]];
    const marks = ["״", "׳", "־", "׃", "׀", "₪", "{פ}", "{ס}", "(", ")", "?", "!"];
    const k = $("#osk");
    k.innerHTML = rows.map(r => `<div class="krow">${r.map(c => `<button data-c="${esc(c)}">${esc(c)}</button>`).join("")}</div>`).join("")
      + `<div class="krow">${nikud.map(([c, n]) => `<button class="nk" data-c="${c}" title="${n}">ב${c}</button>`).join("")}</div>`
      + `<div class="krow">${marks.map(c => `<button data-c="${esc(c)}">${esc(c)}</button>`).join("")}</div>`
      + `<div class="krow"><button class="wide" data-act="close">close</button><button class="wide" data-c=" ">space</button><button class="wide" data-act="bs">⌫ delete</button><button class="wide" data-act="enter">↵ new line</button></div>`;
    k.addEventListener("mousedown", e => e.preventDefault());
    k.onclick = e => {
      const b = e.target.closest("button"); if (!b) return;
      if (b.dataset.act === "close") return k.classList.add("hidden");
      const tgt = this.lastFocus; if (!tgt) return this.toast("Click in a text box first, then use the keyboard", true);
      tgt.focus();
      if (b.dataset.act === "bs") return document.execCommand("delete");
      if (b.dataset.act === "enter") return this.insertText(tgt.tagName === "INPUT" ? "" : "\n", tgt);
      if (b.dataset.c === " ") this.fixFinal(tgt);
      this.insertText(b.dataset.c, tgt);
    };
    $("#oskBtn").onclick = () => k.classList.toggle("hidden");
  },

  /* ---------------- clipboard catcher & copy with citation ---------------- */
  async refreshClips() {
    const clips = await this.api("ud_list", { table: "clips", limit: 200 });
    const c = $("#clipCatcher .clips");
    c.innerHTML = clips.map(x => `<div class="clip" draggable="true" data-id="${x.id}"><div class="${isHeb(x.text) ? "he" : ""}" style="font-size:15px">${esc(x.text).slice(0, 400)}</div>
      <div class="row small muted"><span>${esc(x.ref || "")}</span><span class="spacer"></span><a href="#" data-copy="${x.id}">copy</a> · <a href="#" data-del="${x.id}">✕</a></div></div>`).join("") || `<p class="muted small">Select text anywhere and press <span class="kbd">Ctrl+Shift+C</span> or use “📋” on a passage to collect it here.</p>`;
    c.onclick = async e => {
      const id = e.target.dataset.del || e.target.dataset.copy; if (!id) return; e.preventDefault();
      if (e.target.dataset.del) { await this.api("ud_delete", { table: "clips", value: +id }); this.refreshClips(); }
      else { const x = clips.find(y => y.id == id); this.copy(x.text + (x.ref ? `\n— ${x.ref}` : "")); }
    };
    $$(".clip", c).forEach(el => el.ondragstart = ev => { const x = clips.find(y => y.id == el.dataset.id); ev.dataTransfer.setData("text/plain", x.text + (x.ref ? `\n— ${x.ref}` : "")); });
  },
  async addClip(text, ref) { if (!text) return; await this.api("ud_save", { table: "clips", row: { text, ref: ref || "" } }); this.toast("Added to clipboard catcher"); if (!$("#clipCatcher").classList.contains("hidden")) this.refreshClips(); },
  initClipCatcher() {
    const cc = $("#clipCatcher");
    cc.innerHTML = `<header>📋 Clipboard catcher<span class="spacer"></span><button class="btn small" id="ccOutline">→ Notes</button><button class="btn small" id="ccClear">Clear</button><button class="btn small" id="ccClose">✕</button></header><div class="clips"></div>`;
    $("#clipBtn").onclick = () => { cc.classList.toggle("hidden"); if (!cc.classList.contains("hidden")) this.refreshClips(); };
    $("#ccClose").onclick = () => cc.classList.add("hidden");
    $("#ccClear").onclick = async () => { if (!await this.confirm("Remove all collected snippets?")) return; for (const c of await this.api("ud_list", { table: "clips" })) await this.api("ud_delete", { table: "clips", value: c.id }); this.refreshClips(); };
    $("#ccOutline").onclick = async () => { const clips = await this.api("ud_list", { table: "clips", order: "id ASC" }); Notes.openWithHtml("Collected snippets", clips.map(c => `<p>${esc(c.text)}</p>${c.ref ? `<p style="font-size:.8em;color:#8a6d3b">— ${esc(c.ref)}</p>` : ""}`).join("")); };
    // drag the window
    let drag = null; cc.querySelector("header").onmousedown = e => { if (e.target.tagName === "BUTTON") return; drag = [e.clientX - cc.offsetLeft, e.clientY - cc.offsetTop]; };
    document.addEventListener("mousemove", e => { if (drag) { cc.style.left = (e.clientX - drag[0]) + "px"; cc.style.top = (e.clientY - drag[1]) + "px"; cc.style.right = "auto"; } });
    document.addEventListener("mouseup", () => drag = null);
    document.addEventListener("keydown", e => { if (e.ctrlKey && e.shiftKey && (e.key === "C" || e.key === "c")) { const s = String(window.getSelection()); if (s) { e.preventDefault(); this.addClip(s, this.selectionRef()); } } });
    // copy with automatic citation (book, chapter, verse + Sefaria link) when copying from the library
    document.addEventListener("copy", e => {
      if (this.state.settings.cite_on_copy === false) return;
      const sel = window.getSelection(); if (!sel || sel.isCollapsed) return;
      const ref = this.selectionRef(); if (!ref) return;
      const text = String(sel);
      const link = this.sefariaLink(ref);
      e.clipboardData.setData("text/plain", `${text}\n— ${ref}\n${link}`);
      const div = document.createElement("div"); div.appendChild(sel.getRangeAt(0).cloneContents());
      e.clipboardData.setData("text/html", `<div dir="${isHeb(text) ? "rtl" : "ltr"}">${div.innerHTML}</div><p style="color:#8a6d3b;font-size:smaller">— ${esc(ref)} · <a href="${link}">${link}</a></p>`);
      e.preventDefault(); this.status("Copied with citation: " + ref);
    });
  },
  selectionRef() {
    const sel = window.getSelection(); if (!sel || !sel.anchorNode) return "";
    const el = (sel.anchorNode.nodeType === 1 ? sel.anchorNode : sel.anchorNode.parentElement)?.closest("[data-ref]");
    if (!el) return "";
    const end = (sel.focusNode?.nodeType === 1 ? sel.focusNode : sel.focusNode?.parentElement)?.closest("[data-ref]");
    const a = el.dataset.ref, b = end?.dataset.ref;
    if (b && b !== a) { const pa = a.lastIndexOf(" "), last = b.split(/[ :]/).pop(); return a + "-" + last; }
    return a;
  },
  /* "Genesis 1:3" + "בראשית" → "בראשית א׳:ג׳" ; "Berakhot 2a:1" → "ברכות ב׳ ע״א:א׳" */
  heRef(ref, heTitle, title) {
    if (!heTitle) return "";
    const loc = title && ref.startsWith(title) ? ref.slice(title.length).trim() : (ref.match(/\s([\dab:]+)$/) || [, ""])[1];
    const part = loc.split(":").map(x => /^\d+[ab]$/.test(x) ? App.heNum(parseInt(x)) + (x.endsWith("a") ? " ע״א" : " ע״ב") : /^\d+$/.test(x) ? App.heNum(+x) : x).join(":");
    const node = title && ref.startsWith(title + ", ") ? "" : "";
    return (heTitle + " " + part).trim();
  },
  both(en, he) { return he ? `${esc(en)} <span class="he-name">${esc(he)}</span>` : esc(en); },
  sefariaLink(ref) { const m = ref.match(/^(.*?)\s+([\dab:\-]+)$/); const p = m ? m[1].replace(/ /g, "_") + "." + m[2].replace(/:/g, ".") : ref.replace(/ /g, "_"); return "https://www.sefaria.org/" + encodeURI(p); },
  copy(text, html) {
    if (html && window.ClipboardItem) return navigator.clipboard.write([new ClipboardItem({ "text/plain": new Blob([text], { type: "text/plain" }), "text/html": new Blob([html], { type: "text/html" }) })]).then(() => this.toast("Copied"));
    return navigator.clipboard.writeText(text).then(() => this.toast("Copied"), () => { const t = document.createElement("textarea"); t.value = text; document.body.appendChild(t); t.select(); document.execCommand("copy"); t.remove(); this.toast("Copied"); });
  },

  /* ---------------- appearance ---------------- */
  applyTheme(t) {
    let theme = t;
    if (t === "auto") {
      const d = this.state.dash; const now = new Date();
      theme = d && d.sunrise && d.sunset ? (now < new Date(d.sunrise) || now > new Date(d.sunset) ? "dark" : "light") : "light";
    }
    document.documentElement.dataset.theme = theme;
  },
  applySettings() {
    const s = this.state.settings, r = document.documentElement.style;
    if (s.he_font) r.setProperty("--he-font", `"${s.he_font}", "Frank Ruhl Libre", "David", serif`);
    if (s.en_font) r.setProperty("--en-font", `"${s.en_font}", Georgia, serif`);
    if (s.he_size) r.setProperty("--he-size", s.he_size + "px");
    if (s.en_size) r.setProperty("--en-size", s.en_size + "px");
    if (s.read_margin != null) r.setProperty("--read-margin", s.read_margin + "px");
    $("#themeSel").value = s.theme || "light"; this.applyTheme(s.theme || "light");
    $("#langSel").value = s.ui_lang || "en";
    document.documentElement.lang = s.ui_lang || "en";
    $("#quick").placeholder = this.t("Quick search or go to (e.g. Genesis 1:1, בראשית, אור)…");
    this.buildRail(); if (this.current) $$("#rail button").forEach(b => b.classList.toggle("active", b.dataset.id === this.current));
  },
  async setSetting(key, value) { this.state.settings[key] = value; await this.api("setting", { key, value }); },
  async loadFonts() {
    const fonts = await this.api("fonts");
    const css = fonts.map(f => `@font-face{font-family:"${f.family}";src:url("${f.url}") format("${/\.(ttf|otf)$/.test(f.file) ? "truetype" : "woff2"}");font-weight:${/700/.test(f.file) ? 700 : 400};font-display:swap;${/latin/.test(f.file) ? "unicode-range:U+0000-024F;" : /hebrew/.test(f.file) ? "unicode-range:U+0590-05FF,U+FB1D-FB4F,U+200C-2010,U+20AA,U+25CC;" : ""}}`).join("\n");
    let st = $("#appFonts"); if (!st) { st = document.createElement("style"); st.id = "appFonts"; document.head.appendChild(st); }
    st.textContent = css;
    this.state.fonts = [...new Set(fonts.map(f => f.family))];
  },
  fontList() {
    const system = ["David", "Frank Ruehl", "FrankRuehl", "Miriam", "Narkisim", "Gisha", "Aharoni", "Levenim MT", "Rod", "Ezra SIL", "SBL Hebrew", "Times New Roman", "Arial", "Tahoma", "Segoe UI", "Calibri", "Courier New", "Guttman Keren", "Guttman Vilna", "Guttman Rashi", "Stam Ashkenaz CLM", "Taamey Frank CLM", "Shofar", "Keter YG"];
    const avail = system.filter(f => this.fontAvailable(f));
    return [...new Set([...(this.state.fonts || []), ...avail])].sort();
  },
  fontAvailable(name) {
    const c = this._fc || (this._fc = document.createElement("canvas").getContext("2d"));
    const txt = "שלום עולם abcdefg";
    c.font = "40px monospace"; const a = c.measureText(txt).width;
    c.font = `40px "${name}", monospace`; const b = c.measureText(txt).width;
    c.font = "40px serif"; const a2 = c.measureText(txt).width;
    c.font = `40px "${name}", serif`; const b2 = c.measureText(txt).width;
    return a !== b || a2 !== b2;
  },

  status(msg) { $("#status-left").textContent = msg; },
  async waitInstall() {
    this.modal(`<h3>📚 Installing the seforim library</h3><p>This happens only once and takes a few minutes. Please keep the app open.</p>
      <div class="progress" style="height:14px"><div id="instBar"></div></div><p class="small muted" id="instMsg"></p>`);
    while (true) {
      const st = await this.api("install_status").catch(() => ({ state: "running", progress: 0 }));
      const bar = $("#instBar"); if (bar) bar.style.width = (st.progress || 0) + "%";
      const m = $("#instMsg"); if (m) m.textContent = `${st.message || ""} ${st.progress ? "(" + Math.round(st.progress) + "%)" : ""}`;
      if (st.state !== "running") {
        this.closeModal();
        if (st.state === "error") this.toast(st.message, true); else { this.toast(st.message); location.reload(); }
        return;
      }
      await new Promise(r => setTimeout(r, 1000));
    }
  },
  saveSession() {
    clearTimeout(this._ss); this._ss = setTimeout(() => {
      const sess = { page: this.current, tabs: (window.Library && Library.tabs || []).map(t => ({ work_id: t.work_id, node: t.node, chapter: t.chapter, title: t.title })), active: window.Library ? Library.activeIdx : 0 };
      this.api("setting", { key: "session", value: sess }).catch(() => {});
    }, 800);
  },

  async quickGo(q) {
    q = q.trim(); if (!q) return;
    const hit = /\d|[א-ת]{1,3}[:׳'"]/.test(q) ? await this.api("find_ref", { ref: q }).catch(() => null) : null;
    if (hit && hit.work_id) { this.show("library"); Library.open(hit.work_id, hit.node, hit.chapter, hit.id); return; }
    this.show("search"); Search.run(q);
  },

  async start() {
    this.initKeyboard(); this.initOSK(); this.initClipCatcher();
    this.state.status = await this.api("status");
    if (this.state.status.install && this.state.status.install.state === "running") await this.waitInstall();
    this.state.settings = this.state.status.settings || {};
    $("#profileName").textContent = this.state.status.profile;
    await this.loadFonts().catch(() => {});
    try { this.state.dash = await this.api("dashboard"); } catch (e) { }
    this.applySettings();
    if (this.state.settings.heb_default) this.setHeb(true);
    $("#themeSel").onchange = e => { this.setSetting("theme", e.target.value); this.applyTheme(e.target.value); };
    $("#langSel").onchange = e => { this.setSetting("ui_lang", e.target.value); this.applySettings(); };
    $("#focusBtn").onclick = () => { document.body.classList.toggle("focus"); this.toast("Focus mode — press Esc to exit"); };
    $("#quick").onkeydown = e => { if (e.key === "Enter") this.quickGo(e.target.value); };
    $("#profileBtn").onclick = () => Settings.profileDialog();
    $("#modalWrap").onclick = e => { if (e.target.id === "modalWrap") this.closeModal(); };
    const lib = this.state.status.library;
    $("#status-right").textContent = `${lib.works} seforim · ${lib.passages.toLocaleString()} passages · ${this.state.status.tools} tools · offline`;
    setInterval(() => this.api("ping").catch(() => {}), 5000);
    setInterval(() => { if ((this.state.settings.theme || "") === "auto") this.applyTheme("auto"); }, 60000);
    const sess = this.state.settings.session;
    this.show(sess && sess.page && this.pages[sess.page] && sess.page !== "library" ? sess.page : "home");
    if (sess && sess.tabs && sess.tabs.length && this.state.settings.restore_session !== false) Library.restore(sess);
    if (!lib.works) this.status("Tip: open Settings → Library download to get the texts once; after that everything works offline.");
  }
};
