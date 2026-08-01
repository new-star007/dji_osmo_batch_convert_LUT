#!/usr/bin/env python3
"""为当前平台下载静态 ffmpeg 到 build/assets/。

在打包时运行，使应用完全离线（"解压即用"）。

- Windows：使用 gyan.dev 的 essentials 构建，内置 NVIDIA (h264_nvenc)、
  AMD (h264_amf)、Intel QSV (h264_qsv)、VAAPI 硬件编码器以及 libx264。
  static_ffmpeg 包的 OSS 开源构建没有硬件编码器，这正是 Windows 上
  只有 libx264 能用的原因。
- macOS / Linux：使用 static_ffmpeg 的 OSS 构建（h264_videotoolbox / h264_vaapi）。
"""

import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "build" / "assets"

GYAN_ESSENTIALS_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def _download(url: str, dest: Path) -> None:
    print(f"Downloading {url}")
    with urllib.request.urlopen(url) as resp, open(dest, "wb") as fh:
        shutil.copyfileobj(resp, fh)
    print(f"Downloaded {dest} ({dest.stat().st_size / 1024 / 1024:.1f} MB)")


def _fetch_gyan_windows(dest: Path) -> None:
    """Windows：下载 gyan.dev 的 essentials 构建。

    该构建同时内置 NVIDIA (h264_nvenc)、AMD (h264_amf)、Intel QSV
    (h264_qsv) 与 VAAPI 硬件编码器，以及 libx264。若沿用 static_ffmpeg
    的 OSS 开源构建，Windows 上就只有 libx264 可用，硬件加速全部失效。
    """
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "ffmpeg-essentials.zip"
        _download(GYAN_ESSENTIALS_URL, zip_path)
        print("Extracting ffmpeg.exe...")
        with zipfile.ZipFile(zip_path) as zf:
            exe_name = next(
                name for name in zf.namelist()
                if name.endswith("bin/ffmpeg.exe")
            )
            with zf.open(exe_name) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)


def _fetch_static_ffmpeg(dest: Path) -> None:
    """macOS / Linux：使用 static_ffmpeg 的 OSS 开源构建。

    macOS 自带的 h264_videotoolbox、Linux 的 h264_vaapi 已可满足硬件加速需求，
    故这两个平台继续沿用 OSS 构建即可。
    """
    from static_ffmpeg import run
    print("Fetching static ffmpeg (may take a while)...")
    ffmpeg, _ = run.get_or_fetch_platform_executables_else_raise()
    shutil.copy2(Path(ffmpeg), dest)


def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    dest = ASSETS_DIR / exe_name
    if dest.exists():
        dest.unlink()

    if sys.platform == "win32":
        _fetch_gyan_windows(dest)
    else:
        _fetch_static_ffmpeg(dest)
    print(f"Bundled ffmpeg -> {dest}")


if __name__ == "__main__":
    main()
