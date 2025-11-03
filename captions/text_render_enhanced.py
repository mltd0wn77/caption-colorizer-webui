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

    This enhanced implementation fixes font selection and color rendering issues.
    """

    def __init__(self, cfg: dict):
        if Image is None:
            raise PillowNotAvailable("Pillow library is not installed; text rendering cannot proceed.")

        self.cfg = cfg
        self.font_cache: dict[Tuple[str, int, int], ImageFont.FreeTypeFont] = {}

        text_cfg = cfg["text"]
        
        # Check for custom font path first (from webapp)
        if "_custom_font_path" in text_cfg:
            self.base_font_path = text_cfg["_custom_font_path"]
            _LOGGER.info("Using custom uploaded font: %s", self.base_font_path)
        else:
            self.base_font_path = self._find_font_path(text_cfg["fontFamily"])
            if not self.base_font_path:
                _LOGGER.warning("Font '%s' not found. Falling back to default Pillow font.", text_cfg["fontFamily"])
                self.base_font_path = None  # indicates to use default font
        
        self.font_size = text_cfg["size"]
        self.font_weight = text_cfg["weight"]

    # --------------------------------------------------------------------- #
    @staticmethod
    def _find_font_path(font_family: str) -> str | None:
        """Improved font lookup that prioritizes regular/bold variants over italic."""
        lookup_dirs = [
            "/System/Library/Fonts",
            "/Library/Fonts",
            os.path.expanduser("~/Library/Fonts"),
            "/usr/share/fonts",
            "/usr/local/share/fonts",
        ]
        
        # Priority list for font file matching
        # We want to avoid italic variants
        preferred_suffixes = [
            "-bold.ttf", "-bold.otf",
            "-regular.ttf", "-regular.otf",
            "-medium.ttf", "-medium.otf",
            "bold.ttf", "bold.otf",
            "regular.ttf", "regular.otf",
            ".ttf", ".otf"
        ]
        
        # Avoid these patterns
        avoid_patterns = ["italic", "oblique", "light", "thin", "condensed"]
        
        candidates = []
        
        for d in lookup_dirs:
            if not os.path.isdir(d):
                continue
            for root, _dirs, files in os.walk(d):
                for f in files:
                    f_lower = f.lower()
                    
                    # Skip if it contains avoided patterns
                    if any(pattern in f_lower for pattern in avoid_patterns):
                        continue
                    
                    # Check if it matches the font family
                    if font_family.lower().replace(" ", "") in f_lower.replace(" ", "").replace("-", ""):
                        full_path = os.path.join(root, f)
                        candidates.append((full_path, f_lower))
        
        # Sort candidates by preferred suffix priority
        for suffix in preferred_suffixes:
            for path, name in candidates:
                if name.endswith(suffix):
                    _LOGGER.info("Selected font: %s", path)
                    return path
        
        # Return first candidate if no preferred suffix found
        if candidates:
            _LOGGER.info("Selected font (fallback): %s", candidates[0][0])
            return candidates[0][0]
        
        return None

    # ------------------------------------------------------------------ #
    def _get_font(self, size: int, weight: int) -> ImageFont.FreeTypeFont:
        """Get font with proper weight handling."""
        if self.base_font_path is None:
            return ImageFont.load_default()

        key = (self.base_font_path, size, weight)
        if key in self.font_cache:
            return self.font_cache[key]
        
        try:
            # Try to load with specific variations for better weight control
            font = ImageFont.truetype(self.base_font_path, size=size)
            
            # Some fonts support variable weight through set_variation_by_name
            if hasattr(font, 'set_variation_by_name'):
                if weight >= 700:
                    try:
                        font.set_variation_by_name('Bold')
                    except:
                        pass
                elif weight >= 500:
                    try:
                        font.set_variation_by_name('Medium')
                    except:
                        pass
        except Exception as e:
            _LOGGER.warning("Error loading font %s: %s. Using default.", self.base_font_path, e)
            font = ImageFont.load_default()
        
        self.font_cache[key] = font
        return font

    # ------------------------------------------------------------------ #
    def render_caption(self, cap: Caption, accent_color: str, canvas_size: Tuple[int, int]) -> Image.Image:  # type: ignore
        """Render a single caption block with enhanced color accuracy.

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
            elif capitalization == "lower":
                return text.lower()
            elif capitalization == "title":
                return text.title()
            return text

        # Ensure proper color format (remove alpha if present, ensure full hex)
        def normalize_color(color: str) -> str:
            """Normalize color to #RRGGBB format."""
            if color.startswith("#"):
                # Remove alpha channel if present
                color = color[:7]
                # Ensure 6 digits
                if len(color) == 4:  # #RGB -> #RRGGBB
                    color = "#" + "".join([c*2 for c in color[1:]])
            return color.upper()

        accent_color = normalize_color(accent_color)
        base_color = normalize_color(self.cfg["colors"]["base"])

        # Build text lines with accent decisions
        rendered_lines: List[Tuple[str, List[Tuple[str, str]]]] = []
        if len(cap.lines) == 2:
            for i, line in enumerate(cap.lines):
                line = apply_capitalization(line)
                color = accent_color if i == cap.chosen_line else base_color
                rendered_lines.append((line, [(line, color)]))
        else:
            line = apply_capitalization(cap.lines[0])
            words = line.split()
            accent_words = words[-cap.words_colored :] if cap.words_colored else []
            color_runs: List[Tuple[str, str]] = []
            for w in words:
                color_runs.append((w, accent_color if w in accent_words else base_color))
            rendered_lines.append((line, color_runs))

        # Create image with proper alpha channel
        img_tmp = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img_tmp)

        # Get font with proper weight (force bold for better visibility)
        effective_weight = max(self.font_weight, 700)  # Ensure at least bold
        font = self._get_font(font_size, effective_weight)
        
        # Calculate text positioning
        spacing = text_cfg.get("letterSpacing", 0)
        total_height = 0
        line_metrics: List[Tuple[int, int]] = []
        
        try:
            ascent, descent = font.getmetrics()
        except:
            # Fallback for fonts without metrics
            bbox = draw.textbbox((0, 0), "Ay", font=font)
            ascent = abs(bbox[1])
            descent = bbox[3] - bbox[1]
        
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

        # Render each line
        for idx, (_line, runs) in enumerate(rendered_lines):
            line_height_px, ascent_px = line_metrics[idx]
            x_cursor = 0  # we'll center later
            run_imgs: List[Image.Image] = []
            
            for token, color in runs:
                # Ensure color is properly formatted
                color = normalize_color(color)
                t_img = self._render_token(token, font, color, stroke_cfg)
                run_imgs.append(t_img)
            
            # compute line width
            line_width = sum(img.width for img in run_imgs) + spacing * (len(run_imgs) - 1)
            x_start = (canvas_size[0] - line_width) // 2 + pos_cfg["offsetX"]
            
            # composite tokens
            for t_img in run_imgs:
                img_tmp.alpha_composite(t_img, (x_start + x_cursor, y_start))
                x_cursor += t_img.width + spacing
            
            y_start += line_height_px

        # Apply shadow if configured
        if shadow_cfg.get("enabled", False):
            shadow_img = img_tmp.copy()
            shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=shadow_cfg.get("blur", 5)))
            
            # Create shadow layer with proper alpha
            shadow_layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
            shadow_layer.alpha_composite(
                shadow_img,
                (shadow_cfg.get("offsetX", 0), shadow_cfg.get("offsetY", 0))
            )
            
            # Composite shadow under main text
            final_img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
            final_img.alpha_composite(shadow_layer)
            final_img.alpha_composite(img_tmp)
            return final_img

        return img_tmp

    def _render_token(
        self,
        token: str,
        font: ImageFont.FreeTypeFont,
        color: str,
        stroke_cfg: dict
    ) -> Image.Image:  # type: ignore
        """Render a single word/token with stroke."""
        # Normalize color
        color = color[:7] if color.startswith("#") else color
        
        # Get text bbox
        tmp_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        tmp_draw = ImageDraw.Draw(tmp_img)
        bbox = tmp_draw.textbbox((0, 0), token, font=font, stroke_width=stroke_cfg.get("width", 0))
        
        width = bbox[2] - bbox[0] + 10  # padding
        height = bbox[3] - bbox[1] + 10
        
        # Create image for token
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Calculate position to center text in image
        x = -bbox[0] + 5
        y = -bbox[1] + 5
        
        # Draw text with stroke
        stroke_width = stroke_cfg.get("width", 0)
        stroke_color = stroke_cfg.get("color", "#000000")[:7]
        
        try:
            # Use native stroke support if available
            draw.text(
                (x, y),
                token,
                font=font,
                fill=color,
                stroke_width=stroke_width,
                stroke_fill=stroke_color
            )
        except TypeError:
            # Fallback for older Pillow versions
            # Draw stroke manually
            if stroke_width > 0:
                for adj_x in range(-stroke_width, stroke_width + 1):
                    for adj_y in range(-stroke_width, stroke_width + 1):
                        if adj_x != 0 or adj_y != 0:
                            draw.text(
                                (x + adj_x, y + adj_y),
                                token,
                                font=font,
                                fill=stroke_color
                            )
            # Draw main text
            draw.text((x, y), token, font=font, fill=color)
        
        return img
