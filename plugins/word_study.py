PLUGIN = {"id": "word_study", "name": "Word Study", "icon": "🔤", "version": "1.0",
          "description": "Everything about one Hebrew word on one page: all gematria values, how often and where it appears, "
                         "its first appearance in Tanach, words with the same gematria, spelling variants and abbreviations."}

from core import hebrew as H
from core.library import skeleton


def study(app, a):
    word = H.letters_only(a.get("word", "")).strip()
    if not word:
        raise ValueError("Type a Hebrew word")
    lib = app.lib
    gem = [{"method": k, "value": fn(word)} for k, fn in H.GEMATRIA_METHODS.items()]
    std = H.g_standard(word)
    row = lib.q1("SELECT freq FROM words WHERE word=?", (word,))
    same = [r for r in lib.gematria_words(std, limit=40) if r["word"] != word][:30]
    variants = lib.q("SELECT word, freq FROM words WHERE skel=? AND word<>? ORDER BY freq DESC LIMIT 20", (skeleton(word), word))
    res = lib.search(word, "he", {}, None, 0, 1000, "book")
    by_book = {}
    for r in res.get("results", []):
        k = (r.get("title") or "", r.get("category_path") or "")
        by_book[k] = by_book.get(k, 0) + 1
    books = [{"title": t, "category": c, "n": n} for (t, c), n in sorted(by_book.items(), key=lambda kv: -kv[1])[:25]]
    first = next((r for r in res.get("results", []) if (r.get("category_path") or "").startswith("Tanakh")), None)
    from core.data_tables import ABBREV_CLEAN
    abbr = [{"abbr": k, "meaning": v} for k, v in ABBREV_CLEAN.items() if H.letters_only(k) == word][:10] if isinstance(ABBREV_CLEAN, dict) else []
    return {"word": word, "letters": len(word), "gematria": gem, "freq": row["freq"] if row else 0, "same_gematria": same,
            "variants": variants, "books": books, "hits": res.get("total", 0),
            "first_tanakh": {"ref": first["ref"], "he": first["he"]} if first else None, "abbrevs": abbr,
            "atbash": H.atbash(word), "reverse": word[::-1], "letters_names": " ".join(word)}


ROUTES = {"study": study}

PAGE_JS = r"""
App.register("word_study", { title: "Word Study", icon: "🔤", render(el) { WS.render(el); } });
const WS = {
  render(el) {
    el.innerHTML = `<h1 class="page-title">🔤 Word Study <small>type one Hebrew word</small></h1>
      <div class="row"><input id="wsW" class="he" style="font-size:22px;flex:1" placeholder="למשל: שלום"><button class="btn primary" id="wsGo">Study</button></div><div id="wsOut" style="margin-top:12px"></div>`;
    const go = async () => {
      const r = await Plugins.call("word_study", "study", { word: $("#wsW", el).value });
      const wl = xs => xs.map(x => `<a href="#" class="chip he" data-w="${esc(x.word)}">${esc(x.word)} <small>${x.freq}</small></a>`).join(" ") || `<span class="small muted">none</span>`;
      $("#wsOut", el).innerHTML = `<div class="grid g2">
        <div class="card"><h2 class="he" style="margin-top:0;font-size:34px">${esc(r.word)}</h2>
          <p class="small">${r.letters} letters · appears <b>${r.freq.toLocaleString()}</b> times in your library · in ${r.hits.toLocaleString()} passages · Atbash <span class="he">${esc(r.atbash)}</span></p>
          ${r.first_tanakh ? `<p><b>In Tanach:</b> <a href="#" data-ref="${esc(r.first_tanakh.ref)}">${esc(r.first_tanakh.ref)}</a><br><span class="he">${r.first_tanakh.he}</span></p>` : ""}
          <h3>Gematria</h3><table class="tbl">${r.gematria.map(g => `<tr><td class="small">${esc(g.method)}</td><td><b>${g.value}</b></td></tr>`).join("")}</table></div>
        <div class="card"><h3 style="margin-top:0">Same gematria (${r.gematria[0].value})</h3>${wl(r.same_gematria)}
          <h3>Other spellings (מלא / חסר)</h3>${wl(r.variants)}
          ${r.abbrevs.length ? `<h3>As an abbreviation</h3>${r.abbrevs.map(x => `<div class="small">${esc(x.abbr)} = ${esc(x.meaning)}</div>`).join("")}` : ""}
          <h3>Where it appears most</h3>${r.books.map(b => `<div class="list-item small row"><span style="flex:1">${esc(b.title)}</span><span class="muted">${b.n}</span></div>`).join("") || `<p class="small muted">Not found in the library</p>`}
          <button class="btn small" id="wsSearch" style="margin-top:6px">Show all in Search ›</button></div></div>`;
      $$("[data-w]", el).forEach(a => a.onclick = e => { e.preventDefault(); $("#wsW", el).value = a.dataset.w; go(); });
      $$("[data-ref]", el).forEach(a => a.onclick = e => { e.preventDefault(); App.quickGo(a.dataset.ref); });
      $("#wsSearch", el).onclick = () => { App.show("search"); Search.run(r.word); };
    };
    $("#wsGo", el).onclick = go; $("#wsW", el).onkeydown = e => { if (e.key === "Enter") go(); };
  }
};
"""
