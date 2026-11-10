/* Home dashboard: Hebrew date, parasha, daf yomi, zmanim, upcoming holidays & their texts, goals, history */
const Home = {
  async load(el) {
    let d;
    try { d = App.state.dash = await App.api("dashboard"); } catch (e) { return; }
    const st = (App.state.status && App.state.status.library) || { works: 0, passages: 0 };
    const z = d.zmanim;
    const zKeys = ["Alos HaShachar (16.1°)", "Netz / Sunrise", "Sof Zman Shema (MGA)", "Sof Zman Shema (GRA)", "Sof Zman Tefillah (GRA)", "Chatzos", "Mincha Gedola", "Plag HaMincha", "Candle lighting", "Shkia / Sunset", "Tzeis HaKochavim (8.5°)"];
    el.innerHTML = `
    <div class="home-hero">
      <div class="card">
        <div class="row"><div><div class="he-date">${esc(d.hebrew)}</div><div class="muted">${esc(d.weekday)} · ${new Date(d.date + "T12:00").toLocaleDateString(undefined, { dateStyle: "long" })} · ${esc(d.hebrew_en)}</div></div><span class="spacer"></span>
        ${d.parasha ? `<div class="col" style="align-items:flex-end"><span class="pill">Parashas ${esc(d.parasha)}</span><span class="he" style="font-size:20px">${esc(d.parasha_he)}</span></div>` : ""}</div>
        ${d.today_holidays.length ? `<p><b>Today:</b> ${d.today_holidays.map(x => esc(x[0]) + " — " + esc(x[1])).join(", ")}</p>` : ""}
        ${d.omer ? `<p class="he" style="font-size:17px">🌾 ${esc(d.omer)}</p>` : ""}
        <div class="grid g3" style="margin-top:10px">
          <div class="card feature-tile" id="hDaf"><div class="muted small">Daf Yomi</div><div class="he" style="font-size:26px">${esc(d.daf.he)}</div><div class="small">${esc(d.daf.masechta)} ${d.daf.daf} — open ›</div></div>
          <div class="card feature-tile" id="hPar"><div class="muted small">This week's parasha</div><div class="he" style="font-size:26px">${esc(d.parasha_he)}</div><div class="small">Open in library ›</div></div>
          <div class="card"><div class="muted small">Library</div><div style="font-size:24px;color:var(--accent);font-weight:700">${st.works.toLocaleString()}</div><div class="small">seforim · ${st.passages.toLocaleString()} passages</div></div>
        </div>
        <div class="home-search"><input id="hQ" placeholder="Search the seforim, go to a place (Berakhot 2a), or translate a word…"><button class="btn primary" id="hGo">Search</button><button class="btn" id="hTr">🌐 Translate</button></div>
        <div class="quick-acts">${[["library", "📚", "Library"], ["search", "🔎", "Search"], ["translate", "🌐", "Translate"], ["gematria", "🔢", "Gematria"], ["scanner", "📷", "Scan notes"], ["notes", "✍️", "Write notes"], ["mitzvos", "📜", "613 Mitzvos"], ["cover", "📕", "Make a cover"]]
          .filter(([id]) => App.pages[id]).map(([id, ic, t]) => `<button class="qa" data-go-page="${id}"><span>${ic}</span>${esc(t)}</button>`).join("")}</div>
      </div>
      <div class="card"><div class="row"><b>Zmanim</b><span class="muted small">— ${esc(d.location.name)}</span><span class="spacer"></span><a href="#" id="hLoc" class="small">change</a></div>
        <table class="data" style="margin-top:6px">${zKeys.filter(k => z[k]).map(k => `<tr><td>${esc(k)}</td><td style="text-align:right;font-weight:600">${esc(z[k])}</td></tr>`).join("")}</table></div>
    </div>
    <div class="grid g3" style="margin-top:14px">
      <div class="card"><b>Upcoming</b>${d.upcoming.map(u => `<div class="list-item" data-texts="${esc(JSON.stringify(u.texts))}"><div class="row"><span>${esc(u.en)}</span><span class="spacer"></span><span class="he" style="font-size:16px">${esc(u.he)}</span></div>
        <div class="small muted">${new Date(u.date + "T12:00").toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })} · in ${u.days} days ${u.texts.length ? "· 📖 " + u.texts.map(esc).join(", ") : ""}</div></div>`).join("")}</div>
      <div class="card"><div class="row"><b>Reading goals</b><span class="spacer"></span><button class="btn small" id="hGoal">+ Goal</button></div>
        ${d.goals.length ? d.goals.map(g => `<div class="list-item"><div class="row"><b>${esc(g.title)}</b><span class="spacer"></span><span class="small">${g.done || 0}/${g.total}</span></div>
          <div class="progress"><div style="width:${Math.min(100, 100 * (g.done || 0) / (g.total || 1))}%"></div></div>
          <div class="small muted">${g.per_day ?? "?"} passages/day to finish by ${esc(g.end_date)}${g.eta_days ? ` · at your pace: ~${g.eta_days} days` : ""} <a href="#" data-goal="${g.id}">+ log progress</a></div></div>`).join("") : `<p class="muted small">Plan to finish a sefer by a date — e.g. Mishnah Berurah by Pesach.</p>`}
        ${d.pace.passages_per_hour ? `<p class="small muted">Your pace: ${d.pace.passages_per_hour} passages/hour, ${d.pace.passages_per_day}/day.</p>` : ""}</div>
      <div class="card"><b>Recently opened</b>${d.history.length ? d.history.map(x => `<div class="list-item" data-ref="${esc(x.ref)}">${esc(x.ref)}<div class="small muted">${esc(x.ts)}</div></div>`).join("") : `<p class="muted small">Nothing yet.</p>`}</div>
    </div>
    <h2>Everything in Seforim Studio</h2>
    <div class="grid g4">${[
      ["library", "📚", "Library", "Every sefer neatly sorted, side-by-side Hebrew & English, commentaries, Daf layout"],
      ["search", "🔎", "Search", "Hebrew ⇄ English, phrases, wildcards, root, malei/chaser, NEAR, regex"],
      ["gematria", "🔢", "Gematria", "18 methods; find every word & phrase with a value"],
      ["roshei", "🔤", "Roshei Teivos", "Find acronyms & sofei teivos across the library"],
      ["notes", "✍️", "Notes", "Hebrew word processor with nikud, fonts, footnotes, export to Word"],
      ["mylib", "🗂", "My Library", "Your notes, seforim, bookmarks; import & export"],
      ["cover", "📕", "Covers", "Design a beautiful sefer cover"], ["scanner", "📷", "Scanner", "Clean photos of handwritten notes, pull text from documents"],
      ["tools", "🧰", "130+ Hebrew tools", "Calendar, ciphers, numbers, measures, text cleanup"], ["analysis", "📊", "Analysis", "Word clouds, co-occurrence, timelines, networks"],
      ["share", "📡", "Share", "Send to another computer over Wi-Fi or Bluetooth — no internet"], ["calendar", "📅", "Calendar", "Hebrew/English month view with holidays & daf"]
    ].map(([id, ic, t, dsc]) => `<div class="card feature-tile" data-go="${id}"><div class="ic">${ic}</div><b>${t}</b><div class="small muted">${dsc}</div></div>`).join("")}</div>`;
    App.api("home_cards").then(cards => {
      if (!cards.length) return;
      el.querySelector(".home-hero").insertAdjacentHTML("afterend", `<div class="grid g3" style="margin-top:14px">${cards.map(c => `<div class="card" data-plugin="${esc(c.plugin)}"><div class="row"><b>${esc(c.icon || "")} ${esc(c.title)}</b><span class="spacer"></span>${c.open ? `<a href="#" class="small" data-pgo="${esc(c.open)}">open ›</a>` : ""}</div>${c.html}</div>`).join("")}</div>`);
      $$("[data-pgo]", el).forEach(a => a.onclick = e => { e.preventDefault(); App.show(a.dataset.pgo); });
      $$("[data-ref]", el).forEach(x => { if (!x.onclick) x.onclick = () => App.quickGo(x.dataset.ref); });
    }).catch(() => {});
    $$("[data-go]", el).forEach(x => x.onclick = () => App.show(x.dataset.go));
    $("#hDaf", el).onclick = () => App.quickGo(d.daf.ref);
    const hq = () => { const v = $("#hQ", el).value.trim(); if (v) App.quickGo(v); };
    $("#hGo", el).onclick = hq; $("#hQ", el).onkeydown = e => { if (e.key === "Enter") hq(); };
    $("#hTr", el).onclick = () => { const v = $("#hQ", el).value.trim(); App.show("translate"); if (v) setTimeout(() => { $("#trQ").value = v; App.pages.translate.run(v); }, 50); };
    $$("[data-go-page]", el).forEach(b => b.onclick = () => App.show(b.dataset.goPage));
    $("#hPar", el).onclick = async () => { const ref = await App.api("reference_data"); const p = ref.parshiyos.find(x => d.parasha.startsWith(x[0]) || x[0].startsWith(d.parasha.split(/[ -]/)[0])); App.quickGo(p ? p[2] : "Genesis 1:1"); };
    $$("[data-ref]", el).forEach(x => x.onclick = () => App.quickGo(x.dataset.ref));
    $$("[data-texts]", el).forEach(x => x.onclick = () => { const t = JSON.parse(x.dataset.texts); if (t.length) App.quickGo(t[0]); });
    $("#hLoc", el).onclick = e => { e.preventDefault(); App.show("settings"); Settings.tab("appearance"); };
    $("#hGoal", el).onclick = () => Home.goalDialog(el);
    $$("[data-goal]", el).forEach(a => a.onclick = async e => {
      e.preventDefault(); const g = d.goals.find(x => x.id == a.dataset.goal); const n = await App.prompt(`Passages finished in "${g.title}" (total so far)`, g.done || 0, { type: "number" });
      if (n != null) { await App.api("ud_save", { table: "goals", row: { ...g, done: +n } }); Home.load(el); }
    });
  },
  async goalDialog(el) {
    const works = await App.api("lib_works");
    App.modal(`<h3>New reading goal</h3><label>Sefer</label><select id="gW" style="width:100%">${works.map(w => `<option value="${w.id}" data-n="${w.n_passages}">${esc(w.title)} ${w.he_title ? "— " + esc(w.he_title) : ""} (${w.n_passages})</option>`).join("")}</select>
      <div class="row" style="margin-top:8px"><label>Finish by <input type="date" id="gE"></label></div><div class="row" style="justify-content:flex-end;margin-top:12px"><button class="btn" data-close>Cancel</button><button class="btn primary" id="gOk">Create</button></div>`, m => {
      const dd = new Date(); dd.setMonth(dd.getMonth() + 3); $("#gE", m).value = dd.toISOString().slice(0, 10);
      $("#gOk", m).onclick = async () => {
        const s = $("#gW", m), o = s.selectedOptions[0]; if (!o) return;
        await App.api("ud_save", { table: "goals", row: { work_id: +s.value, title: o.textContent.split(" (")[0], start_date: new Date().toISOString().slice(0, 10), end_date: $("#gE", m).value, total: +o.dataset.n, done: 0 } });
        App.closeModal(); Home.load(el);
      };
    });
  }
};
App.register("home", { title: "Home", icon: "🏠", render(el) { el.innerHTML = "<p class='muted'>Loading…</p>"; }, onShow() { Home.load(this.el); } });
