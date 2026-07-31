#!/usr/bin/env python3
"""Batch apply LUT to DJI D-Log M videos using FFmpeg (CLI)."""

import argparse
import sys
from pathlib import Path

from core import (
    DEFAULT_INPUT,
    DEFAULT_OUTPUT,
    DEFAULT_LUT,
    find_ffmpeg,
    get_video_files,
    pick_encoder,
    convert,
)


def main():
    parser = argparse.ArgumentParser(description="Batch apply LUT to videos with FFmpeg.")
    parser.add_argument("-i", "--input", default=str(DEFAULT_INPUT), help=f"Input directory (default: {DEFAULT_INPUT})")
    parser.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT), help=f"Output directory (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--lut", default=str(DEFAULT_LUT), help=f"LUT .cube file (default: {DEFAULT_LUT.name})")
    parser.add_argument("--encoder", default=None,
                        help="Force video encoder (default: auto-detect, e.g. h264_videotoolbox/libx264)")
    args = parser.parse_args()

    ffmpeg, source = find_ffmpeg()
    if not ffmpeg:
        print("Error: ffmpeg not found. Install it (e.g. `brew install ffmpeg`) or run `pip install -r requirements.txt`.")
        sys.exit(1)
    encoder = args.encoder or pick_encoder(ffmpeg)
    print(f"Using ffmpeg ({source}): {ffmpeg}")
    print(f"Video encoder: {encoder}\n")

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    videos = get_video_files(input_dir)
    if not videos:
        print(f"No video files found in {input_dir}.")
        sys.exit(1)

    lut = Path(args.lut)
    print(f"Found {len(videos)} video(s) in {input_dir}, LUT: {lut.name}\n")
    for v in videos:
        print(f"[CONVERT] {v.name} ({encoder})", flush=True)
        result = convert(v, output_dir, ffmpeg, encoder, lut,
                         on_error=lambda msg: print(msg, flush=True))
        if result == "skipped":
            print(f"[SKIP] {v.name}")
        elif result == "failed":
            print(f"[FAIL] {v.name}")
    print("\nAll done.")


if __name__ == "__main__":
    main()
