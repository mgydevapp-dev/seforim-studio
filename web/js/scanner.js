/* Scanner: clean photos/scans, read handwriting / cursive / print (AI · Kraken · Tesseract print+cursive), edit, save as Word. */
const Scanner = {
  files: [], pages: [],
  render(el) {
    el.innerHTML = `<h1 class="page-title">📷 Scanner <small>handwriting, cursive (כתב) and print → editable Hebrew text → Word · fully offline</small></h1>
    <div class="steps"><span class="step on" id="st1">① Add pages</span><span class="step" id="st2">② Read</span><span class="step" id="st3">③ Check & save</span></div>
    <div class="grid sc-grid">
      <div class="col" style="gap:12px">
        <div class="card">
          <div class="dropzone" id="scDrop"><div style="font-size:34px">📄</div><b>Drop photos, scans or documents here</b><div class="small">JPG · PNG · PDF · Word · text — phone photos are fine</div>
            <button class="btn primary" id="scAdd" style="margin-top:10px">Choose files…</button></div>
          <div id="scFiles" class="sc-files"></div>
          <h3 class="sc-h">What kind of writing?</h3>
          <div class="seg" id="scKind">
            <button data-k="hand" class="on">✍️ Handwriting<small>cursive / כתב / notes</small></button>
            <button data-k="print">🖨 Print<small>sefer, typed page</small></button>
            <button data-k="auto">🤔 Not sure<small>let the app decide</small></button></div>
          <h3 class="sc-h">How clear is it?</h3>
          <div class="seg" id="scQual">
            <button data-q="normal" class="on">👍 Clear</button>
            <button data-q="hard">🌫 Unclear / messy / faded<small>slower, tries harder</small></button></div>
          <details class="sc-adv"><summary>Advanced settings</summary>
            <div class="opts small" style="margin-top:8px">
              <label><input type="checkbox" id="o_crop" checked> Crop to page & fix perspective</label><label><input type="checkbox" id="o_orient" checked> Auto-rotate</label>
              <label><input type="checkbox" id="o_deskew" checked> Straighten</label><label><input type="checkbox" id="o_shadows" checked> Remove shadows</label>
              <label><input type="checkbox" id="o_faint" checked> Boost faint pencil</label><label><input type="checkbox" id="o_denoise" checked> Denoise</label>
              <label><input type="checkbox" id="o_lines" checked> Remove notebook lines</label><label><input type="checkbox" id="o_specks" checked> Remove specks</label></div>
            <div class="row" style="margin-top:8px"><label class="small">Reader <select id="scEngine"><option value="auto">Automatic (best installed)</option></select></label>
              <label class="small" title="Tall pages are read in overlapping parts if the AI skips lines">Parts <select id="scStrips"><option value="">auto</option><option>1</option><option>2</option><option>3</option><option>4</option></select></label></div>
          </details>
          <div class="row" style="margin-top:12px"><button class="btn primary big" id="scStart">▶ Read the pages</button>
            <button class="btn" id="scAgain" title="Read the cleaned pages again (e.g. with another reader)">🔁 Read again</button>
            <button class="btn" id="scText" title="For PDFs / Word files that already contain typed text">📄 Text from document</button></div>
          <div class="progress" style="margin-top:10px"><div id="scBar"></div></div><div class="small muted" id="scStat"></div>
        </div>
        <div class="card"><h3 class="sc-h" style="margin-top:0">Readers on this computer</h3><div id="scEng" class="small"></div></div>
      </div>
      <div class="card col sc-text">
        <div class="row"><b>Text</b><span class="small muted">— correct it here, right-to-left</span><span class="spacer"></span>
          <select id="scOrder" title="If Hebrew words come out backwards, choose 'Fix reversed'"><option value="auto">Word order: auto</option><option value="visual">Fix reversed Hebrew</option><option value="logical">Keep as is</option></select></div>
        <div class="sc-split"><div class="sc-img" id="scImg"><div class="muted small" style="padding:30px;text-align:center">The page appears here next to its text, so you can compare line by line.</div></div>
        <textarea id="scOut" class="he-input" dir="rtl" spellcheck="false" style="text-align:right;unicode-bidi:plaintext;white-space:pre-wrap" placeholder="The text appears here. Correct it, then save as Word."></textarea></div>
        <div class="row"><button class="btn primary" id="scDocx">💾 Save as Word</button><button class="btn" id="scTxt">Save .txt</button><button class="btn" id="scCopy">Copy</button>
          <button class="btn" id="scNotes">→ Notes editor</button><button class="btn" id="scSefer">→ My Library</button>
          <button class="btn" id="scTrain" title="After correcting the text, save it as a sample to teach the reader this person's handwriting">🎓 Teach this handwriting</button></div>
      </div>
    </div>
    <div class="row" style="margin-top:16px"><h2 style="margin:0">Cleaned pages</h2><span class="spacer"></span><label class="small">Show <select id="scView"><option value="color">Colour (for AI reader)</option><option value="gray">Enhanced grey</option><option value="bw">Black & white</option><option value="original">Original</option></select></label>
      <button class="btn small" id="scFolder">📂 Open folder</button><button class="btn small" id="scDesk">🖼 Transcription desk</button></div>
    <div class="pages-grid" id="scPages" style="margin-top:8px"></div>`;
    this.kind = "hand"; this.qual = "normal";
    $$("#scKind button", el).forEach(b => b.onclick = () => { $$("#scKind button", el).forEach(x => x.classList.toggle("on", x === b)); this.kind = b.dataset.k; });
    $$("#scQual button", el).forEach(b => b.onclick = () => { $$("#scQual button", el).forEach(x => x.classList.toggle("on", x === b)); this.qual = b.dataset.q; });
    const dz = $("#scDrop", el);
    dz.ondragover = e => { e.preventDefault(); dz.classList.add("over"); }; dz.ondragleave = () => dz.classList.remove("over");
    dz.ondrop = async e => { e.preventDefault(); dz.classList.remove("over"); for (const f of e.dataTransfer.files) this.files.push(await App.upload(f)); this.drawFiles(); };
    $("#scAdd", el).onclick = async () => { this.files.push(...await App.uploadPicked("image/*,.pdf,.docx,.txt,.md,.html,.htm")); this.drawFiles(); };
    $("#scStart", el).onclick = () => this.start();
    $("#scAgain", el).onclick = () => this.pages.length ? this.recognise() : App.toast("Press Start first");
    $("#scText", el).onclick = () => this.extractText();
    $("#scView", el).onchange = () => this.drawPages();
    $("#scDocx", el).onclick = () => this.saveText("docx"); $("#scTxt", el).onclick = () => this.saveText("txt");
    $("#scNotes", el).onclick = () => Notes.openWithHtml("Scanned notes", $("#scOut").value.split("\n").map(l => `<p>${esc(l) || "<br>"}</p>`).join(""));
    $("#scCopy", el).onclick = () => App.copy($("#scOut").value);
    $("#scSefer", el).onclick = async () => { const t = await App.prompt("Title for this sefer:", "Scanned notes"); if (!t) return; const r = await App.api("import_as_sefer", { title: t, text: $("#scOut").value }); App.toast(`Added (${r.passages} paragraphs)`); Library.loadTree(); };
    $("#scFolder", el).onclick = () => App.api("open_folder", { path: this.folder });
    $("#scDesk", el).onclick = () => { App.show("notes"); Notes.addImages(this.pages.map(p => p.urls.original)); };
    $("#scTrain", el).onclick = () => this.train();
    this.loadEngines();
  },
  async loadEngines() {
    const es = await App.api("scan_engines");
    const sel = $("#scEngine"); sel.innerHTML = `<option value="auto">Automatic (best installed)</option>` + es.map(e => `<option value="${e.key}" ${e.ok ? "" : "disabled"}>${esc(e.name)}${e.ok ? "" : " — not installed"}</option>`).join("") + `<option value="none">Image cleanup only</option>`;
    if (!es.some(e => e.ok)) sel.value = "none";
    const desc = { ollama: "Best for handwriting, cursive and messy notes", kraken: "Can learn one person's handwriting", tesseract: "Fast — print, and neat cursive" };
    $("#scEng").innerHTML = `<div class="eng-list">` + es.filter(e => e.ok || e.key !== "kraken").map(e => `<div class="eng ${e.ok ? "ok" : ""}"><div class="row"><b>${esc(e.name)}</b><span class="spacer"></span><span class="badge ${e.ok ? "good" : ""}">${e.ok ? "ready" : "not installed"}</span></div>
      <div class="small">${esc(desc[e.key] || "")}</div><div class="small muted" style="word-break:break-all">${esc(e.info)}</div>
      ${e.key === "ollama" && e.models.length > 1 ? `<select id="scOm">${e.models.map(m => `<option ${m === App.state.settings.ollama_model ? "selected" : ""}>${esc(m)}</option>`).join("")}</select>` : ""}</div>`).join("") + `</div><a href="#" id="scRef" class="small">re-check</a>`;
    this.engs = es;
    const ai = await App.api("ai_status");
    const aiOk = (es.find(e => e.key === "ollama") || {}).ok;
    if (ai.state === "running") {
      $("#scEng").insertAdjacentHTML("afterbegin", `<div class="ai-box"><b>⏳ Installing the AI reader</b>
        <div class="progress" style="height:12px;margin:6px 0"><div style="width:${ai.progress || 0}%"></div></div>
        <div class="small">${esc(ai.message || "")} — ${Math.round(ai.progress || 0)}%. Keep the app open.</div></div>`);
      clearTimeout(this._aiT); this._aiT = setTimeout(() => this.loadEngines(), 1000);
    } else if (!aiOk) {
      $("#scEng").insertAdjacentHTML("afterbegin", `<div class="ai-box">
        <b>🤖 AI handwriting reader</b>
        <ol class="small" style="margin:6px 0 6px 18px;padding:0">
          <li>Put the 3 files <code>SeforimAI.tar.part1of3</code>, <code>part2of3</code>, <code>part3of3</code> into the <b>app folder</b>:<br><code>${esc(ai.folder || "")}</code> <a href="#" id="scAiFolder">open it</a></li>
          <li>Press <b>Install AI pack</b>. It checks the files, installs them and starts the AI (a few minutes).</li></ol>
        <div class="row" style="gap:6px"><button class="btn small primary" id="scAiInst">Install AI pack</button>
          ${ai.bundled ? `<button class="btn small" id="scAiStart">▶ Start the AI</button>` : ""}</div>
        ${ai.message ? `<div class="small ${ai.state === "error" || ai.state === "incomplete" ? "lh-msg" : ""}" style="margin-top:6px">${esc(ai.message)}</div>` : ""}</div>`);
      $("#scAiFolder").onclick = e => { e.preventDefault(); App.api("ai_open_folder"); };
      $("#scAiInst").onclick = async () => { await App.api("ai_check", { force: true }); this.loadEngines(); };
      if ($("#scAiStart")) $("#scAiStart").onclick = async () => { App.toast("Starting the AI reader… (up to a minute)"); await App.api("ai_check"); this.loadEngines(); };
    } else if (ai.state === "done" && ai.message) {
      $("#scEng").insertAdjacentHTML("afterbegin", `<div class="ai-box ok small">${esc(ai.message)}</div>`);
    }
    $("#scRef").onclick = e => { e.preventDefault(); this.loadEngines(); };
    if ($("#scOm")) $("#scOm").onchange = e => App.setSetting("ollama_model", e.target.value);
  },
  showPageImage(i) {
    const p = this.pages[i]; const box = $("#scImg"); if (!p || !box) return;
    box.innerHTML = (this.pages.length > 1 ? `<div class="row small" style="padding:4px">${this.pages.map((_, j) => `<button class="chip ${j === i ? "on" : ""}" data-pg="${j}">page ${j + 1}</button>`).join("")}</div>` : "")
      + `<img src="${App.fileUrl(p.urls.gray || p.urls.color || p.urls.original)}" alt="page ${i + 1}">`;
    $$("[data-pg]", box).forEach(b => b.onclick = () => this.showPageImage(+b.dataset.pg));
  },
  drawFiles() {
    $("#scFiles").innerHTML = this.files.map((f, i) => `<span class="pill" style="margin:2px">${/\.(jpe?g|png|webp|bmp|gif)$/i.test(f.name) && f.url ? `<img src="${f.url}" style="height:26px;vertical-align:middle;border-radius:3px">` : "📄"} ${esc(f.name)} <a href="#" data-rm="${i}">✕</a></span>`).join("") || "";
    $$("#scFiles [data-rm]").forEach(a => a.onclick = e => { e.preventDefault(); this.files.splice(+a.dataset.rm, 1); this.drawFiles(); });
  },
  opts() { const o = {}; ["crop", "orient", "deskew", "shadows", "faint", "denoise", "lines", "specks"].forEach(k => o[k] = $("#o_" + k).checked); return o; },
  async start() {
    const imgs = this.files.filter(f => /\.(jpe?g|png|bmp|tiff?|webp|pdf)$/i.test(f.name));
    if (!imgs.length) return App.toast("Add some photos, scans or PDFs first");
    $("#scStat").textContent = "Cleaning…";
    const { job } = await App.api("scan_start", { uploads: imgs.map(f => f.upload), opts: this.opts() });
    const r = await App.job(job, s => { $("#scBar").style.width = (s.total ? 100 * s.progress / s.total : 3) + "%"; $("#scStat").textContent = s.label ? `Page ${Math.min(s.progress + 1, s.total)} of ${s.total}: ${s.label}` : "Starting…"; });
    this.pages = r.pages; this.folder = r.folder; this.showPageImage(0);
    $("#scStat").textContent = `Cleaned ${r.pages.length} page(s).`;
    this.drawPages();
    if ($("#scEngine").value !== "none") await this.recognise();
    else if (imgs.some(f => /\.pdf$/i.test(f.name))) this.extractText(true);
  },
  async recognise() {
    if (!this.pages.length) return;
    let engine = $("#scEngine").value;
    if (engine === "auto" && this.engs) {
      const ok = k => (this.engs.find(e => e.key === k) || {}).ok;
      if (this.kind === "print" && ok("tesseract")) engine = "tesseract";
      else if (this.kind === "hand" && ok("ollama")) engine = "ollama";
    }
    $("#st2").classList.add("on");
    const st = await App.api("scan_ocr", { engine, pages: this.pages, strips: $("#scStrips").value || null, quality: this.qual, kind: this.kind }).catch(e => { App.toast(e.message, true); return null; });
    if (!st) return;
    $("#scStat").textContent = "Reading with " + st.engine + "…";
    const r = await App.job(st.job, s => { $("#scBar").style.width = (s.total ? 100 * s.progress / s.total : 3) + "%"; if (s.label) $("#scStat").textContent = s.label; });
    this.textPages = r.pages;
    $("#scOut").value = r.pages.map((t, i) => (r.pages.length > 1 ? `——— page ${i + 1} ———\n` : "") + t).join("\n\n");
    $("#scStat").textContent = `Done — read ${r.pages.length} page(s) with ${r.engine}. Please check and correct the text.`;
    $("#st3").classList.add("on"); this.showPageImage(0);
    const w = $("#scWarn") || (() => { const d = document.createElement("div"); d.id = "scWarn"; $("#scStat").after(d); return d; })();
    w.innerHTML = r.warning ? `<div class="lib-health" style="margin:8px 0"><b>⚠ The text came out as symbols</b><div class="small">${esc(r.warning)}</div></div>` : "";
  },
  async train() {
    if (!this.pages.length) return App.toast("Scan a page first");
    const texts = $("#scOut").value.split(/\n*——— page \d+ ———\n/).filter(x => x.trim());
    const writer = await App.prompt("Whose handwriting is this? (one training set per person)", App.state.settings.last_writer || "Abba"); if (!writer) return;
    App.setSetting("last_writer", writer);
    const r = await App.api("scan_train", { pages: this.pages, texts, writer });
    const bad = r.pages.filter(p => !p.ok);
    App.modal(`<h3>🎓 Training samples</h3><p>${r.pages.filter(p => p.ok).length} page(s) saved — <b>${r.total_lines}</b> lines collected so far for ${esc(writer)}.</p>
      ${bad.length ? `<p class="small" style="color:var(--danger)">${bad.length} page(s) skipped: the number of text lines (${bad.map(b => b.text_lines).join(", ")}) did not match the lines found in the image (${bad.map(b => b.lines_found).join(", ")}). Make each handwritten line one line in the text box and try again.</p>` : ""}
      <p class="small">Folder: <code>${esc(r.folder)}</code><br>When you have 300+ lines, fine-tune Kraken (see README → “Teach Kraken one person's handwriting”).</p><div class="row" style="justify-content:flex-end"><button class="btn" data-close>OK</button></div>`);
  },
  drawPages() {
    const v = $("#scView").value;
    $("#scPages").innerHTML = this.pages.map((p, i) => `<div class="card page-card"><div class="row small"><b>Page ${p.page}</b><span class="muted">${esc(p.label)}</span><span class="spacer"></span>
      <button class="btn small" data-rot="${i}" data-d="-90" title="Rotate left">⟲</button><button class="btn small" data-rot="${i}" data-d="90" title="Rotate right">⟳</button><button class="btn small" data-rot="${i}" data-d="180" title="Upside down">↕</button></div>
      <img src="${App.fileUrl(p.urls[v])}" data-big="${i}"><div class="small muted">${p.info.page_found ? "✔ page found" : "• whole photo used"}${p.info.rotated_90 ? " · turned 90°" : ""} · straightened ${p.info.skew_deg ?? 0}° · ${p.info.size ? p.info.size.join("×") : ""}</div></div>`).join("");
    $$("[data-rot]").forEach(b => b.onclick = async () => {
      const p = this.pages[+b.dataset.rot]; p.rot = ((p.rot || 0) + +b.dataset.d + 360) % 360;
      const r = await App.api("scan_redo", { original: p.urls.original, opts: { ...this.opts(), rotate_extra: p.rot, orient: false } });
      Object.assign(p.urls, r.urls); p.info = r.info; this.drawPages();
    });
    $$("[data-big]").forEach(img => img.onclick = () => App.modal(`<img src="${img.src}" style="max-width:100%"><div class="row" style="justify-content:flex-end"><button class="btn" data-close>Close</button></div>`));
  },
  async extractText(quiet) {
    const docs = this.files.filter(f => /\.(pdf|docx|txt|md|html?|epub)$/i.test(f.name));
    if (!docs.length) return quiet || App.toast("Add a PDF, Word or text document first");
    const r = await App.api("scan_text", { uploads: docs.map(f => f.upload), order: $("#scOrder").value });
    this.textPages = r.pages;
    $("#scOut").value = r.pages.map((t, i) => (r.pages.length > 1 ? `——— page ${i + 1} ———\n` : "") + (t || "[this page is a picture with no typed text — handwriting/scan reading comes in Step 2]")).join("\n\n");
    App.toast(r.needs_ocr.length ? `${r.pages.length - r.needs_ocr.length} page(s) had text; ${r.needs_ocr.length} are pictures (Step 2 will read those)` : `Extracted ${r.pages.length} page(s) of editable text`);
  },
  async saveText(fmt) {
    const t = $("#scOut").value; if (!t.trim()) return App.toast("Nothing to save");
    const pages = t.split(/\n*——— page \d+ ———\n/).filter(x => x.trim());
    const title = await App.prompt("File name:", "scanned-notes"); if (!title) return;
    const r = await App.api("scan_save", { format: fmt, pages: pages.length ? pages : [t], title });
    App.download(r.url); App.toast("Saved " + r.name);
  }
};
App.register("scanner", { title: "Scanner", icon: "📷", render(el) { Scanner.render(el); } });
