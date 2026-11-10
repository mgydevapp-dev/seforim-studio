/* Translate: Hebrew word -> English meanings, English -> Hebrew words, a sentence word by word — offline. */
App.register("translate", {
  title: "Translate", icon: "🌐",
  render(el) {
    el.innerHTML = `<h1 class="page-title">🌐 Translate <small>Hebrew ↔ English · offline dictionary + how your seforim translate it</small></h1>
      <div class="card"><div class="row" style="gap:8px">
        <input id="trQ" class="tr-in" placeholder="Type a Hebrew word (שלום) or an English word (peace) — or a whole pasuk for word-by-word" style="flex:1">
        <button class="btn primary" id="trGo">Translate</button><button class="btn" id="trSwap" title="Use the Hebrew keyboard">א/A</button></div>
        <div class="small muted" style="margin-top:6px">Try: <a href="#" data-ex="בראשית">בראשית</a> · <a href="#" data-ex="ובבית">ובבית</a> · <a href="#" data-ex="מצוה">מצוה</a> · <a href="#" data-ex="peace">peace</a> · <a href="#" data-ex="to bless">to bless</a> · <a href="#" data-ex="בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם">a whole pasuk</a></div></div>
      <div id="trOut" style="margin-top:12px"></div>`;
    const go = () => this.run($("#trQ", el).value);
    $("#trGo", el).onclick = go; $("#trQ", el).onkeydown = e => { if (e.key === "Enter") go(); };
    $("#trSwap", el).onclick = () => { App.setHeb(!App.state.heb); $("#trQ", el).focus(); };
    $$("[data-ex]", el).forEach(a => a.onclick = e => { e.preventDefault(); $("#trQ", el).value = a.dataset.ex; go(); });
    this.el = el;
  },
  async run(q) {
    const out = $("#trOut", this.el); if (!q.trim()) return;
    out.innerHTML = `<p class="muted">Looking up…</p>`;
    const r = await App.api("translate", { q });
    const ent = e => `<div class="tr-ent"><div class="row" style="gap:8px;align-items:baseline"><span class="he tr-w">${esc(e.word)}</span><span class="small muted">${esc(e.pos || "")}${e.lang === "arc" ? " · Aramaic" : ""}</span><span class="spacer"></span><span class="badge">${esc(e.source)}${e.strong ? " " + esc(e.strong) : ""}</span></div>
      <div class="tr-g">${esc(e.gloss)}</div>${e.via ? `<div class="small muted">${esc(e.via)}</div>` : ""}</div>`;
    let html = "";
    if (!r.dictionary) html += `<div class="lib-health">The offline dictionary is not in this version — showing how your seforim translate it.</div>`;
    if (r.dir === "he-en") {
      if (r.word_by_word && r.word_by_word.length) html += `<div class="card"><h3 style="margin-top:0">Word by word</h3><div class="inter-words">${r.word_by_word.map(w => `<span class="iw"><span class="iw-he">${esc(w.he)}</span><span class="iw-en">${esc(w.en || "·")}</span></span>`).join("")}</div>
        <p class="small muted">Each word's dictionary meaning — a reading help, not a polished translation.</p></div>`;
      if (r.entries.length) html += `<div class="card"><h3 style="margin-top:0">${esc(r.q)} — meanings</h3>${r.entries.map(ent).join("")}</div>`;
      else if (!r.word_by_word.length) html += `<div class="card"><p>Not found in the dictionary.</p></div>`;
    } else {
      if (r.entries.length) html += `<div class="card"><h3 style="margin-top:0">“${esc(r.q)}” in Hebrew</h3><div class="tr-grid">${r.entries.map(ent).join("")}</div></div>`;
      if (r.library && r.library.length) html += `<div class="card"><h3 style="margin-top:0">How your seforim translate “${esc(r.q)}”</h3><div>${r.library.map(w => `<a href="#" class="chip he" data-w="${esc(w.word || w.he || w)}">${esc(w.word || w.he || w)}</a>`).join(" ")}</div></div>`;
    }
    if (r.examples && r.examples.length) html += `<div class="card"><h3 style="margin-top:0">In the seforim</h3>${r.examples.map(x => `<div class="tr-ex"><a href="#" data-ref="${esc(x.ref)}" class="small">${esc(x.ref)} ›</a><div class="he">${esc(x.he)}</div><div class="small">${esc(x.en)}</div></div>`).join("")}</div>`;
    out.innerHTML = html || `<p class="muted">Nothing found.</p>`;
    $$("[data-ref]", out).forEach(a => a.onclick = e => { e.preventDefault(); App.quickGo(a.dataset.ref); });
    $$("[data-w]", out).forEach(a => a.onclick = e => { e.preventDefault(); $("#trQ", this.el).value = a.dataset.w; this.run(a.dataset.w); });
    $$(".tr-w", out).forEach(a => { a.style.cursor = "pointer"; a.onclick = () => { $("#trQ", this.el).value = a.textContent; this.run(a.textContent); }; });
  }
});
