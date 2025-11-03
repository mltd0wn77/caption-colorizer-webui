from __future__ import annotations

import os
from pathlib import Path
from typing import List

from .parser import Caption
from .timing import ms_to_frames


def build_frame_sequence(
    captions: List[Caption],
    fps: float,
    canvas_dims: tuple[int, int],
    png_dir: Path,
    seq_dir: Path,
):
    """Generate a PNG sequence directory with one file per frame.

    Each frame is a symlink to the active caption PNG or a blank transparent image.
    """
    seq_dir.mkdir(parents=True, exist_ok=True)
    blank = png_dir / "blank.png"
    if not blank.exists():
        from PIL import Image

        Image.new("RGBA", canvas_dims, (0, 0, 0, 0)).save(blank)

    # Map frame index to caption PNG
    frame_map = {}
    for cap in captions:
        fi = ms_to_frames(cap.start_ms, cap.end_ms, fps)
        png_name = f"cap_{cap.index:04d}.png"
        for f in range(fi.in_frame, fi.out_frame):
            frame_map[f] = png_name

    total_frames = max(frame_map.keys()) + 1 if frame_map else 0

    for f in range(total_frames):
        target = frame_map.get(f, "blank.png")
        link_name = seq_dir / f"{f:06d}.png"
        if link_name.exists():
            link_name.unlink()
        os.symlink(os.path.relpath(png_dir / target, seq_dir), link_name)
