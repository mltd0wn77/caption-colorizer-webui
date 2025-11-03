from __future__ import annotations

from pathlib import Path
from typing import Tuple, List
import logging
import math
import os

from .parser import Caption

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:  # pragma: no cover
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    ImageFont = None  # type: ignore
    ImageFilter = None  # type: ignore

_LOGGER = logging.getLogger(__name__)


class PillowNotAvailable(RuntimeError):
    """Raised when Pillow is required but not installed."""


class TextRenderer:
    """Render `Caption` objects to RGBA `PIL.Image`s according to config.

    This implementation prioritizes matching the project spec rather than pixel-perfect typography.
    """

    def __init__(self, cfg: dict):
        if Image is None:
            raise PillowNotAvailable("Pillow library is not installed; text rendering cannot proceed.")

        self.cfg = cfg
        self.font_cache: dict[Tuple[str, int, int], ImageFont.FreeTypeFont] = {}

        text_cfg = cfg["text"]
        self.base_font_path = self._find_font_path(text_cfg["fontFamily"])
        if not self.base_font_path:
            _LOGGER.warning("Font '%s' not found. Falling back to default Pillow font.", text_cfg["fontFamily"])
            self.base_font_path = None  # indicates to use default font
        
        self.font_size = text_cfg["size"]
        self.font_weight = text_cfg["weight"]

    # --------------------------------------------------------------------- #
    @staticmethod
    def _find_font_path(font_family: str) -> str | None:
        """Very naive font lookup across common system directories."""
        lookup_dirs = [
            "/System/Library/Fonts",
            "/Library/Fonts",
            os.path.expanduser("~/Library/Fonts"),
            "/usr/share/fonts",
            "/usr/local/share/fonts",
        ]
        for d in lookup_dirs:
            if not os.path.isdir(d):
                continue
            for root, _dirs, files in os.walk(d):
                for f in files:
                    if f.lower().startswith(font_family.lower().replace(" ", "")) and f.lower().endswith((".ttf", ".otf")):
                        return os.path.join(root, f)
        return None

    # ------------------------------------------------------------------ #
    def _get_font(self, size: int, weight: int) -> ImageFont.FreeTypeFont:  # noqa: D401
        if self.base_font_path is None:
            return ImageFont.load_default()

        key = (self.base_font_path, size, weight)
        if key in self.font_cache:
            return self.font_cache[key]
        font = ImageFont.truetype(self.base_font_path, size=size)
        self.font_cache[key] = font
        return font

    # ------------------------------------------------------------------ #
    def render_caption(self, cap: Caption, accent_color: str, canvas_size: Tuple[int, int]) -> Image.Image:  # type: ignore
        """Render a single caption block and return an RGBA image the same size as video frame.

        Returns an image with transparent background; caller handles compositing.
        """
        text_cfg = self.cfg["text"]
        stroke_cfg = self.cfg["stroke"]
        shadow_cfg = self.cfg["shadow"]
        pos_cfg = self.cfg["position"]

        is_4k = canvas_size[0] >= 3840
        font_size = self.font_size * 2 if is_4k else self.font_size

        capitalization = text_cfg.get("capitalization", "none").lower()

        def apply_capitalization(text: str) -> str:
            if capitalization == "upper":
                return text.upper()
            return text

        # Build text lines with accent decisions
        rendered_lines: List[Tuple[str, List[Tuple[str, str]]]] = []
        if len(cap.lines) == 2:
            for i, line in enumerate(cap.lines):
                line = apply_capitalization(line)
                color = accent_color if i == cap.chosen_line else self.cfg["colors"]["base"]
                rendered_lines.append((line, [(line, color)]))
        else:
            line = apply_capitalization(cap.lines[0])
            words = line.split()
            base_color = self.cfg["colors"]["base"]
            accent_words = words[-cap.words_colored :] if cap.words_colored else []
            color_runs: List[Tuple[str, str]] = []
            for w in words:
                color_runs.append((w, accent_color if w in accent_words else base_color))
            rendered_lines.append((cap.lines[0], color_runs))

        # Create temporary surface just big enough
        # measure text width/height with letter spacing manually
        spacing = text_cfg.get("letterSpacing", 0)
        font = self._get_font(font_size, self.font_weight)
        img_tmp = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img_tmp)

        total_height = 0
        line_metrics: List[Tuple[int, int]] = []
        ascent, descent = font.getmetrics()
        line_height = (
            text_cfg.get("lineHeight")
            if text_cfg.get("lineHeight")
            else ascent + descent + 10  # simple default leading
        )
        for _line, _runs in rendered_lines:
            line_height_px = line_height
            total_height += line_height_px
            line_metrics.append((line_height_px, ascent))

        y_start = canvas_size[1] + pos_cfg["offsetY"] - total_height

        for idx, (_line, runs) in enumerate(rendered_lines):
            line_height_px, ascent_px = line_metrics[idx]
            x_cursor = 0  # we'll center later
            run_imgs: List[Image.Image] = []
            for token, color in runs:
                t_img = self._render_token(token, font, color, stroke_cfg)
                run_imgs.append(t_img)
            # compute line width
            line_width = sum(img.width for img in run_imgs) + spacing * (len(run_imgs) - 1)
            x_start = (canvas_size[0] - line_width) // 2 + pos_cfg["offsetX"]
            y = y_start + idx * line_height_px
            for t_img in run_imgs:
                img_tmp.alpha_composite(t_img, (x_start + x_cursor, y))
                x_cursor += t_img.width + spacing

        # Shadow pass: blur entire alpha + offset
        if shadow_cfg["opacity"]:
            shadow_img = img_tmp.copy()
            shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=shadow_cfg["blur"]))
            # multiply alpha by opacity
            alpha = shadow_img.getchannel("A")
            alpha = alpha.point(lambda p: p * (shadow_cfg["opacity"] / 100))
            shadow_img.putalpha(alpha)
            result = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
            result.alpha_composite(shadow_img, (shadow_cfg["x"], shadow_cfg["y"]))
            result.alpha_composite(img_tmp)
            return result
        return img_tmp

    # ------------------------------------------------------------------ #
    def _render_token(self, text: str, font: ImageFont.FreeTypeFont, fill_color: str, stroke_cfg: dict) -> Image.Image:
        """Render a single word with stroke using two-pass approach."""
        ascent, descent = font.getmetrics()
        h = ascent + descent
        bbox = font.getbbox(text)
        w = bbox[2] - bbox[0]

        stroke_width = stroke_cfg["width"]
        canvas = Image.new("RGBA", (w + stroke_width * 2, h + stroke_width * 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        # Left of text should be at `stroke_width`. `bbox[0]` is text's left offset.
        x = stroke_width - bbox[0]
        # Baseline should be at `ascent + stroke_width`.
        y = ascent + stroke_width

        if stroke_width > 0:
            # stroke pass
            for dx in range(-stroke_width, stroke_width + 1):
                for dy in range(-stroke_width, stroke_width + 1):
                    draw.text((x + dx, y + dy), text, font=font, fill=stroke_cfg["color"], anchor="ls")
        # fill
        draw.text((x, y), text, font=font, fill=fill_color, anchor="ls")
        return canvas
