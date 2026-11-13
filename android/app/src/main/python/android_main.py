"""Seforim Studio on Android: start the same engine as the Windows app (core/server.py) inside the phone app.
MainActivity.java calls start(config_json) and then shows http://127.0.0.1:<port>/ in a WebView."""
import json
import os
import shutil
import sys
import threading

PORT = 48765  # fixed, so the pages keep their settings (they are remembered per address)


class _Tee:
    def __init__(self, *outs):
        self.outs = outs

    def write(self, s):
        for o in self.outs:
            try:
                o.write(s)
            except Exception:
                pass

    def flush(self):
        for o in self.outs:
            try:
                o.flush()
            except Exception:
                pass


def storage_choice(files_dir, storages):
    """Where the big things go (library ~12 GB, AI ~3.5 GB): the place chosen in the app, else an SD card when
    there is one, else the phone's storage."""
    f = os.path.join(files_dir, "storage.json")
    try:
        p = json.load(open(f, encoding="utf-8")).get("path")
        if p:
            os.makedirs(p, exist_ok=True)
            return p
    except Exception:
        pass
    sd = [s for s in storages if s.get("removable")]
    best = (sd or storages or [{"path": os.path.join(files_dir, "big")}])[0]["path"]
    os.makedirs(best, exist_ok=True)
    return best


def start(cfg_json):
    cfg = json.loads(cfg_json)
    app_dir, files_dir = cfg["app"], cfg["files"]
    os.environ["SEFORIM_ANDROID"] = "1"
    os.environ["SEFORIM_ANDROID_CFG"] = cfg_json
    os.environ.setdefault("HOME", files_dir)
    data = os.path.join(files_dir, "data")
    os.makedirs(data, exist_ok=True)
    log = open(os.path.join(data, "app_log.txt"), "a", encoding="utf-8", buffering=1)
    sys.stdout = _Tee(sys.__stdout__ or sys.stdout, log)
    sys.stderr = _Tee(sys.__stderr__ or sys.stderr, log)
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    shared = storage_choice(files_dir, cfg.get("storages") or [])
    os.environ["SEFORIM_SHARED"] = shared
    print("Seforim Studio (Android) starting; big files in", shared, flush=True)
    bundled = os.path.join(app_dir, "data", "seforim_catalog.db")
    target = os.path.join(shared, "seforim_catalog.db")
    if os.path.exists(bundled) and (not os.path.exists(target) or os.path.getsize(target) != os.path.getsize(bundled)):
        try:
            shutil.copyfile(bundled, target)
        except OSError as e:
            print("catalog copy:", e)
    from core.server import App, serve
    app = App(app_dir, data, shared)
    try:
        srv = serve(app, PORT)
    except OSError:
        srv = serve(app, 0)
    globals()["_app"], globals()["_srv"] = app, srv
    return srv.server_address[1]
