"""Seforim Studio on Android: start the same engine as the Windows app (core/server.py) inside the phone app.
MainActivity.java calls start(config_json); the WebView then sends every request to handle() - no server, no network."""
import io
import json
import os
import shutil
import sys
import threading



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
    os.environ["SEFORIM_LLAMA_URL"] = "unix:" + os.path.join(files_dir, "llama.sock")  # the AI: no network at all
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
    from core.server import App, make_handler
    app = App(app_dir, data, shared)
    globals()["_app"], globals()["_handler"] = app, make_handler(app)
    print("Seforim Studio (Android) ready - no server, the pages talk to the engine directly", flush=True)
    return 0


class _Conn:
    """Stands in for a network connection: the request comes from the app's WebView, the answer goes back to it."""

    def __init__(self, data):
        self.r, self.out = io.BytesIO(data), bytearray()

    def makefile(self, mode, *a, **k):
        return self.r

    def sendall(self, b):
        self.out += b

    def settimeout(self, t):
        pass

    def setsockopt(self, *a):
        pass

    def close(self):
        pass


def handle(raw):
    """One HTTP request (bytes) from the WebView -> the complete HTTP answer (bytes). Same code as the Windows app."""
    c = _Conn(bytes(raw))
    try:
        _handler(c, ("127.0.0.1", 0), None)
    except Exception:  # noqa
        import traceback
        traceback.print_exc()
        if not c.out:
            return b"HTTP/1.1 500 Error\r\nContent-Type: application/json\r\nContent-Length: 30\r\n\r\n" + b'{"error": "engine error"}     '
    return bytes(c.out)
