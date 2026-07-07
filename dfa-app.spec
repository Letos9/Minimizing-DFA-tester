# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ["src/dfa_app/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=["openpyxl", "matplotlib.backends.backend_qtagg"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DFA-Minimizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

