"""Offline sharing between two copies of Seforim Studio.
- LAN: both computers on the same Wi-Fi / hotspot / cable (no internet needed). Each app announces itself by
  UDP broadcast; the receiver shows a 6-digit pairing code which the sender must type.
- Bluetooth: exports a .seforim package and opens the operating system's Bluetooth file-send dialog."""
import json
import os
import platform
import random
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid

DISCOVERY_PORT = 47474


class ShareHub:
    def __init__(self, inbox_dir, name=None):
        self.inbox_dir = inbox_dir
        os.makedirs(inbox_dir, exist_ok=True)
        self.id = uuid.uuid4().hex[:10]
        self.name = name or platform.node() or "Seforim Studio"
        self.port = None
        self.enabled = False
        self.code = f"{random.randint(0, 999999):06d}"
        self.peers = {}
        self._threads = []
        self._stop = threading.Event()

    # ---------------------------------------------------------------- discovery
    def start(self, http_port):
        self.port = http_port
        self.enabled = True
        self._stop.clear()
        for fn in (self._announce, self._listen):
            t = threading.Thread(target=fn, daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self):
        self.enabled = False
        self._stop.set()

    def _announce(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        msg = lambda: json.dumps({"app": "SeforimStudio", "id": self.id, "name": self.name, "port": self.port}).encode()
        while not self._stop.is_set():
            for addr in ("255.255.255.255", "127.0.0.1"):
                try:
                    s.sendto(msg(), (addr, DISCOVERY_PORT))
                except OSError:
                    pass
            self._stop.wait(3)
        s.close()

    def _listen(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass
        try:
            s.bind(("", DISCOVERY_PORT))
        except OSError:
            return
        s.settimeout(1)
        while not self._stop.is_set():
            try:
                data, (ip, _) = s.recvfrom(4096)
                js = json.loads(data)
                if js.get("app") == "SeforimStudio" and js.get("id") != self.id:
                    self.peers[js["id"]] = {"id": js["id"], "name": js["name"], "ip": ip, "port": js["port"], "seen": time.time()}
            except (socket.timeout, ValueError, OSError):
                pass
        s.close()

    def peer_list(self):
        now = time.time()
        return [p for p in self.peers.values() if now - p["seen"] < 15]

    def add_manual_peer(self, ip, port):
        pid = f"manual-{ip}-{port}"
        self.peers[pid] = {"id": pid, "name": f"{ip}:{port}", "ip": ip, "port": int(port), "seen": time.time() + 10 ** 9}
        return pid

    # ---------------------------------------------------------------- transfer
    def send(self, peer_id, package_path, code, sender_name=None):
        p = self.peers.get(peer_id)
        if not p:
            raise ValueError("That computer is no longer visible")
        with open(package_path, "rb") as f:
            data = f.read()
        req = urllib.request.Request(f"http://{p['ip']}:{p['port']}/share/inbox", data=data, method="POST",
                                     headers={"X-Pair-Code": code, "X-Sender": (sender_name or self.name).encode("utf-8").hex(),
                                              "X-Filename": os.path.basename(package_path).encode("utf-8").hex(),
                                              "Content-Type": "application/zip"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 403:
                raise ValueError("The other computer refused it — check the 6-digit code and that receiving is turned on there")
            raise ValueError(f"Sending failed ({e.code})")
        except OSError as e:
            raise ValueError(f"Could not reach that computer ({e.__class__.__name__}). Are both on the same network?")

    def receive(self, data, code, sender, filename):
        if not self.enabled:
            return 403, {"error": "Receiving is turned off"}
        if code != self.code:
            return 403, {"error": "Wrong pairing code"}
        safe = "".join(c for c in filename if c.isalnum() or c in "-_. ")[:80] or "package.seforim"
        path = os.path.join(self.inbox_dir, f"{int(time.time())}-{safe}")
        with open(path, "wb") as f:
            f.write(data)
        with open(path + ".from", "w", encoding="utf-8") as f:
            f.write(sender)
        return 200, {"ok": True}

    def inbox(self):
        out = []
        for fn in sorted(os.listdir(self.inbox_dir), reverse=True):
            if fn.endswith(".from"):
                continue
            p = os.path.join(self.inbox_dir, fn)
            sender = ""
            if os.path.exists(p + ".from"):
                with open(p + ".from", encoding="utf-8") as f:
                    sender = f.read()
            out.append({"file": fn, "from": sender, "size": os.path.getsize(p), "time": os.path.getmtime(p)})
        return out

    def remove(self, fn):
        p = os.path.join(self.inbox_dir, os.path.basename(fn))
        for x in (p, p + ".from"):
            if os.path.exists(x):
                os.remove(x)


def local_ips():
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))  # no packet is sent; only picks the LAN interface
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(i for i in ips if not i.startswith("127."))


def bluetooth_send(path):
    """Open the OS Bluetooth send dialog for a file."""
    sysname = platform.system()
    try:
        if sysname == "Windows":
            subprocess.Popen(["fsquirt.exe"])  # Windows Bluetooth File Transfer wizard (choose the file shown in the folder)
            subprocess.Popen(["explorer", "/select,", os.path.abspath(path)])
            return "Bluetooth wizard opened. Choose 'Send files', pick the device, then select the highlighted file."
        if sysname == "Darwin":
            subprocess.Popen(["open", "-a", "Bluetooth File Exchange", path])
            return "Bluetooth File Exchange opened."
        subprocess.Popen(["bluetooth-sendto", path])
        return "Bluetooth send dialog opened."
    except Exception as e:  # noqa
        return f"Could not open Bluetooth dialog ({e}). The file is saved at: {path}"


def bluetooth_receive():
    sysname = platform.system()
    try:
        if sysname == "Windows":
            subprocess.Popen(["fsquirt.exe", "-receive"])
            return "Waiting for a Bluetooth file. When it arrives, use Import to open the .seforim file."
        if sysname == "Darwin":
            return "On Mac, turn on Bluetooth Sharing in System Settings → General → Sharing, then Import the received file."
        return "Use your system's Bluetooth receive option, then Import the received file."
    except Exception as e:  # noqa
        return f"Could not open Bluetooth receive ({e})."
