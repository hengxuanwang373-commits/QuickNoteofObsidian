# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['quicknote_menubar.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['rumps', 'AppKit', 'Foundation', 'subprocess', 'json', 'pathlib', 'datetime', 'hashlib', 'shutil', 'tempfile'],
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
    name='QuickNoteMenuBar',
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
)
app = BUNDLE(
    exe,
    name='QuickNoteMenuBar.app',
    icon=None,
    bundle_identifier=None,
)
