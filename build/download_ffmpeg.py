#!/usr/bin/env python3
"""Download a static ffmpeg binary for the current platform into build/assets/.

Used at build time so the packaged app is fully offline ("解压即用").
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "build" / "assets"


def main():
    from static_ffmpeg import run
    print("Fetching static ffmpeg (may take a while)...")
    ffmpeg, _ = run.get_or_fetch_platform_executables_else_raise()

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    src = Path(ffmpeg)
    dest = ASSETS_DIR / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
    if dest.exists():
        dest.unlink()
    shutil.copy2(src, dest)
    print(f"Bundled ffmpeg -> {dest}")


if __name__ == "__main__":
    main()
