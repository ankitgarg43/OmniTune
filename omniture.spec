# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the portable single-file OmniTune.exe.

Build with:  pyinstaller omniture.spec --noconfirm --clean
"""

block_cipher = None

a = Analysis(
    ["src/omniture/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        # Bundled resources (TuneUp PowerShell script, future assets).
        ("src/omniture/resources", "omniture/resources"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="OmniTune",
    icon="src/omniture/resources/icon/omniture.ico",
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
    # Request administrator rights at launch (one UAC prompt, no installer).
    uac_admin=True,
    uac_uiaccess=False,
)
