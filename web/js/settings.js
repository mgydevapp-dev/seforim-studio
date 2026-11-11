/* Settings: library download (one-time), fonts, appearance & reading, location, privacy PIN, profiles, backup, developer API */
const Settings = {
  render(el) {
    el.innerHTML = `<h1 class="page-title">⚙ Settings</h1><div class="tabs" id="stTabs">${[["library", "📚 Library"], ["fonts", "🔤 Fonts"], ["appearance", "🎨 Appearance & location"], ["privacy", "🔒 Privacy & profiles"], ["backup", "💾 Backup"], ["plugins", "🧩 Plugins"], ["dev", "🛠 Developer & about"]].map(([k, t]) => `<button data-t="${k}">${t}</button>`).join("")}</div><div id="stBody"></div>`;
    $$("#stTabs button", el).forEach(b => b.onclick = () => this.tab(b.dataset.t));
    this.tab("library");
  },
  tab(t) { if (!$("#stTabs")) App.show("settings"); $$("#stTabs button").forEach(b => b.classList.toggle("active", b.dataset.t === t)); return this["t_" + t]($("#stBody")); },
  async drawLocations() {
    const L = await App.api("locations"), el = $("#stLoc"); if (!el) return;
    el.innerHTML = `<table class="tbl"><tr><td><b>Seforim library</b></td><td><code>${esc(L.library)}</code></td></tr>
      <tr><td><b>AI handwriting models</b></td><td><code>${esc(L.ai)}</code> ${L.ai_found ? "✅" : "— not installed"}</td></tr>
      <tr><td><b>Your notes & settings</b></td><td><code>${esc(L.data)}</code></td></tr></table>
      ${L.all_users ? `<p>✅ Installed for <b>all users</b>: the library and AI models are installed once in <code>${esc(L.shared)}</code> for everyone on this computer; each user has their own notes.</p>` : `<p class="muted">To install once for every user of this computer, run SeforimStudio-Setup.exe and tick “Install for ALL users”.</p>`}
      <div class="grid g2" style="margin-top:8px">
        <div><b>Use the AI models from a USB stick or another folder</b><p class="muted">No copying needed — the app runs them from there. (A USB stick with a <code>SeforimAI</code> folder is found automatically.)</p>
          <div class="row"><input id="locAi" data-pick="folder" placeholder="e.g. E:\\SeforimAI" style="flex:1"><button class="btn" id="locAiGo">Use this folder</button></div>
          <div class="row" style="margin-top:6px"><input id="locCopy" data-pick="folder" placeholder="Copy my AI models to… e.g. E:\\" style="flex:1"><button class="btn" id="locCopyGo">Copy to USB</button></div>
          <div class="progress" style="margin-top:6px"><div id="locBar"></div></div><div id="locStat"></div></div>
        <div><b>Use a library from a USB stick or another drive</b><p class="muted">Point to a folder that has <code>library.sqlite</code> (e.g. to keep the 11 GB library off drive C:).</p>
          <div class="row"><input id="locLib" data-pick="folder" placeholder="e.g. D:\\SeforimLibrary" style="flex:1"><button class="btn" id="locLibGo">Use this library</button></div>
          ${Object.keys(L.custom || {}).length ? `<button class="btn small" id="locReset" style="margin-top:6px">Back to the normal places</button>` : ""}</div></div>`;
    const set = async a => { try { await App.api("locations", a); App.toast("Saved"); this.drawLocations(); Library.loadTree && Library.loadTree(); } catch (e) { App.toast(e.message, true); } };
    $("#locAiGo").onclick = () => set({ ai: $("#locAi").value });
    $("#locLibGo").onclick = () => set({ library: $("#locLib").value });
    if ($("#locReset")) $("#locReset").onclick = () => set({ ai: "", library: "" });
    $("#locCopyGo").onclick = async () => {
      const f = $("#locCopy").value.trim(); if (!f) return App.toast("Type the USB stick, e.g. E:\\", true);
      const use = await App.confirm("After copying, run the AI models from the USB stick? (OK = use them from the USB stick · Cancel = only make a copy)");
      const { job } = await App.api("copy_ai", { folder: f, use });
      const r = await App.job(job, s => { $("#locBar").style.width = (s.total ? 100 * s.progress / s.total : 2) + "%"; $("#locStat").textContent = s.label || ""; });
      $("#locStat").textContent = r && r.folder ? "Copied to " + r.folder : "";
      this.drawLocations();
    };
  },
  async t_library(el) {
    const st = await App.api("status"); App.state.status = st;
    el.innerHTML = `<div class="grid g2"><div class="card"><h2 style="margin-top:0">Your library</h2>
        <p><b>${st.library.works.toLocaleString()}</b> seforim · <b>${st.library.passages.toLocaleString()}</b> passages · ${st.library.words.toLocaleString()} distinct words · ${st.library.links.toLocaleString()} links between seforim · ${st.library.size_mb} MB</p>
        <p class="small muted">The seforim, their names, order, commentaries and links come from the Otzaria library; English translations are shown beside the seforim that have one.</p>
        <div class="row" style="margin-top:8px"><button class="btn" id="stCompact">Compact database</button><button class="btn" id="stOpen">📂 Data folder</button></div></div>
      <div class="card"><h2 style="margin-top:0">Install the library</h2>
        <p class="small">Downloaded the library files (<b>SeforimLibrary.sqlite.xz.part…</b>)? Leave them in Downloads, on the USB stick next to SeforimStudio-Setup.exe, or choose their folder, then press Install. Your own notes and seforim are kept.</p>
        <div class="row"><input id="stInstDir" data-pick="folder" placeholder="(optional) folder where the download is" style="flex:1"><button class="btn primary" id="stInst">📥 Install library</button></div>
        <p class="small" id="stInstMsg">${st.install && st.install.message ? esc(st.install.message) : ""}</p></div>
      <div class="card" style="grid-column:1/-1"><h2 style="margin-top:0">📍 Where the library and AI models are</h2><div id="stLoc" class="small">…</div></div></div>`;
    this.drawLocations();
    $("#stInst").onclick = async () => {
      const r = await App.api("install_check", { folder: $("#stInstDir").value.trim() || null });
      if (r.state === "running") return App.waitInstall();
      $("#stInstMsg").textContent = r.message || (r.state === "idle" ? "No library download found. Looked in this app's folder, its data folder, Downloads, Desktop and USB sticks." : "Already installed.");
    };
    $("#stCompact").onclick = async () => { App.toast("Compacting…"); const r = await App.api("compact"); App.toast(`Done — ${r.size_mb} MB`); };
    $("#stOpen").onclick = () => App.api("open_folder", {});
  },
  async t_plugins(el) {
    const list = await App.api("plugins").catch(() => []);
    const ex = `PLUGIN = {"id": "hello", "name": "Hello", "icon": "👋", "version": "1.0",
          "description": "My first Seforim Studio plugin"}

from core.tools import tool          # optional: add a tool to the Tools screen

def count_words(app, args):          # called from your page with Plugins.call("hello", "count", {...})
    return {"n": len(args.get("text", "").split())}

ROUTES = {"count": count_words}

def home(app):                       # optional: a card on the Home screen
    return {"title": "Hello", "html": "<p>Hello from my plugin!</p>"}

@tool("My tools", "Reverse a word", "Writes a word backwards",
      [{"name": "text", "label": "Word", "type": "text"}])
def reverse_word(a, ctx=None):
    return a.get("text", "")[::-1]

PAGE_JS = r"""
App.register("hello", { title: "Hello", icon: "👋", render(el) {
  el.innerHTML = '<h1 class="page-title">👋 Hello</h1><textarea id="hT"></textarea><button class="btn" id="hB">Count</button><p id="hR"></p>';
  document.getElementById("hB").onclick = async () => {
    const r = await Plugins.call("hello", "count", { text: document.getElementById("hT").value });
    document.getElementById("hR").textContent = r.n + " words";
  };
} });
"""`;
    el.innerHTML = `<div class="grid g2">
      <div class="card"><h2 style="margin-top:0">🧩 Load a plugin</h2>
        <p class="small">A plugin is a <b>.py</b> file, or a <b>.zip</b> with a folder that has <code>plugin.py</code> in it (plus a <code>page.js</code> or other files if it needs them). It works offline, like the rest of the app.</p>
        <div class="row"><button class="btn primary" id="spLoad">📂 Load a plugin file (.py / .zip)…</button><button class="btn" id="spOpen">Open the plugins folder</button></div>
        <h3>Installed</h3>${(list || []).map(p => `<div class="list-item row"><span>${esc(p.icon || "🧩")}</span><b>${esc(p.name)}</b><span class="small muted">${esc(p.version || "")} ${p.builtin ? "· built in" : ""} ${p.error ? `· <span style="color:var(--danger)">${esc(p.error)}</span>` : ""}</span><span class="spacer"></span><span class="badge ${p.enabled ? "good" : ""}">${p.enabled ? "on" : "off"}</span></div>`).join("") || `<p class="muted small">None</p>`}
        <p class="small">Turn plugins on/off or remove them on the <a href="#" id="spPage">Plugins screen</a>.</p></div>
      <div class="card"><h2 style="margin-top:0">📘 How to build a plugin</h2>
        <ol class="small" style="line-height:1.7">
          <li>Make a new text file named e.g. <code>hello.py</code> (any name, letters and _ only).</li>
          <li>At the top put <code>PLUGIN = {...}</code> with an <b>id</b>, <b>name</b>, <b>icon</b>, <b>version</b> and <b>description</b>.</li>
          <li>Add what you need — all optional:
            <ul><li><b>ROUTES</b> = {"name": function(app, args)} — Python the page can call with <code>Plugins.call(id, name, args)</code>. <code>app.lib</code> is the library (search, passages, gematria…), <code>app.pget / app.pset</code> save your plugin's data.</li>
            <li><b>PAGE_JS</b> = a screen of your own: <code>App.register(id, { title, icon, render(el) {…} })</code> — it appears in the menu under Add-ons.</li>
            <li><b>home(app)</b> — returns a card for the Home screen.</li>
            <li><b>@tool(...)</b> — a tool in the Tools screen (inputs: text / number / date / select).</li></ul></li>
          <li>Save it, press <b>Load a plugin file</b> above and choose it. Done — the app reloads with your plugin.</li>
          <li>For several files: put <code>plugin.py</code> (+ <code>page.js</code>, pictures, data) in a folder, zip the folder, load the .zip.</li>
          <li>To share it: send the .py / .zip to a friend; they load it the same way. Errors show in the list on the left.</li></ol>
        <details><summary class="small">Full example (copy it)</summary><pre class="code-box" id="spEx"></pre><button class="btn small" id="spCopy">Copy example</button>
          <button class="btn small" id="spSave">Save example as hello.py</button></details>
        <p class="small muted">The built-in add-ons (Daily Learning, Chazara, Tehillim, Word Study, 613 Mitzvos) are written exactly this way — open the plugins folder to read them.</p></div></div>`;
    $("#spEx", el).textContent = ex;
    $("#spCopy", el).onclick = () => { navigator.clipboard.writeText(ex); App.toast("Copied"); };
    $("#spSave", el).onclick = () => App.saveData(ex, "hello.py");
    $("#spLoad", el).onclick = async () => { const u = await App.uploadPicked(".py,.zip", false); if (!u.length) return;
      const r = await App.api("plugin_install", { upload: u[0].upload }); App.toast(r.error ? "Problem: " + r.error : "Loaded " + r.name + " — reloading…", !!r.error); if (!r.error) setTimeout(() => location.reload(), 900); };
    $("#spOpen", el).onclick = () => App.api("open_folder", { which: "plugins" });
    $("#spPage", el).onclick = e => { e.preventDefault(); App.show("plugins"); };
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
      <label><input type="checkbox" id="stAskSave" ${s.ask_save !== "0" ? "checked" : ""}> Ask where to save files (Save as…) — otherwise they go to Downloads</label>
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
    $("#stAskSave", el).onchange = e => App.setSetting("ask_save", e.target.checked ? "1" : "0");
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
      <div class="row"><input id="bDir" data-pick="folder" placeholder="Folder (blank = data\\backups)" style="flex:1"><button class="btn primary" id="bGo">Back up now</button></div><button class="btn" id="bRes" style="margin-top:8px">Restore from a backup .zip…</button></div>
      <div class="card" style="grid-column:1/-1;background:var(--gold-soft)"><h2 style="margin-top:0">📦 One complete zip for another computer</h2>
        <p class="small">Makes <b>one file</b> with everything — the app, the whole library, the AI handwriting reader, all fonts and your notes. Copy it to any offline computer (USB / external drive), right-click → <b>Extract All</b>, and double-click <b>SeforimStudio.exe</b> inside. Nothing to install there.</p>
        <div class="row"><input id="bzDest" data-pick="folder" style="flex:1" placeholder="Where to save (blank = Desktop\SeforimStudio-Complete.zip — or type a USB drive, e.g. E:\SeforimStudio-Complete.zip)">
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
    el.innerHTML = `<div class="grid g2"><div class="card"><h2 style="margin-top:0">About</h2><p><b>Seforim Studio</b> ${esc(st.version)} — fully offline. Seforim from the Otzaria library (see each sefer's source and license). ${st.tools} Hebrew tools.</p>
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
