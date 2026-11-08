/* Plugins: manage add-ons (turn on/off, install from file, remove) + helper used by plugin pages */
const Plugins = {
  call(id, fn, args = {}) { return App.api("plugin_call", { id, fn, args }); },
  async render(el) {
    const list = await App.api("plugins");
    el.innerHTML = `<h1 class="page-title">🧩 Plugins <small>Add-ons that add screens, tools and Home cards. Turn them on or off, or install your own.</small>
      <span class="spacer"></span><button class="btn primary" id="plInst">📥 Install a plugin (.py / .zip)…</button></h1>
      <div class="grid g2">${list.map(p => `<div class="card">
        <div class="row"><span style="font-size:24px">${esc(p.icon || "🧩")}</span><div style="flex:1"><b>${esc(p.name)}</b> <span class="small muted">${esc(p.version || "")} ${p.builtin ? "· built-in" : "· added by you"}</span></div>
          <label class="row small" style="gap:4px"><input type="checkbox" data-t="${esc(p.id)}" ${p.enabled ? "checked" : ""}> On</label></div>
        <p class="small" style="margin:6px 0">${esc(p.description || "")}</p>
        ${p.error ? `<p class="small" style="color:var(--danger)">Problem: ${esc(p.error)}</p>` : ""}
        <div class="row small muted">${p.has_page ? "📄 has its own screen" : ""} ${p.tools.length ? `· 🧰 ${p.tools.length} tool(s)` : ""}<span class="spacer"></span>
          ${p.has_page ? `<button class="btn small" data-open="${esc(p.id)}">Open</button>` : ""}${p.builtin ? "" : `<button class="btn small danger" data-rm="${esc(p.id)}">Remove</button>`}</div></div>`).join("")}</div>
      <h2>Make your own plugin</h2><div class="card small"><p>A plugin is one Python file. Save it as <code>my_plugin.py</code> and install it here:</p>
      <pre style="white-space:pre-wrap;direction:ltr;background:var(--panel2);padding:8px;border-radius:8px">PLUGIN = {"id": "my_plugin", "name": "My plugin", "icon": "⭐", "version": "1.0", "description": "What it does"}
from core.tools import tool

@tool("My plugin", "Count words", "Counts the words in a text.")
def my_count(a, ctx=None):
    return f"{len(a.get('text', '').split())} words"

def home(app):                       # optional card on the Home screen
    return {"title": "Hello", "html": "&lt;p&gt;Shalom from my plugin&lt;/p&gt;"}

ROUTES = {"hello": lambda app, args: {"msg": "Shalom " + args.get("name", "")}}
PAGE_JS = """App.register("my_plugin", {title: "Mine", icon: "⭐", render(el) {
  el.innerHTML = '&lt;button class=btn id=b&gt;Say hello&lt;/button&gt;';
  el.querySelector('#b').onclick = async () =&gt; App.toast((await Plugins.call("my_plugin", "hello", {name: "Yisroel"})).msg);
}});"""</pre><p>Plugins can use everything in <code>core</code> (library search, gematria, calendar…) through <code>app.lib</code>, <code>app.user</code>, and store their own data with <code>app.pget</code>/<code>app.pset</code>.</p></div>`;
    $$("[data-t]", el).forEach(c => c.onchange = async () => { await App.api("plugin_toggle", { id: c.dataset.t, on: c.checked }); App.toast((c.checked ? "Turned on: " : "Turned off: ") + c.dataset.t + " — reloading…"); setTimeout(() => location.reload(), 700); });
    $$("[data-open]", el).forEach(b => b.onclick = () => App.show(b.dataset.open));
    $$("[data-rm]", el).forEach(b => b.onclick = async () => { if (await App.confirm("Remove this plugin?")) { await App.api("plugin_remove", { id: b.dataset.rm }); location.reload(); } });
    $("#plInst", el).onclick = async () => { const u = await App.uploadPicked(".py,.zip", false); if (!u.length) return; const r = await App.api("plugin_install", { upload: u[0].upload }); App.toast(r.error ? "Problem: " + r.error : "Installed " + r.name + " — reloading…"); setTimeout(() => location.reload(), 900); };
  }
};
App.register("plugins", { title: "Plugins", icon: "🧩", render(el) { Plugins.render(el); }, onShow() { if (this.el) Plugins.render(this.el); } });
