from pathlib import Path
from unittest.mock import patch
import tempfile
from PIL import ImageFont

from captions.renderer import CaptionRenderer
from captions.config import load_config

SRT_TEXT = """1\n00:00:00,000 --> 00:00:01,000\nHello world!\n\n2\n00:00:01,200 --> 00:00:02,000\nAnother line\n"""


def test_images_mode_generates_files(tmp_path: Path):
    srt_path = tmp_path / "test.srt"
    srt_path.write_text(SRT_TEXT, encoding="utf-8")

    video_path = tmp_path / "dummy.mov"
    video_path.touch()  # empty placeholder

    out_dir = tmp_path / "out"

    cfg = load_config()
    renderer = CaptionRenderer(cfg)

    dejavu_path = Path(ImageFont.__file__).parent / "fonts/DejaVuSans.ttf"

    with patch("captions.utils.detect_fps", return_value=30.0), patch(
        "captions.utils.video_dimensions", return_value=(1920, 1080)
    ), patch("captions.text_render.TextRenderer._find_font_path", return_value=str(dejavu_path)), patch(
        "captions.text_render.TextRenderer._get_font", lambda self, size, weight: ImageFont.load_default()
    ):
        renderer.render(
            mode="images-xml",
            video=video_path,
            srt=srt_path,
            out=out_dir,
            track_index=2,
            seed=123,
            show_progress=False,
        )

    assert (out_dir / "captions_manifest.csv").exists()
    assert (out_dir / "captions.fcpxml").exists()
    pngs = list(out_dir.glob("*.png"))
    # Should have 2 pngs for 2 captions
    assert len(pngs) == 2
