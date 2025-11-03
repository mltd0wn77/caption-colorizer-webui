from pathlib import Path
from typing import Dict
import logging
import subprocess
from PIL import Image

class CaptionRenderer:
    """Facade that orchestrates either video burn-in or images-xml rendering. Only a skeletal implementation for v0.1."""

    def __init__(self, cfg: Dict, dry_run: bool = False):
        self.cfg = cfg
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)

    def render(self, mode: str, video: Path, srt: Path, out: Path, track_index: int = 2, seed: int | None = None, show_progress: bool = False):
        if mode == "video":
            raise ValueError("video rendering disabled in current version")
        elif mode == "images-xml":
            return self._render_images_xml(video, srt, out, track_index, seed, show_progress)
        elif mode == "export":
            return self._export_pngs(video, srt, out, seed, show_progress)
        else:
            raise ValueError(f"Unknown mode: {mode}")

    def _render_video(self, video: Path, srt: Path, out: Path, seed: int | None, show_progress: bool):
        from tempfile import TemporaryDirectory
        import random
        from .parser import parse_srt, assign_accents
        from .line_splitter import split_long_lines
        from .text_render import TextRenderer
        from .timing import ms_to_frames
        from .utils import detect_fps, video_dimensions

        fps = detect_fps(video)
        if fps is None:
            raise RuntimeError("Could not detect FPS of input video")

        dims = video_dimensions(video)
        if dims is None:
            raise RuntimeError("Could not determine video dimensions")

        captions = parse_srt(srt)
        captions = split_long_lines(captions)
        rng = random.Random(seed)
        assign_accents(
            captions,
            accents_count=len(self.cfg["colors"]["accents"]),
            starting_index=self.cfg["colors"].get("startingAccentIndex", 0),
            rng=rng,
        )

        renderer = TextRenderer(self.cfg)

        # ensure output directory exists and doesn't collide with existing dir of same name
        if out.exists() and out.is_dir():
            import shutil
            shutil.rmtree(out)

        out.parent.mkdir(parents=True, exist_ok=True)

        png_dir = out.parent / "caption_pngs"
        png_dir.mkdir(parents=True, exist_ok=True)

        # write caption PNGs -------------------------------------------------
        safe_margin = self.cfg["render"].get("safeMargin", 0)

        for cap in captions:
            accent_color = self.cfg["colors"]["accents"][cap.accent_index]
            img_full = renderer.render_caption(cap, accent_color, dims)

            # Trim bbox and pad safe margin
            bbox = img_full.getbbox()
            if bbox is None:
                continue
            img = img_full.crop(bbox)
            if safe_margin:
                w, h = img.size
                padded = Image.new("RGBA", (w + safe_margin * 2, h + safe_margin * 2), (0, 0, 0, 0))
                padded.alpha_composite(img, (safe_margin, safe_margin))
                img = padded

            img_path = png_dir / f"cap_{cap.index:04d}.png"
            img.save(img_path)

            frame_info = ms_to_frames(cap.start_ms, cap.end_ms, fps)
            start_ts = frame_info.in_frame / fps
            end_ts = frame_info.out_frame / fps

            # build per-frame symlink sequence -----------------------------------
            from .frame_seq import build_frame_sequence

            # cleanup any prior sequence dir if exists
            seq_dir = out.parent / "caption_frame_seq"
            if seq_dir.exists():
                import shutil
                shutil.rmtree(seq_dir)
            build_frame_sequence(captions, fps, dims, png_dir, seq_dir)

            # encode alpha track --------------------------------------------------
            alpha_mov = out.parent / "caption_track.mov"
            cmd_alpha = [
                "ffmpeg",
                "-y",
                "-framerate",
                f"{fps}",
                "-start_number",
                "0",
                "-i",
                str(seq_dir / "%06d.png"),
                "-c:v",
                "qtrle",
                "-pix_fmt",
                "argb",
                str(alpha_mov),
            ]
            subprocess.run(cmd_alpha, check=True)

            # final composite -----------------------------------------------------
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(video),
                "-i",
                str(alpha_mov),
                "-filter_complex",
                "[0:v][1:v]overlay[v]",
                "-map",
                "[v]",
                "-map",
                "0:a?",
                "-c:v",
                "libx265",
                "-b:v",
                "25M",
                "-preset",
                "medium",
                "-tag:v",
                "hvc1",
                "-pix_fmt",
                "yuv420p",
                "-threads",
                "4",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(out),
            ]

            subprocess.run(cmd, check=True)

    def _render_images_xml(self, video: Path, srt: Path, out_dir: Path, track_index: int, seed: int | None, show_progress: bool):
        from tempfile import TemporaryDirectory
        import csv
        import random
        from .parser import parse_srt, assign_accents
        from .line_splitter import split_long_lines
        from .text_render import TextRenderer
        from .timing import ms_to_frames
        from .utils import detect_fps, video_dimensions
        from .fcpxml import write_fcpxml
        from PIL import Image

        out_dir.mkdir(parents=True, exist_ok=True)

        fps = detect_fps(video) or 30.0
        dims = video_dimensions(video) or (1920, 1080)

        captions = parse_srt(srt)
        captions = split_long_lines(captions)
        rng = random.Random(seed)
        assign_accents(
            captions,
            accents_count=len(self.cfg["colors"]["accents"]),
            starting_index=self.cfg["colors"].get("startingAccentIndex", 0),
            rng=rng,
        )

        renderer = TextRenderer(self.cfg)

        items_for_xml = []
        manifest_path = out_dir / "captions_manifest.csv"
        with manifest_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                "index",
                "start_ms",
                "end_ms",
                "start_frame",
                "end_frame",
                "accent",
                "chosen_line",
                "words_colored",
                "filename",
            ])

            for cap in captions:
                accent_color = self.cfg["colors"]["accents"][cap.accent_index]
                img = renderer.render_caption(cap, accent_color, dims)

                # Trim transparency, then add safeMargin
                bbox = img.getbbox()
                if bbox:
                    img = img.crop(bbox)
                pad = self.cfg["render"].get("safeMargin", 0)
                if pad:
                    w, h = img.size
                    padded = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))  # type: ignore
                    padded.alpha_composite(img, (pad, pad))
                    img = padded

                png_name = f"cap_{cap.index:04d}.png"
                img_path = out_dir / png_name
                img.save(img_path)

                frame_info = ms_to_frames(cap.start_ms, cap.end_ms, fps)

                items_for_xml.append(
                    {
                        "file": png_name,
                        "start_frame": frame_info.in_frame,
                        "end_frame": frame_info.out_frame,
                        "offset_x": self.cfg["position"].get("offsetX", 0),
                        "offset_y": self.cfg["position"].get("offsetY", 0),
                    }
                )

                writer.writerow([
                    cap.index,
                    cap.start_ms,
                    cap.end_ms,
                    frame_info.in_frame,
                    frame_info.out_frame,
                    cap.accent_index,
                    cap.chosen_line,
                    cap.words_colored,
                    png_name,
                ])

        xml_path = out_dir / "captions.fcpxml"
        write_fcpxml(items_for_xml, fps, xml_path, track_index)
        self.logger.info("Images + FCPXML written to %s", out_dir)

    def _export_pngs(self, video: Path, srt: Path, out_dir: Path, seed: int | None, show_progress: bool):
        from .parser import parse_srt, assign_accents
        from .line_splitter import split_long_lines
        from .text_render import TextRenderer
        from .utils import video_dimensions, detect_fps
        from .xmeml import write_xmeml
        from .timing import ms_to_frames
        import random

        dims = video_dimensions(video) or (1920, 1080)
        fps_num, fps_den = detect_fps(video) or (30, 1)

        out_dir.mkdir(parents=True, exist_ok=True)

        captions = parse_srt(srt)
        captions = split_long_lines(captions)
        rng = random.Random(seed)
        assign_accents(captions, len(self.cfg["colors"]["accents"]), self.cfg["colors"].get("startingAccentIndex", 0), rng)

        renderer = TextRenderer(self.cfg)
        safe_margin = self.cfg["render"].get("safeMargin", 0)

        items_for_xml = []
        current_frame = 0
        for cap in captions:
            accent_color = self.cfg["colors"]["accents"][cap.accent_index]
            img = renderer.render_caption(cap, accent_color, dims)
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)
            if safe_margin:
                # Extra descender pad
                stroke_w = self.cfg["stroke"].get("width", 0)
                blur = self.cfg["shadow"].get("blur", 0)
                extra_pad = stroke_w + blur + 4

                w, h = img.size
                from PIL import Image

                padded = Image.new(
                    "RGBA",
                    (w + safe_margin * 2, h + safe_margin * 2 + extra_pad),
                    (0, 0, 0, 0),
                )
                padded.alpha_composite(img, (safe_margin, safe_margin))
                img = padded

            file_name = f"cap_{cap.index:04d}.png"
            img.save(out_dir / file_name)

            frame_info = ms_to_frames(cap.start_ms, cap.end_ms, fps_num, fps_den)
            duration = frame_info.duration_frames

            items_for_xml.append(
                {
                    "file": file_name,
                    "start_frame": current_frame,
                    "end_frame": current_frame + duration,
                }
            )
            current_frame += duration

        xml_path = out_dir / "captions.xml"
        write_xmeml(items_for_xml, fps_num, fps_den, xml_path, out_dir, dims)
        self.logger.info("Exported %d caption PNGs and captions.xml to %s", len(captions), out_dir)
