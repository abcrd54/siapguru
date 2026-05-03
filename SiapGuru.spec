# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules, copy_metadata


APP_NAME = os.environ.get("SIAPGURU_BUILD_NAME", "SiapGuru")
ENTRY_SCRIPT = "main.py"
APP_ICON = "assets\\icon.ico"
APP_DATAS = [
    ("ui/styles.qss", "ui"),
    ("assets/icon.ico", "assets"),
    ("assets/logo-siapguru.png", "assets"),
]

HIDDEN_IMPORTS = collect_submodules("firebase_admin") + collect_submodules("google.cloud.firestore")
BINARIES = collect_dynamic_libs("numpy")
DATAS = (
    APP_DATAS
    + copy_metadata("numpy")
    + copy_metadata("pandas")
    + copy_metadata("openpyxl")
    + copy_metadata("firebase-admin")
    + copy_metadata("google-cloud-firestore")
)


a = Analysis(
    [ENTRY_SCRIPT],
    pathex=[],
    binaries=BINARIES,
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[APP_ICON],
)
