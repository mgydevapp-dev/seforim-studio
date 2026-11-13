/* Seforim Studio inside the Android app: saving goes to Download/Seforim Studio, printing uses the phone's printing,
   files are chosen with the phone's picker, and the big files (library, AI) can live on the SD card. */
(() => {
  const AND = window.SeforimAndroid; if (!AND) return;
  document.documentElement.classList.add("android");
  const gb = n => (n / 1e9).toFixed(1) + " GB";

  App.download = async function (u, name) {
    try { const r = await this.api("save_as", { url: u, name }); if (r.saved) this.toast("Saved: " + r.path); } catch (e) { }
  };
  App.saveData = async function (data, name) {
    try { const r = await this.api("save_data", { data, name }); if (r.saved) this.toast("Saved: " + r.path); } catch (e) { }
  };
  // a file: pick it on the phone; the app keeps a copy and uses that
  App.pickFile = async function () {
    const files = await this.pickFiles("", false); if (!files.length) return "";
    const r = await this.upload(files[0]); return r.path || "";
  };
  // a folder: the phone's storage places
  App.pickFolder = async function (title, start) {
    const s = await this.api("android_storage").catch(() => null);
    const places = s ? [{ name: "Download folder", path: s.download }, ...s.storages.map(x => ({ name: x.name, path: x.path }))] : [];
    return new Promise(res => this.modal(`<h3>${esc(title || "Choose a folder")}</h3><div class="eng-list">${places.map((p, i) =>
      `<button class="btn" data-i="${i}" style="display:block;width:100%;text-align:left;margin:4px 0"><b>${esc(p.name)}</b><br><span class="small muted" style="word-break:break-all">${esc(p.path)}</span></button>`).join("")}</div>
      <div class="row" style="margin-top:8px"><input id="apPath" style="flex:1" value="${esc(start || "")}" placeholder="…or type a folder"><button class="btn primary" id="apOk">OK</button></div>
      <div class="row" style="justify-content:flex-end;margin-top:6px"><button class="btn" data-close>Cancel</button></div>`, m => {
      $$("[data-i]", m).forEach(b => b.onclick = () => { App.closeModal(); res(places[+b.dataset.i].path); });
      $("#apOk", m).onclick = () => { const v = $("#apPath", m).value.trim(); App.closeModal(); res(v); };
      $("[data-close]", m).addEventListener("click", () => res(""));
    }));
  };
  window.print = () => AND.printPage(document.title || "Seforim Studio");

  // keep the screen on while something long runs (reading a page with the AI takes minutes on a phone)
  const job = App.job.bind(App);
  App.job = async function (id, cb) { AND.keepAwake(true); try { return await job(id, cb); } finally { AND.keepAwake(false); } };

  /* ------------ the phone's storage: phone / SD card, moving the big files, file access, copying downloads in ------------ */
  const Phone = {
    async card(el) {
      const s = await App.api("android_storage");
      el.innerHTML = `<p class="small">The library (about 12 GB once installed) and the AI reader (about 3.5 GB) are big. Keep them on the <b>SD card</b> if your phone has one. Your notes and settings always stay inside the app.</p>
        <div class="eng-list">${s.storages.map(x => `<div class="eng ${x.current ? "ok" : ""}"><div class="row"><b>${x.removable ? "💾" : "📱"} ${esc(x.name)}</b><span class="spacer"></span>
          ${x.current ? `<span class="badge good">in use</span>` : `<button class="btn small" data-use="${esc(x.path)}">Use this</button>`}</div>
          <div class="small">${x.free != null ? gb(x.free) + " free of " + gb(x.total) : ""}${x.library_gb ? " · library here (" + x.library_gb + " GB)" : ""}${x.ai ? " · AI reader here" : ""}</div>
          <div class="small muted" style="word-break:break-all">${esc(x.path)}</div></div>`).join("")}</div>
        <div class="progress" style="margin-top:6px"><div id="phBar"></div></div><div id="phStat" class="small"></div>
        <h3>Downloaded files</h3>
        <p class="small">Download the library or AI files on this phone (they go into <b>Download</b>), or copy them from a computer into Download or the SD card. The app finds them by itself when it may read your files:</p>
        <div class="row" style="gap:6px">${s.all_files ? `<span class="badge good">✅ The app can read your downloaded files</span>` : `<button class="btn primary" id="phPerm">Allow access to files</button>`}
          <button class="btn" id="phPick">📂 Pick the files myself…</button></div>
        <div class="small muted" id="phImp"></div>
        <p class="small muted">Phone: ${esc(s.model || "")} · ${s.ram_gb} GB memory${s.ram_gb && s.ram_gb < 5.5 ? " — the AI reader needs about 6 GB; it may not run on this phone" : ""}</p>`;
      $$("[data-use]", el).forEach(b => b.onclick = async () => {
        const has = s.storages.find(x => x.current);
        const move = has && (has.library_gb || has.ai) ? await App.confirm(`Move the library and AI reader to ${b.dataset.use}? (Yes = move them · Cancel = start there empty)`) : false;
        const r = await App.api("android_storage", { set: b.dataset.use, move });
        if (r.job) await App.job(r.job, j => { $("#phBar").style.width = (j.total ? 100 * j.progress / j.total : 2) + "%"; $("#phStat").textContent = j.label || ""; });
        App.toast("Restarting the app…"); setTimeout(() => AND.restart(), 800);
      });
      if ($("#phPerm", el)) $("#phPerm", el).onclick = () => { AND.askAllFiles(); Phone.waitPerm(el); };
      $("#phPick", el).onclick = () => Phone.importFiles(s.incoming, $("#phImp", el));
    },
    waitPerm(el) { let n = 0; const t = setInterval(() => { if (AND.hasAllFiles() || ++n > 120) { clearInterval(t); if (AND.hasAllFiles()) { App.toast("✅ Access allowed"); Phone.card(el); } } }, 1000); },
    importFiles(dest, out) {
      AND.importFiles(dest);
      const t = setInterval(() => {
        let s = {}; try { s = JSON.parse(AND.importStatus()); } catch (e) { }
        if (out && s.message) out.textContent = s.message + (s.total ? ` (${Math.round(100 * s.done / s.total)}%)` : "");
        if (s.state === "done" || s.state === "error") { clearInterval(t); if (s.state === "done") App.toast(s.message); }
      }, 1000);
      setTimeout(() => clearInterval(t), 6 * 3600e3);
    }
  };
  window.Phone = Phone;

  // Settings → Library: the phone card instead of the Windows "USB stick" card
  if (typeof Settings !== "undefined") {
    Settings.drawLocations = async function () { const el = $("#stLoc"); if (el) await Phone.card(el); };
  }

  // Scanner: the AI box explains the phone files
  if (typeof Scanner !== "undefined") {
    const load = Scanner.loadEngines.bind(Scanner);
    Scanner.loadEngines = async function () {
      await load();
      const box = $("#scEng .ai-box"); const ol = box && box.querySelector("ol"); if (!ol) return;
      const s = await App.api("android_storage").catch(() => ({}));
      ol.innerHTML = `<li>Download the files <code>SeforimAI-android.tar.part1of2</code> and <code>part2of2</code> on this phone (or copy them into Download or the SD card).</li>
        <li>${s.all_files ? "✅ The app may read your downloads." : `Press <b>Allow access to files</b> (once), or <b>Pick the files</b> to copy them in.`}</li>
        <li>Press <b>Install AI pack</b>. It unpacks and starts the AI (a few minutes). It needs a phone with about 6 GB memory; reading one page takes 1–4 minutes.</li>`;
      const row = box.querySelector(".row");
      if (!s.all_files) row.insertAdjacentHTML("afterbegin", `<button class="btn small" id="scPerm">Allow access to files</button>`);
      row.insertAdjacentHTML("beforeend", `<button class="btn small" id="scPick">📂 Pick the files…</button><span class="small muted" id="scImp"></span>`);
      if ($("#scPerm")) $("#scPerm").onclick = () => { AND.askAllFiles(); const t = setInterval(() => { if (AND.hasAllFiles()) { clearInterval(t); this.loadEngines(); } }, 1000); setTimeout(() => clearInterval(t), 120e3); };
      $("#scPick").onclick = () => Phone.importFiles(s.incoming, $("#scImp"));
    };
  }

  // first start: ask once for access to the downloaded files (that is how the library and AI files are found)
  setTimeout(() => {
    try {
      if (AND.hasAllFiles() || localStorage.getItem("askedFiles")) return;
      localStorage.setItem("askedFiles", "1");
    } catch (e) { return; }
    App.modal(`<h3>📂 One more step</h3><p>Seforim Studio installs the library and the AI reader from files you download onto this phone (or copy onto the SD card).
      Allow the app to read your files so it can find them by itself.</p>
      <div class="row" style="justify-content:flex-end"><button class="btn" data-close>Later</button><button class="btn primary" id="apAllow">Allow access</button></div>`,
      m => { $("#apAllow", m).onclick = () => { App.closeModal(); AND.askAllFiles(); }; });
  }, 2500);
})();
