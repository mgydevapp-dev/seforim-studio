/* Phones: the side menu becomes a slide-out menu (☰), and the phone's Back button goes back inside the app */
(() => {
  const tb = document.getElementById("topbar"); if (!tb) return;
  const b = document.createElement("button"); b.id = "menuBtn"; b.className = "icon-btn"; b.title = "Menu"; b.textContent = "☰";
  tb.prepend(b);
  let last = 0;  // a finger tap gives touchend and then click - act on the first only
  const toggle = e => {
    e.preventDefault(); e.stopPropagation();
    const now = Date.now(); if (now - last < 500) return; last = now;
    document.body.classList.toggle("rail-open");
  };
  b.addEventListener("touchend", toggle);
  b.addEventListener("click", toggle);
  document.addEventListener("click", e => {
    if (!document.body.classList.contains("rail-open") || Date.now() - last < 500) return;
    if (e.target.closest("#rail button") || !e.target.closest("#rail")) document.body.classList.remove("rail-open");
  });
  // Library on a phone: the list of seforim and the open sefer take turns on the screen
  if (typeof Library !== "undefined") {
    const open = Library.open.bind(Library), render = Library.render.bind(Library);
    Library.render = function (el) {
      render(el);
      const t = el.querySelector("#rTool");
      if (t) { const b = document.createElement("button"); b.id = "mBooks"; b.className = "btn small"; b.textContent = "📚 Seforim"; t.prepend(b);
        b.onclick = () => el.querySelector(".lib-wrap").classList.remove("has-book"); }
    };
    Library.open = async function (...a) { const w = document.querySelector("#page-library .lib-wrap"); if (w) w.classList.add("has-book"); return open(...a); };
  }
  const hist = [];
  const show = App.show.bind(App);
  App.show = function (id, arg) { if (this.current && this.current !== id) { hist.push(this.current); if (hist.length > 30) hist.shift(); } return show(id, arg); };
  window.AndroidBack = () => {
    if (document.body.classList.contains("rail-open")) { document.body.classList.remove("rail-open"); return true; }
    if (!document.getElementById("modalWrap").classList.contains("hidden")) { App.closeModal(); return true; }
    const osk = document.getElementById("osk"); if (osk && !osk.classList.contains("hidden")) { osk.classList.add("hidden"); return true; }
    if (hist.length) { const p = hist.pop(); show(p); return true; }
    if (App.current !== "home") { show("home"); return true; }
    return false;
  };
})();
