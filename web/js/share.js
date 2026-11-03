/* Offline sharing: LAN (built-in server between two copies of the app), Bluetooth, and package files */
const Share = {
  pre: null,
  render(el) {
    el.innerHTML = `<h1 class="page-title">📡 Share <small>Between two computers running Seforim Studio — over the same Wi-Fi, a phone hotspot or a cable. No internet needed.</small></h1>
    <div class="grid g2">
      <div class="card"><h2 style="margin-top:0">1 · Receive on this computer</h2>
        <div class="row"><label><input type="checkbox" id="shOn"> Allow other computers to send me items</label></div>
        <div id="shInfo" class="small muted" style="margin-top:6px"></div>
        <h2>Inbox</h2><div id="shInbox"></div>
        <h2>Bluetooth</h2><div class="row"><button class="btn" id="shBtRecv">Receive via Bluetooth</button><span class="small muted">then use “Import a package”.</span></div>
      </div>
      <div class="card"><h2 style="margin-top:0">2 · Send to another computer</h2>
        <label class="small muted">What to send</label>
        <div class="row"><select id="shKind"><option value="docs">Documents (notes)</option><option value="sheets">Source sheets</option><option value="covers">Covers</option><option value="notes">Notes on passages</option><option value="bookmarks">Bookmarks</option><option value="works">Seforim (whole books)</option></select></div>
        <div id="shItems" style="max-height:240px;overflow:auto;margin-top:6px;border:1px solid var(--line);border-radius:8px;padding:4px"></div>
        <h2>Computers found nearby</h2><div id="shPeers" class="small"></div>
        <div class="row small" style="margin-top:6px"><input id="shIp" placeholder="or type its address e.g. 192.168.1.20" style="width:200px"><button class="btn small" id="shAddIp">Add</button></div>
        <div class="row" style="margin-top:10px"><input id="shCode" placeholder="6-digit code shown on the other computer" style="width:240px"><button class="btn primary" id="shSend">Send</button></div>
        <div class="row" style="margin-top:12px"><button class="btn" id="shBt">Send via Bluetooth</button><button class="btn" id="shPkg">⤓ Save as package file (USB / email)</button><button class="btn" id="shImp">📥 Import a package</button></div>
      </div></div>`;
    $("#shOn", el).onchange = async e => { const r = await App.api("share_enable", { on: e.target.checked }); this.info(r); };
    $("#shKind", el).onchange = () => this.items();
    $("#shAddIp", el).onclick = async () => { await App.api("share_peers", { add_ip: $("#shIp").value.trim() }); this.peers(); };
    $("#shSend", el).onclick = () => this.send();
    $("#shBt", el).onclick = async () => { const ids = this.selected(); if (!ids.length) return App.toast("Tick what to send"); const r = await App.api("bluetooth", { kind: $("#shKind").value, ids }); App.modal(`<h3>Bluetooth</h3><p>${esc(r.message)}</p><p class="small muted">${esc(r.path)}</p><div class="row" style="justify-content:flex-end"><button class="btn" data-close>OK</button></div>`); };
    $("#shBtRecv", el).onclick = async () => { const r = await App.api("bluetooth", { receive: true }); App.toast(r.message); };
    $("#shPkg", el).onclick = async () => { const ids = this.selected(); if (!ids.length) return App.toast("Tick what to send"); const r = await App.api("package_export", { kind: $("#shKind").value, ids }); App.download(r.url); App.toast(`Package with ${r.count} item(s) saved`); };
    $("#shImp", el).onclick = async () => { const ups = await App.uploadPicked(".seforim,.zip"); for (const u of ups) { const r = await App.api("package_import", { upload: u.upload }); App.toast(`Imported ${r.count} ${r.kind}${r.from ? " from " + r.from : ""}`); } };
    this.info(App.state.status.share);
    this.items(); this.inbox();
    this.iv = setInterval(() => { if (App.current === "share") { this.peers(); this.inbox(); } }, 3000);
  },
  info(s) {
    $("#shOn").checked = s.enabled;
    $("#shInfo").innerHTML = s.enabled ? `<div class="card" style="background:var(--gold-soft)"><div>This computer: <b>${esc(s.name)}</b></div><div>Pairing code: <b style="font-size:26px;letter-spacing:4px">${esc(s.code)}</b></div><div>Address: ${s.ips.map(ip => `<b>${esc(ip)}</b>`).join(", ") || "—"} · port ${s.port}</div><div class="small">Only items sent with this code are accepted; nothing else on this computer can be read from the network.</div></div>` : "Off — nobody can send you anything.";
  },
  async items() {
    const k = $("#shKind").value; let rows;
    if (k === "works") rows = (await App.api("lib_works")).map(w => ({ id: w.id, label: w.title + (w.source === "user" ? " (mine)" : "") }));
    else rows = (await App.api("ud_list", { table: k })).filter(r => !r.private).map(r => ({ id: r.id, label: r.title || r.ref || r.text || ("#" + r.id) }));
    $("#shItems").innerHTML = rows.map(r => `<label class="list-item" style="display:flex;gap:6px"><input type="checkbox" value="${r.id}" ${this.pre && this.pre.kind === k && this.pre.id == r.id ? "checked" : ""}> ${esc(String(r.label).slice(0, 80))}</label>`).join("") || "<p class='small muted'>Nothing here yet (private items are never shared).</p>";
  },
  selected() { return $$("#shItems input:checked").map(i => +i.value); },
  preselect(kind, id, title) { this.pre = { kind, id }; if ($("#shKind")) { $("#shKind").value = kind; this.items(); } App.toast("Ready to share: " + title); },
  async peers() {
    const ps = await App.api("share_peers");
    $("#shPeers").innerHTML = ps.map(p => `<label class="list-item" style="display:flex;gap:6px"><input type="radio" name="peer" value="${esc(p.id)}"> 💻 <b>${esc(p.name)}</b> <span class="muted">${esc(p.ip)}</span></label>`).join("") || `<span class="muted">Searching… make sure the other computer has “Allow other computers to send me items” turned on and is on the same network.</span>`;
  },
  async send() {
    const peer = $("input[name=peer]:checked"); const ids = this.selected();
    if (!peer) return App.toast("Choose a computer"); if (!ids.length) return App.toast("Tick what to send");
    const r = await App.api("share_send", { peer: peer.value, kind: $("#shKind").value, ids, code: $("#shCode").value.trim(), sender: App.state.status.profile });
    if (r.ok) App.toast("Sent ✔");
  },
  async inbox() {
    const items = await App.api("share_inbox");
    $("#shInbox").innerHTML = items.map(x => `<div class="list-item row"><span style="flex:1">📦 ${esc(x.file)} <span class="small muted">from ${esc(x.from)} · ${(x.size / 1024).toFixed(1)} KB</span></span><button class="btn small primary" data-imp="${esc(x.file)}">Import</button><button class="btn small" data-del="${esc(x.file)}">✕</button></div>`).join("") || "<p class='small muted'>Empty</p>";
    $$("#shInbox [data-imp]").forEach(b => b.onclick = async () => { const r = await App.api("package_import", { inbox: b.dataset.imp }); App.toast(`Imported ${r.count} ${r.kind}`); await App.api("share_inbox", { delete: b.dataset.imp }); this.inbox(); Library.loadTree && Library.loadTree(); });
    $$("#shInbox [data-del]").forEach(b => b.onclick = async () => { await App.api("share_inbox", { delete: b.dataset.del }); this.inbox(); });
  }
};
App.register("share", { title: "Share", icon: "📡", render(el) { Share.render(el); } });
