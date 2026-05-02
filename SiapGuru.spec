# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import (
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)


hiddenimports = (
    collect_submodules('firebase_admin')
    + collect_submodules('google.cloud.firestore')
)

binaries = collect_dynamic_libs('numpy')

datas = (
    [('ui/styles.qss', 'ui'), ('assets/icon.ico', 'assets'), ('assets/logo-siapguru.png', 'assets'), ('servicekey-py.json', '.')]
    + copy_metadata('numpy')
    + copy_metadata('pandas')
    + copy_metadata('openpyxl')
    + copy_metadata('firebase-admin')
    + copy_metadata('google-cloud-firestore')
)


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='SiapGuru',
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
    icon=['assets\\icon.ico'],
)
