/* Settings: library download (one-time), fonts, appearance & reading, location, privacy PIN, profiles, backup, developer API */
const Settings = {
  render(el) {
    el.innerHTML = `<h1 class="page-title">⚙ Settings</h1><div class="tabs" id="stTabs">${[["library", "📚 Library & download"], ["fonts", "🔤 Fonts"], ["appearance", "🎨 Appearance & location"], ["privacy", "🔒 Privacy & profiles"], ["backup", "💾 Backup"], ["dev", "🧩 Developer & about"]].map(([k, t]) => `<button data-t="${k}">${t}</button>`).join("")}</div><div id="stBody"></div>`;
    $$("#stTabs button", el).forEach(b => b.onclick = () => this.tab(b.dataset.t));
    this.tab("library");
  },
  tab(t) { if (!$("#stTabs")) App.show("settings"); $$("#stTabs button").forEach(b => b.classList.toggle("active", b.dataset.t === t)); return this["t_" + t]($("#stBody")); },
  async t_library(el) {
    const st = await App.api("status"); App.state.status = st;
    const tree = (await App.api("catalog_tree")).tree;
    const count = n => n.works.length + n.children.reduce((a, c) => a + count(c), 0);
    const rows = []; const walk = (ns, d) => ns.forEach(n => { rows.push({ path: n.path, name: n.name, he: n.he, d, n: count(n) }); if (d < 1) walk(n.children, d + 1); });
    walk(tree, 0);
    el.innerHTML = `<div class="grid g2"><div class="card"><h2 style="margin-top:0">Seforim catalog</h2>
        ${st.catalog ? `<p>Loaded: <b>${st.catalog.works.toLocaleString()}</b> works · ${st.catalog.texts.toLocaleString()} text versions · ${st.catalog.categories.toLocaleString()} categories<br><span class="small muted">${esc(st.catalog.path)} · export ${esc(st.catalog.generated_at)}</span></p>` : "<p class='muted'>No catalog loaded.</p>"}
        <button class="btn" id="stCat">Load a different catalog .db…</button>
        <h2>Your offline library</h2><p><b>${st.library.works}</b> seforim · <b>${st.library.passages.toLocaleString()}</b> passages · ${st.library.words.toLocaleString()} distinct words · ${st.library.links.toLocaleString()} cross-references · ${st.library.size_mb} MB</p>
        <h2>Pre-built full library</h2><p class="small">Downloaded <b>SeforimLibrary.sqlite.xz</b> (or its parts)? Put the file(s) in this app's folder or leave them in Downloads, then press the button. Your own notes and seforim are kept.</p>
        <div class="row"><input id="stInstDir" placeholder="(optional) folder where the download is" style="flex:1"><button class="btn primary" id="stInst">📥 Install library download</button></div>
        <p class="small" id="stInstMsg">${st.install && st.install.message ? esc(st.install.message) : ""}</p>
        <h2>Hebrew names of seforim</h2><p class="small" id="stHe">…</p>
        <div class="row"><button class="btn" id="stHeDl" title="Downloads ~116 MB once: exact Hebrew title, author and date of every sefer">⬇ Get exact Hebrew titles for all seforim (one time)</button></div>
        <div class="row" style="margin-top:8px"><button class="btn" id="stCompact">Compact database</button><button class="btn" id="stFolder">Import from a Sefaria export folder (USB)…</button><button class="btn" id="stOpen">📂 Data folder</button></div></div>
      <div class="card"><h2 style="margin-top:0">One-time download</h2>
        <p class="small">Your catalog lists the texts; this downloads the Hebrew (and English) text of the sections you tick, once. <b>After that the app never needs internet.</b> Tip: start with Tanakh, Mishnah and Talmud; add more any time. You can also click a grey title in the Library to get just that sefer.</p>
        <div style="max-height:320px;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:6px">${rows.map(r => `<label class="row small" style="padding-left:${r.d * 22}px"><input type="checkbox" data-path="${esc(r.path)}"> ${esc(r.name)} <span class="he" style="font-size:14px">${esc(r.he || "")}</span><span class="muted">(${r.n})</span></label>`).join("")}</div>
        <div class="row small" style="margin-top:6px"><label><input type="checkbox" id="dlEn" checked> Include English translations</label><label><input type="checkbox" id="dlLinks"> Cross-references (commentary links, ~800 MB download)</label></div>
        <div class="row" style="margin-top:8px"><button class="btn primary" id="dlGo">⬇ Download & build library</button><button class="btn" id="dlStop">Stop</button></div>
        <div class="progress" style="margin-top:8px"><div id="dlBar"></div></div><div class="small" id="dlStat"></div></div></div>`;
    $("#stCat").onclick = async () => { const u = await App.uploadPicked(".db,.sqlite,.sqlite3", false); if (!u.length) return; const r = await App.api("load_catalog", { upload: u[0].upload }); App.toast(`Catalog loaded: ${r.works} works`); Library.loadTree(); this.tab("library"); };
    App.api("he_coverage").then(c => { if (c.works) $("#stHe").innerHTML = `<b>${c.with_hebrew.toLocaleString()}</b> of ${c.works.toLocaleString()} seforim already show their Hebrew name (built-in dictionary${c.official ? ` + ${c.official.toLocaleString()} official titles` : ""}). The one-time download below makes every title exact and adds authors & dates.`; });
    $("#stInst").onclick = async () => {
      const r = await App.api("install_check", { folder: $("#stInstDir").value.trim() || null });
      if (r.state === "running") return App.waitInstall();
      $("#stInstMsg").textContent = r.message || (r.state === "idle" ? "No library download found. Looked in this app's folder, its data folder, Downloads and Desktop." : "Already installed.");
    };
    $("#stHeDl").onclick = async () => { const r = await App.api("dl_titles"); if (r.started) { App.toast("Downloading Hebrew titles…"); this.poll(); } else App.toast("Another download is running — try again when it finishes"); };
    $("#stCompact").onclick = async () => { App.toast("Compacting…"); const r = await App.api("compact"); App.toast(`Done — ${r.size_mb} MB`); };
    $("#stOpen").onclick = () => App.api("open_folder", {});
    $("#stFolder").onclick = async () => { const p = await App.prompt("Folder that contains the Sefaria export (with json/ inside):", "D:\\Sefaria-Export"); if (!p) return; const { job } = await App.api("import_folder", { path: p }); const n = await App.job(job, s => $("#dlStat").textContent = "Importing…"); App.toast(`Imported ${n} seforim`); Library.loadTree(); this.tab("library"); };
    $("#dlGo").onclick = async () => {
      const cats = $$("[data-path]:checked", el).map(i => i.dataset.path); if (!cats.length) return App.toast("Tick at least one section");
      const r = await App.api("dl_start", { categories: cats, english: $("#dlEn").checked, links: $("#dlLinks").checked });
      App.toast(`Downloading ${r.count} seforim…`); this.poll();
    };
    $("#dlStop").onclick = () => App.api("dl_stop");
    this.poll();
  },
  async poll() {
    clearInterval(this._p);
    const tick = async () => {
      const s = await App.api("dl_status"); if (!$("#dlBar")) return clearInterval(this._p);
      $("#dlBar").style.width = (s.total ? 100 * s.done / s.total : 0) + "%";
      $("#dlStat").innerHTML = s.total ? `${s.running ? "⏳" : "✔"} ${s.done}/${s.total} · ${esc(s.current || "")} · ${(s.bytes / 1e6).toFixed(1)} MB${s.errors.length ? ` · <span style="color:var(--danger)">${s.errors.length} problem(s): ${esc(s.errors.slice(-1)[0])}</span>` : ""}` : "";
      if (!s.running) { clearInterval(this._p); if (s.total) { Library.loadTree(); App.state.status = await App.api("status"); } }
    };
    tick(); this._p = setInterval(tick, 1500);
  },
  async t_fonts(el) {
    await App.loadFonts();
    const fonts = App.fontList();
    el.innerHTML = `<div class="card"><div class="row"><b>${fonts.length} Hebrew-capable fonts available</b><span class="spacer"></span><button class="btn primary" id="fDl">⬇ Download the free Hebrew font pack (50+ fonts, once)</button><button class="btn" id="fImp">Add a font file (.ttf/.otf/.woff2)…</button><button class="btn" id="fWin" title="So Microsoft Word and other programs can use them too">Install fonts into Windows (for Word)</button></div>
      <div class="progress hidden" id="fProg" style="margin-top:8px"><div></div></div>
      <input id="fSample" class="he-input" value="בְּרֵאשִׁית בָּרָא אֱלֹהִים — שערי תורה 5787" style="width:100%;margin-top:10px">
      <div id="fList" style="margin-top:10px"></div></div>`;
    const draw = () => $("#fList").innerHTML = fonts.map(f => `<div class="list-item row"><span style="width:200px" class="small">${esc(f)}</span><span dir="rtl" style="font-family:'${esc(f)}';font-size:24px;flex:1">${esc($("#fSample").value)}</span><button class="btn small" data-he="${esc(f)}">Use for Hebrew</button></div>`).join("");
    draw(); $("#fSample").oninput = draw;
    $("#fList").onclick = async e => { const f = e.target.dataset.he; if (f) { await App.setSetting("he_font", f); App.applySettings(); App.toast("Hebrew reading font: " + f); } };
    $("#fDl").onclick = async () => { const { job } = await App.api("fonts_download", {}); $("#fProg").classList.remove("hidden"); const r = await App.job(job, s => $("#fProg div").style.width = (s.total ? 100 * s.progress / s.total : 2) + "%"); App.toast(`Downloaded ${r.downloaded.length} font families`); this.t_fonts(el); };
    $("#fWin").onclick = async () => { const r = await App.api("fonts_install_windows"); App.toast(r.message); };
    $("#fImp").onclick = async () => { const u = await App.uploadPicked(".ttf,.otf,.woff,.woff2"); for (const x of u) await App.api("fonts_import", { upload: x.upload }); this.t_fonts(el); };
  },
  t_appearance(el) {
    const s = App.state.settings; const fonts = App.fontList();
    const fsel = (k, d) => `<select data-k="${k}">${fonts.map(f => `<option ${f === (s[k] || d) ? "selected" : ""}>${esc(f)}</option>`).join("")}</select>`;
    el.innerHTML = `<div class="grid g2"><div class="card col"><h2 style="margin-top:0">Reading</h2>
      <label>Hebrew font ${fsel("he_font", "Frank Ruhl Libre")}</label><label>English font ${fsel("en_font", "Georgia")}</label>
      <label>Hebrew size <input type="number" data-k="he_size" value="${s.he_size || 22}"></label><label>English size <input type="number" data-k="en_size" value="${s.en_size || 16}"></label>
      <label>Text margins <input type="number" data-k="read_margin" value="${s.read_margin ?? 48}"></label>
      <label>Font for Word exports ${fsel("export_font", "David")}</label>
      <label><input type="checkbox" data-k="cite_on_copy" ${s.cite_on_copy !== false ? "checked" : ""}> Add citation + link when copying from the library</label>
      <label><input type="checkbox" data-k="restore_session" ${s.restore_session !== false ? "checked" : ""}> Reopen my books & tabs when the app starts</label>
      <label><input type="checkbox" data-k="heb_default" ${s.heb_default ? "checked" : ""}> Start with Hebrew typing on (English keys → Hebrew)</label>
      <label><input type="checkbox" data-k="comm_new_tab" ${s.comm_new_tab ? "checked" : ""}> Open commentary links in a new tab</label>
      <label><input type="checkbox" data-k="keep_paste_format" ${s.keep_paste_format ? "checked" : ""}> Keep formatting when pasting into Notes</label></div>
      <div class="card col"><h2 style="margin-top:0">Location (for zmanim & Auto theme)</h2>
      <label>Name <input data-k="location_name" value="${esc(s.location_name || "Bethpage, NY")}"></label>
      <label>Latitude <input type="number" step="any" data-k="lat" value="${s.lat ?? 40.744}"></label><label>Longitude <input type="number" step="any" data-k="lon" value="${s.lon ?? -73.482}"></label>
      <label>UTC offset (hours, e.g. -5 winter / -4 summer NY; 2 or 3 Israel) <input type="number" step="any" data-k="tz" value="${s.tz ?? -5}"></label>
      <label>Candle lighting minutes before shkia <input type="number" data-k="candle_minutes" value="${s.candle_minutes ?? 18}"></label>
      <label><input type="checkbox" data-k="israel" ${s.israel ? "checked" : ""}> Eretz Yisrael calendar (one day Yom Tov)</label>
      <div class="row"><b>Quick pick:</b>${[["New York", 40.71, -74.0, -5], ["Lakewood", 40.096, -74.217, -5], ["Monsey", 41.111, -74.068, -5], ["Jerusalem", 31.778, 35.235, 2], ["Bnei Brak", 32.081, 34.833, 2], ["London", 51.5074, -0.1278, 0], ["Montreal", 45.5, -73.57, -5], ["Los Angeles", 34.05, -118.24, -8]].map(c => `<button class="btn small" data-loc='${JSON.stringify(c)}'>${c[0]}</button>`).join("")}</div>
      <h2>Interface</h2><p class="small muted">Theme and language are in the top bar. “Auto (zmanim)” switches to dark after shkia and light after netz.</p></div></div>`;
    $$("[data-k]", el).forEach(i => i.onchange = async () => { await App.setSetting(i.dataset.k, i.type === "checkbox" ? i.checked : (i.type === "number" ? +i.value : i.value)); App.applySettings(); });
    $$("[data-loc]", el).forEach(b => b.onclick = async () => { const [n, la, lo, tz] = JSON.parse(b.dataset.loc); for (const [k, v] of [["location_name", n], ["lat", la], ["lon", lo], ["tz", tz], ["israel", tz === 2]]) await App.setSetting(k, v); this.t_appearance(el); App.toast("Location: " + n); });
  },
  async t_privacy(el) {
    const st = await App.api("status");
    el.innerHTML = `<div class="grid g2"><div class="card"><h2 style="margin-top:0">Private notes PIN</h2><p class="small">Notes and documents marked 🔒 are hidden until the PIN is entered, and are never shared.</p>
      ${st.pin_set ? `<input type="password" id="pOld" placeholder="current PIN">` : ""}<input type="password" id="pNew" placeholder="new PIN (blank = remove)"><button class="btn primary" id="pSet">Save PIN</button></div>
      <div class="card"><h2 style="margin-top:0">Profiles</h2><p class="small">Each family member gets separate notes, bookmarks, history and settings on this computer.</p>
      ${st.profiles.map(p => `<div class="list-item row"><span style="flex:1">${p === st.profile ? "✔ " : ""}<b>${esc(p)}</b></span>${p === st.profile ? "" : `<button class="btn small" data-p="${esc(p)}">Switch</button>`}</div>`).join("")}
      <div class="row" style="margin-top:8px"><input id="pName" placeholder="New profile name"><button class="btn" id="pAdd">Create & switch</button></div></div></div>`;
    $("#pSet").onclick = async () => { const r = await App.api("pin", { action: "set", old: $("#pOld") ? $("#pOld").value : "", pin: $("#pNew").value }); if (r.ok) { App.toast("PIN saved"); App.state.status.pin_set = !!$("#pNew").value; } else App.toast(r.error || "Could not set PIN", true); };
    $$("[data-p]", el).forEach(b => b.onclick = () => this.switchProfile(b.dataset.p));
    $("#pAdd").onclick = () => $("#pName").value.trim() && this.switchProfile($("#pName").value.trim());
  },
  async switchProfile(name) { await App.api("profile", { name }); location.reload(); },
  profileDialog() { App.show("settings"); this.tab("privacy"); },
  t_backup(el) {
    el.innerHTML = `<div class="grid g2"><div class="card"><h2 style="margin-top:0">Backup</h2><p class="small">Saves all profiles (notes, documents, bookmarks, covers, sheets, settings) into one .zip — copy it to a USB stick or another drive.</p>
      <div class="row"><input id="bDir" placeholder="Folder (blank = data\\backups)" style="flex:1"><button class="btn primary" id="bGo">Back up now</button></div><button class="btn" id="bRes" style="margin-top:8px">Restore from a backup .zip…</button></div>
      <div class="card" style="grid-column:1/-1;background:var(--gold-soft)"><h2 style="margin-top:0">📦 One complete zip for another computer</h2>
        <p class="small">Makes <b>one file</b> with everything — the app, the whole library, the AI handwriting reader, all fonts and your notes. Copy it to any offline computer (USB / external drive), right-click → <b>Extract All</b>, and double-click <b>SeforimStudio.exe</b> inside. Nothing to install there.</p>
        <div class="row"><input id="bzDest" style="flex:1" placeholder="Where to save (blank = Desktop\SeforimStudio-Complete.zip — or type a USB drive, e.g. E:\SeforimStudio-Complete.zip)">
          <button class="btn gold" id="bzGo">📦 Make the complete zip</button></div>
        <div class="progress hidden" id="bzProg" style="margin-top:8px"><div></div></div><p class="small" id="bzMsg"></p></div>
      <div class="card"><h2 style="margin-top:0">Export / import my data</h2><p class="small">One readable JSON file with everything in this profile — to move to another computer or keep as an archive.</p>
      <div class="row"><button class="btn" id="bExp">⤓ Export all my data</button><button class="btn" id="bImp">📥 Import data file…</button></div></div></div>`;
    $("#bGo").onclick = async () => { const r = await App.api("backup", { dir: $("#bDir").value.trim() }); App.toast("Backup saved: " + r.path); if (r.url) App.download(r.url); };
    $("#bRes").onclick = async () => { const u = await App.uploadPicked(".zip", false); if (!u.length || !await App.confirm("Restore will replace your current notes with the backup (your current data is kept as .before-restore). Continue?")) return; await App.api("restore", { upload: u[0].upload }); location.reload(); };
    $("#bzGo").onclick = async () => {
      const r = await App.api("make_bundle", { dest: $("#bzDest").value.trim() || null });
      $("#bzProg").classList.remove("hidden"); $("#bzGo").disabled = true;
      $("#bzMsg").textContent = "Making " + r.dest + " … (big library + AI: this can take 5–15 minutes)";
      const res = await App.job(r.job, s => { $("#bzProg div").style.width = (s.total ? 100 * s.progress / s.total : 1) + "%"; }).catch(() => null);
      $("#bzGo").disabled = false;
      if (res && res.path) { $("#bzMsg").innerHTML = `✅ Done: <b>${esc(res.path)}</b> (${res.size_gb} GB). Copy this one file to the other computer, Extract All, run SeforimStudio.exe.`; App.api("open_folder", { path: res.path }); }
    };
    $("#bExp").onclick = async () => { const r = await App.api("export_user"); App.download(r.url); };
    $("#bImp").onclick = async () => { const u = await App.uploadPicked(".json", false); if (!u.length) return; const r = await App.api("import_user", { upload: u[0].upload }); App.toast(`Imported ${r.imported} items`); };
  },
  async t_dev(el) {
    const st = await App.api("status");
    el.innerHTML = `<div class="grid g2"><div class="card"><h2 style="margin-top:0">About</h2><p><b>Seforim Studio</b> ${esc(st.version)} — fully offline. Texts from the Sefaria export (see each text's license). ${st.tools} Hebrew tools.</p>
      <p class="small">Data folder: <code>${esc(st.data_dir)}</code></p><button class="btn" id="dvOpen">📂 Open data folder</button> <button class="btn danger" id="dvQuit">Quit app</button></div>
      <div class="card"><h2 style="margin-top:0">Developer access</h2><p class="small">Local API (only from this computer): <code>POST ${location.origin}/api/&lt;name&gt;</code> with header <code>X-Token</code>. Examples: <code>search</code> {q, lang, opts}, <code>gematria_words</code> {text}, <code>lib_chapter</code> {work_id, node, chapter}, <code>tool_run</code> {id, args}.</p>
      <p class="small">The library is a standard SQLite file (<code>data/library.sqlite</code>) you can open in any SQL tool; any sefer exports to JSON, CSV, TEI-XML, EPUB or SQLite.</p>
      <p class="small"><b>Plugins:</b> put a <code>.py</code> file in <code>data/plugins</code> that registers tools with <code>from core.tools import tool</code>. Loaded: ${st.plugins.map(esc).join(", ") || "none"}.</p>
      <button class="btn small" id="dvTok">Copy API token</button></div></div>`;
    $("#dvOpen").onclick = () => App.api("open_folder", {});
    $("#dvQuit").onclick = async () => { if (await App.confirm("Quit Seforim Studio?")) { await App.api("quit"); document.body.innerHTML = "<p style='padding:40px'>Seforim Studio has closed. You can close this window.</p>"; } };
    $("#dvTok").onclick = () => App.copy(TOKEN);
  }
};
App.register("settings", { title: "Settings", icon: "⚙", render(el) { Settings.render(el); } });
