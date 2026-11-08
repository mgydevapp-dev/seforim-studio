# PyInstaller recipe:  py -m PyInstaller SeforimStudio.spec --noconfirm
# Result: dist\SeforimStudio\SeforimStudio.exe  (copy the whole dist\SeforimStudio folder anywhere you like)
block_cipher = None
a = Analysis(
    ["SeforimStudio.py"],
    pathex=["."],
    datas=[("web", "web"), ("plugins", "plugins"), ("data/seforim_catalog.db", "data")] + ([("scanner/models", "scanner/models")] if __import__("os").path.isdir("scanner/models") else []),
    hiddenimports=["core.server", "core.library", "core.catalog", "core.tools", "core.formats", "core.share", "core.fonts",
                   "core.hcalendar", "core.he_names", "core.userdata", "core.data_tables", "core.order", "core.plugins",
                   "core.installer", "core.winproc", "ast", "difflib", "statistics", "random", "csv",
                   "scanner.cleanup", "scanner.engines", "pyluach", "pyluach.parshios", "docx", "pypdfium2"],
    excludes=["tkinter", "kraken", "torch", "matplotlib", "IPython", "pytest"],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="SeforimStudio", console=False, icon="web/icon.ico")
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name="SeforimStudio")
