#!/usr/bin/env bash
# Build the "解压即用" folder + zip for macOS / Linux.
# Usage: bash build/build.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"

echo "==> Installing build dependencies"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements.txt pyinstaller

echo "==> Downloading static ffmpeg"
"$PYTHON" build/download_ffmpeg.py

echo "==> Running PyInstaller"
rm -rf build/work dist
"$PYTHON" -m PyInstaller batch_lut.spec --workpath build/work --distpath dist

if [[ "$(uname)" == "Darwin" ]]; then
    echo "==> Ad-hoc signing (reduce Gatekeeper friction)"
    codesign --force --deep --sign - "dist/DJI LUT.app" 2>/dev/null || true

    echo "==> Creating zip"
    (cd dist && ditto -c -k --sequesterRsrc --keepParent "DJI LUT.app" "DJI-LUT-Converter-macOS.zip")
    echo "==> dist/DJI-LUT-Converter-macOS.zip"
else
    echo "==> Creating zip"
    (cd dist && zip -r "DJI-LUT-Converter-Linux.zip" "DJI LUT")
    echo "==> dist/DJI-LUT-Converter-Linux.zip"
fi
