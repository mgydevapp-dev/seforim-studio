"""Seforim Studio plugin system.

A plugin is either one file  my_plugin.py  or a folder  my_plugin/plugin.py (+ page.js, + other files).
Built-in plugins live in <app>/plugins, your own in <data>/plugins (install from Plugins screen: .py or .zip).

A plugin module may define:
    PLUGIN = {"id": "my_plugin", "name": "My plugin", "description": "...", "version": "1.0", "icon": "🧩"}
    ROUTES = {"name": fn}              # fn(app, args: dict) -> JSON-able; called from the page with Plugins.call(id, name, args)
    PAGE_JS = "...javascript..."       # (or a page.js file next to plugin.py) adds a screen: App.register(id, {...})
    def home(app): return {"title": "...", "html": "..."}   # a card on the Home screen (optional)
    Tools: use  from core.tools import tool  and decorate functions — they appear in the Tools screen.
"""
import importlib.util
import json
import os
import shutil
import sys
import traceback
import zipfile

from . import tools as TL


class PluginManager:
    def __init__(self, app, dirs):
        self.app = app
        self.dirs = dirs  # [(path, builtin?)]
        self.plugins = {}  # id -> info dict (+ "module")
        self.load_all()

    # ------------------------------------------------------------------ discovery
    def _candidates(self):
        for d, builtin in self.dirs:
            if not os.path.isdir(d):
                continue
            for name in sorted(os.listdir(d)):
                p = os.path.join(d, name)
                if name.endswith(".py") and not name.startswith("_"):
                    yield p, p, builtin
                elif os.path.isdir(p) and os.path.exists(os.path.join(p, "plugin.py")):
                    yield os.path.join(p, "plugin.py"), p, builtin

    def disabled(self):
        return set(self.app.user.get_setting("plugins_disabled") or [])

    def load_all(self):
        for f, root, builtin in self._candidates():
            self._load(f, root, builtin)

    def _load(self, file, root, builtin):
        pid_guess = os.path.splitext(os.path.basename(root))[0]
        info = {"id": pid_guess, "name": pid_guess, "description": "", "version": "", "icon": "🧩", "builtin": builtin,
                "file": file, "root": root, "enabled": False, "error": None, "tools": [], "has_page": False, "module": None}
        meta = self._read_meta(file)
        info.update({k: v for k, v in meta.items() if k in ("id", "name", "description", "version", "icon")})
        pid = info["id"]
        if pid in self.plugins and self.plugins[pid]["builtin"] and not builtin:
            pid = info["id"] = pid + "_user"
        self.plugins[pid] = info
        if pid in self.disabled():
            return info
        before = len(TL.TOOLS)
        try:
            if os.path.dirname(file) not in sys.path:
                sys.path.append(os.path.dirname(file))
            spec = importlib.util.spec_from_file_location(f"seforim_plugin_{pid}", file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            info["module"] = mod
            info["enabled"] = True
            info["tools"] = [t["id"] for t in TL.TOOLS[before:]]
            for t in TL.TOOLS[before:]:
                t["category"] = t.get("category") or info["name"]
                t["plugin"] = pid
            info["has_page"] = bool(self.page_js(pid))
        except Exception as e:  # noqa
            del TL.TOOLS[before:]
            info["error"] = f"{e.__class__.__name__}: {e}"
            traceback.print_exc()
        return info

    @staticmethod
    def _read_meta(file):
        """Read PLUGIN = {...} without running the plugin (so disabled plugins still show their name)."""
        import ast
        try:
            tree = ast.parse(open(file, encoding="utf-8").read())
            for node in tree.body:
                if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "PLUGIN" for t in node.targets):
                    return ast.literal_eval(node.value)
        except Exception:
            pass
        return {}

    # ------------------------------------------------------------------ queries
    def page_js(self, pid):
        info = self.plugins.get(pid)
        if not info or not info["enabled"]:
            return ""
        js = getattr(info["module"], "PAGE_JS", "") or ""
        f = os.path.join(info["root"], "page.js") if os.path.isdir(info["root"]) else ""
        if f and os.path.exists(f):
            js += "\n" + open(f, encoding="utf-8").read()
        return js

    def all_js(self):
        out = []
        for pid, info in self.plugins.items():
            js = self.page_js(pid)
            if js:
                out.append(f"/* plugin {pid} */\ntry {{\n{js}\n}} catch (e) {{ console.error('Plugin {pid} failed', e); }}\n")
        return "\n".join(out)

    def listing(self):
        return [{k: v for k, v in i.items() if k not in ("module", "file", "root")} for i in self.plugins.values()]

    def call(self, pid, name, args):
        info = self.plugins.get(pid)
        if not info or not info["enabled"]:
            raise ValueError(f"Plugin '{pid}' is not turned on")
        fn = (getattr(info["module"], "ROUTES", {}) or {}).get(name)
        if not fn:
            raise ValueError(f"Plugin '{pid}' has no '{name}'")
        return fn(self.app, args or {})

    def home_cards(self):
        cards = []
        for pid, info in self.plugins.items():
            fn = info["enabled"] and getattr(info["module"], "home", None)
            if fn:
                try:
                    c = fn(self.app)
                    if c:
                        cards.append({"plugin": pid, "icon": info["icon"], **c})
                except Exception as e:  # noqa
                    cards.append({"plugin": pid, "title": info["name"], "html": f"<p class='small muted'>Error: {e}</p>"})
        return cards

    # ------------------------------------------------------------------ management
    def toggle(self, pid, on):
        dis = self.disabled()
        info = self.plugins.get(pid)
        if not info:
            raise ValueError("unknown plugin")
        if on:
            dis.discard(pid)
            self.app.user.set_setting("plugins_disabled", sorted(dis))
            if not info["enabled"]:
                self._load(info["file"], info["root"], info["builtin"])
        else:
            dis.add(pid)
            self.app.user.set_setting("plugins_disabled", sorted(dis))
            TL.TOOLS[:] = [t for t in TL.TOOLS if t.get("plugin") != pid]
            info.update(enabled=False, module=None, has_page=False, tools=[])
        return self.plugins[pid]

    def install(self, src_path, user_dir):
        os.makedirs(user_dir, exist_ok=True)
        name = os.path.basename(src_path)
        name = name.split("-", 1)[1] if len(name) > 7 and name[6] == "-" else name  # strip upload prefix
        if name.endswith(".py"):
            dest = os.path.join(user_dir, name)
            shutil.copy2(src_path, dest)
            info = self._load(dest, dest, False)
        elif name.endswith(".zip"):
            folder = os.path.join(user_dir, os.path.splitext(name)[0])
            with zipfile.ZipFile(src_path) as z:
                root = os.path.abspath(folder)
                for m in z.namelist():
                    t = os.path.abspath(os.path.join(folder, m))
                    if not t.startswith(root):
                        raise ValueError("unsafe zip")
                z.extractall(folder)
            # allow a zip that contains one top folder
            inner = [d for d in os.listdir(folder) if os.path.isdir(os.path.join(folder, d))]
            if not os.path.exists(os.path.join(folder, "plugin.py")) and len(inner) == 1:
                folder = os.path.join(folder, inner[0])
            if not os.path.exists(os.path.join(folder, "plugin.py")):
                raise ValueError("The zip must contain plugin.py")
            info = self._load(os.path.join(folder, "plugin.py"), folder, False)
        else:
            raise ValueError("Choose a .py or .zip plugin file")
        return {k: v for k, v in info.items() if k not in ("module",)}

    def remove(self, pid):
        info = self.plugins.get(pid)
        if not info or info["builtin"]:
            raise ValueError("Built-in plugins can be turned off but not removed")
        self.toggle(pid, False)
        if os.path.isdir(info["root"]):
            shutil.rmtree(info["root"], ignore_errors=True)
        elif os.path.exists(info["file"]):
            os.remove(info["file"])
        del self.plugins[pid]
        return True
