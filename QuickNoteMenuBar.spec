# -*- mode: python ; coding: utf-8 -*-

import os
import site

a = Analysis(
    ['quicknote_menubar.py'],
    pathex=[
        '/Users/jiamingli_1/QuickNote',
    ],
    binaries=[
        ('/Users/jiamingli_1/Library/Python/3.14/lib/python/site-packages/objc', 'objc'),
        ('/Users/jiamingli_1/Library/Python/3.14/lib/python/site-packages/rumps', 'rumps'),
    ],
    datas=[
        ('/Users/jiamingli_1/Library/Python/3.14/lib/python/site-packages/rumps', 'rumps'),
        ('/Users/jiamingli_1/Library/Python/3.14/lib/python/site-packages/PyObjCTools', 'PyObjCTools'),
        ('/Users/jiamingli_1/Library/Python/3.14/lib/python/site-packages/AppKit', 'AppKit'),
        ('/Users/jiamingli_1/Library/Python/3.14/lib/python/site-packages/Foundation', 'Foundation'),
        ('/Users/jiamingli_1/Library/Python/3.14/lib/python/site-packages/Cocoa', 'Cocoa'),
        ('/Users/jiamingli_1/Library/Python/3.14/lib/python/site-packages/CoreFoundation', 'CoreFoundation'),
        ('/Users/jiamingli_1/Library/Python/3.14/lib/python/site-packages/objc', 'objc'),
        ('/Users/jiamingli_1/QuickNote/resizable_input_panel.py', '.'),
    ],
    hiddenimports=[
        'Foundation',
        'AppKit',
        'PyObjCTools',
        'objc',
        'rumps',
        'resizable_input_panel',
    ],
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
    [],
    exclude_binaries=True,
    name='QuickNoteMenuBar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='QuickNoteMenuBar',
)
app = BUNDLE(
    coll,
    name='QuickNoteMenuBar.app',
    icon=None,
    bundle_identifier=None,
)
