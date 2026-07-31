# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the DJI LUT converter.

Build:  pyinstaller batch_lut.spec
Output: dist/DJI LUT.app   (macOS)
        dist/DJI_LUT/     (Windows / Linux)
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)
LUT = ROOT / "lib" / "DJI OSMO Pocket 3 D-Log M to Rec.709 V1.cube"
FFMPEG = ROOT / "build" / "assets" / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")

APP_NAME = "DJI LUT"
WINDOWED = True

if not LUT.is_file():
    raise SystemExit(f"LUT file not found: {LUT}")
if not FFMPEG.is_file():
    raise SystemExit(
        f"ffmpeg not found: {FFMPEG}\n"
        "Run `python build/download_ffmpeg.py` first.")

a = Analysis(
    [str(ROOT / "gui.py")],
    pathex=[str(ROOT)],
    binaries=[(str(FFMPEG), ".")],
    datas=[(str(LUT), "lib")],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=APP_NAME + ".app",
        icon=None,
        bundle_identifier="com.example.djilutconverter",
        info_plist={
            "CFBundleName": "DJI LUT",
            "CFBundleDisplayName": "DJI LUT 批量转换工具",
            "CFBundleShortVersionString": "1.1.0",
            "CFBundleVersion": "1.1.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
        },
    )
