"""Shared batch LUT conversion logic used by both the CLI and the GUI."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "input"
DEFAULT_OUTPUT = BASE_DIR / "output"
DEFAULT_LUT = BASE_DIR / "lib" / "DJI OSMO Pocket 3 D-Log M to Rec.709 V1.cube"
EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}

ENCODER_PREFERENCE = {
    "Darwin": ["h264_videotoolbox", "libx264"],
    "Windows": ["h264_nvenc", "h264_amf", "libx264"],
    "Linux": ["h264_nvenc", "h264_vaapi", "libx264"],
}
FALLBACK_ENCODER = "libx264"

IS_FROZEN = getattr(sys, "frozen", False)


def app_home() -> Path:
    """User-facing folder that ships alongside the app (input/output defaults).

    For a frozen macOS .app bundle this is the folder containing the .app,
    otherwise the folder containing the executable.
    """
    if IS_FROZEN:
        exe_dir = Path(sys.executable).resolve().parent
        if platform.system() == "Darwin" and exe_dir.name == "MacOS":
            return exe_dir.parent.parent.parent
        return exe_dir
    return BASE_DIR


def resource_path(relative: str) -> Path:
    """Resolve a bundled resource path for both dev and PyInstaller builds."""
    if IS_FROZEN:
        meipass = Path(getattr(sys, "_MEIPASS", BASE_DIR))
        return meipass / relative
    return BASE_DIR / relative


def user_lut_dir() -> Path:
    """Directory for user-uploaded LUT files (persists next to the app)."""
    directory = app_home() / "luts"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def available_luts():
    """Built-in LUT first, then user-uploaded .cube files."""
    luts = []
    if DEFAULT_LUT.is_file():
        luts.append(DEFAULT_LUT)
    for f in sorted(user_lut_dir().glob("*.cube")):
        if DEFAULT_LUT.resolve() != f.resolve() and f not in luts:
            luts.append(f)
    return luts


def import_lut(src: Path) -> Path:
    """Copy a user LUT into the user LUT directory. Returns the copy path."""
    dest = user_lut_dir() / src.name
    if dest.exists():
        dest.unlink()
    shutil.copy2(src, dest)
    return dest


def bundled_ffmpeg() -> Path | None:
    """Locate the ffmpeg binary bundled alongside the executable.

    Covers macOS .app bundles (Contents/Frameworks, Contents/Resources)
    as well as Windows / Linux one-dir layouts (_internal or exe dir).
    """
    if not IS_FROZEN:
        return None
    exe_name = "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"
    exe_dir = Path(sys.executable).resolve().parent
    meipass = Path(getattr(sys, "_MEIPASS", ""))
    candidates = [
        meipass / exe_name,
        exe_dir / exe_name,
        exe_dir / "_internal" / exe_name,
        exe_dir.parent / "Frameworks" / exe_name,
        exe_dir.parent.parent / "Frameworks" / exe_name,
        exe_dir.parent / "Resources" / exe_name,
        exe_dir.parent.parent / "Resources" / exe_name,
    ]
    seen = set()
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        try:
            if cand.is_file():
                return cand
        except OSError:
            continue
    return None


def build_asset_ffmpeg() -> Path | None:
    """Static ffmpeg downloaded by build/download_ffmpeg.py (dev mode)."""
    if IS_FROZEN:
        return None
    exe_name = "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"
    asset = BASE_DIR / "build" / "assets" / exe_name
    try:
        return asset if asset.is_file() else None
    except OSError:
        return None


def find_ffmpeg():
    bundled = bundled_ffmpeg()
    if bundled:
        return bundled, "bundled"
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return Path(ffmpeg), "system"
    asset = build_asset_ffmpeg()
    if asset:
        return asset, "bundled-asset"
    try:
        from static_ffmpeg import run
        ffmpeg, _ = run.get_or_fetch_platform_executables_else_raise()
        return Path(ffmpeg), "static-ffmpeg"
    except Exception:
        pass
    try:
        import imageio_ffmpeg
        return Path(imageio_ffmpeg.get_ffmpeg_exe()), "imageio-ffmpeg"
    except Exception:
        pass
    return None, None


def pick_encoder(ffmpeg):
    try:
        encoders = subprocess.run(
            [str(ffmpeg), "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=30,
        ).stdout
    except Exception:
        encoders = ""
    pref = ENCODER_PREFERENCE.get(platform.system(), [FALLBACK_ENCODER])
    for enc in pref:
        if enc in encoders:
            return enc
    return FALLBACK_ENCODER


def get_video_files(directory: Path):
    return sorted(
        f for f in directory.iterdir()
        if f.suffix.lower() in EXTENSIONS and f.is_file()
    )


def escape_filter_arg(value: str) -> str:
    """Escape a value for use inside an ffmpeg filtergraph argument.

    The value passes through two parsers (the filtergraph parser and the
    per-filter option parser), each of which treats backslash as an escape
    character, so literal backslashes and quotes must be doubled. A literal
    colon must also be escaped so the option parser does not split on it.
    Without this, Windows paths like ``C:\\Users\\...`` inside ``lut3d=``
    are mangled (e.g. ``C:`` becomes the filename and ``\\U`` collapses to
    ``U``) and the conversion fails.
    """
    option_level = value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return option_level.replace("\\", "\\\\").replace("'", "\\'")


def build_command(video: Path, output: Path, ffmpeg, encoder: str, lut: Path):
    return [
        str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error", "-nostats",
        "-progress", "pipe:2",
        "-i", str(video),
        "-vf", f"lut3d={escape_filter_arg(str(lut))}",
        "-c:v", encoder,
        "-b:v", "50M",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output),
    ]


def convert(video: Path, output_dir: Path, ffmpeg, encoder: str,
            lut: Path, on_progress=None, should_stop=None, on_error=None):
    """Convert a single video. Returns "ok", "skipped", "cancelled" or "failed".
    on_progress(duration, processed) receives floats in seconds and is
    called periodically. on_error(message) receives the last ffmpeg error
    lines when a conversion fails. If should_stop() returns True while
    running, the ffmpeg process is terminated and the partial output file
    is removed."""
    out = output_dir / f"{video.stem}_rec709.mp4"
    if out.exists():
        return "skipped"

    duration = probe_duration(ffmpeg, video)
    cmd = build_command(video, out, ffmpeg, encoder, lut)
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    error_lines = []
    for line in process.stdout:
        if should_stop and should_stop():
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            if out.exists():
                out.unlink(missing_ok=True)
            return "cancelled"
        stripped = line.strip()
        if stripped and not stripped.startswith("out_time"):
            error_lines.append(stripped)
        if not on_progress:
            continue
        if line.startswith("out_time="):
            processed = parse_time(line.split("=", 1)[1])
            if processed is not None:
                on_progress(duration, processed)
        elif line.startswith("out_time_us="):
            try:
                processed = int(line.split("=", 1)[1].strip()) / 1_000_000
            except ValueError:
                continue
            on_progress(duration, processed)
    process.wait()
    if process.returncode != 0 and on_error:
        on_error("\n".join(error_lines[-10:]) or f"ffmpeg 退出码 {process.returncode}")
    return "ok" if process.returncode == 0 else "failed"

def probe_duration(ffmpeg, video: Path):
    try:
        result = subprocess.run(
            [str(ffmpeg), "-hide_banner", "-i", str(video)],
            capture_output=True, text=True, timeout=30,
        )
        text = result.stderr
    except Exception:
        return None
    for line in text.splitlines():
        if "Duration:" not in line:
            continue
        tokens = line.split()
        for i, token in enumerate(tokens):
            if token.startswith("Duration:"):
                raw = tokens[i + 1].rstrip(",") if i + 1 < len(tokens) else ""
                if not raw:
                    raw = token[len("Duration:"):].rstrip(",")
                try:
                    h, m, s = raw.split(":")
                    return int(h) * 3600 + int(m) * 60 + float(s)
                except ValueError:
                    return None
    return None


def parse_time(line: str):
    try:
        raw = line.split("time=")[1].split()[0]
        h, m, s = raw.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        return None
