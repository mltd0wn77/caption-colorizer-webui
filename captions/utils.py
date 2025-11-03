import subprocess
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"


def setup_logger(log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=log_path, level=logging.INFO, format=LOG_FORMAT)
    logging.getLogger().addHandler(logging.StreamHandler())


def which_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def detect_fps(video_path: Path) -> Optional[Tuple[int, int]]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=r_frame_rate",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        out = subprocess.check_output(cmd, text=True).strip()
        num, denom = out.split("/")
        return int(num), int(denom)
    except Exception:
        return None


def video_dimensions(video_path: Path) -> tuple[int, int] | None:
    """Return (width,height) of first video stream using ffprobe or None on failure."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:s=x",
        str(video_path),
    ]
    try:
        out = subprocess.check_output(cmd, text=True).strip()
        w, h = out.split("x")
        return int(w), int(h)
    except Exception:
        return None
