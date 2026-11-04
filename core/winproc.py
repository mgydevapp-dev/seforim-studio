"""Start other programs safely from the windowed (no-console) .exe.
Without explicit stdin/stdout handles Windows raises 'OSError: [WinError 6] The handle is invalid',
and console programs would flash a black window."""
import os
import subprocess

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def run(cmd, timeout=None, text=True):
    return subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=timeout, creationflags=NO_WINDOW,
                          **({"text": True, "encoding": "utf-8", "errors": "replace"} if text else {}))


def popen(cmd, hidden=False):
    return subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=NO_WINDOW if hidden else 0)
