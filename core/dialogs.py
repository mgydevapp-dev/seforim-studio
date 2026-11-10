"""Native Windows dialogs (choose a folder / open a file / save as), shown on top of the app window.
Works offline; uses PowerShell + Windows Forms on Windows, Tk elsewhere. Returns "" when cancelled."""
import base64
import os
import subprocess

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _ps(script, timeout=600):
    enc = base64.b64encode(("[Console]::OutputEncoding=[Text.Encoding]::UTF8\n" + script).encode("utf-16-le")).decode()
    r = subprocess.run(["powershell", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-EncodedCommand", enc],
                       capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    lines = (r.stdout or b"").decode("utf-8", "replace").strip().splitlines()
    return lines[-1].strip() if lines else ""


def _q(s):
    return "'" + (s or "").replace("'", "''") + "'"


OWNER = "$o = New-Object System.Windows.Forms.Form -Property @{TopMost=$true; ShowInTaskbar=$false; StartPosition='CenterScreen'; Width=1; Height=1}; $o.Show(); $o.Activate()\n"


def pick_folder(title="Choose a folder", start=""):
    if os.name == "nt":
        return _ps("Add-Type -AssemblyName System.Windows.Forms\n" + OWNER +
                   f"$f = New-Object System.Windows.Forms.FolderBrowserDialog; $f.Description = {_q(title)}; $f.ShowNewFolderButton = $true\n"
                   + (f"$f.SelectedPath = {_q(start)}\n" if start else "") +
                   "if ($f.ShowDialog($o) -eq 'OK') { $f.SelectedPath }")
    return _tk("folder", title, start)


def pick_file(title="Choose a file", start="", filters="All files|*.*", multi=False):
    if os.name == "nt":
        out = _ps("Add-Type -AssemblyName System.Windows.Forms\n" + OWNER +
                  f"$f = New-Object System.Windows.Forms.OpenFileDialog; $f.Title = {_q(title)}; $f.Filter = {_q(filters)}; $f.Multiselect = ${'true' if multi else 'false'}\n"
                  + (f"$f.InitialDirectory = {_q(start)}\n" if start else "") +
                  "if ($f.ShowDialog($o) -eq 'OK') { $f.FileNames -join '|' }")
        return out
    return _tk("file", title, start)


def save_as(title="Save as", name="", start="", filters="All files|*.*"):
    if os.name == "nt":
        ext = os.path.splitext(name)[1].lstrip(".")
        if ext and filters == "All files|*.*":
            filters = f"{ext.upper()} file|*.{ext}|All files|*.*"
        return _ps("Add-Type -AssemblyName System.Windows.Forms\n" + OWNER +
                   f"$f = New-Object System.Windows.Forms.SaveFileDialog; $f.Title = {_q(title)}; $f.FileName = {_q(name)}; $f.Filter = {_q(filters)}; $f.OverwritePrompt = $true\n"
                   + (f"$f.InitialDirectory = {_q(start)}\n" if start else "") +
                   "if ($f.ShowDialog($o) -eq 'OK') { $f.FileName }")
    return _tk("save", title, start, name)


def _tk(kind, title, start, name=""):
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return ""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        if kind == "folder":
            return filedialog.askdirectory(title=title, initialdir=start or None) or ""
        if kind == "save":
            return filedialog.asksaveasfilename(title=title, initialdir=start or None, initialfile=name) or ""
        return filedialog.askopenfilename(title=title, initialdir=start or None) or ""
    finally:
        root.destroy()
