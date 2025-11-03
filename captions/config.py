import os
import platform
from pathlib import Path
import yaml

DEFAULT_CONFIG_YAML = """# CaptionScript default configuration\ntext:\n  fontFamily: "Inter"\n  size: 78\n  weight: 700\n  letterSpacing: 0\n  alignment: "center"      # left|center|right\n  capitalization: "as-is"  # as-is|upper|lower|title\n  lineHeight: null\ncolors:\n  base: "#FFFFFF"\n  accents: ["#FF4D4D", "#FFD24D", "#4DFF88", "#4DB8FF"]\n  startingAccentIndex: 0   # 0-based\nstroke:\n  color: "#000000"\n  width: 6\nshadow:\n  x: 2\n  y: 2\n  color: "#000000"\n  opacity: 60\n  spread: 2\n  blur: 8\nposition:\n  offsetX: 0\n  offsetY: -120\nrender:\n  safeMargin: 16\n  video:\n    codecPreset: "copy"\noutput:\n  trackIndex: 2\n"""


def _platform_config_path() -> Path:
    """Return the platform-specific absolute path to the YAML config file."""
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
        return base / "Captions" / "config.yaml"
    else:
        return Path.home() / ".captions" / "config.yaml"


def ensure_config_exists(overwrite: bool = False) -> Path:
    """Create the config file with defaults if it does not exist (or overwrite if requested)."""
    cfg_path = _platform_config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    if overwrite or not cfg_path.exists():
        cfg_path.write_text(DEFAULT_CONFIG_YAML, encoding="utf-8")
    return cfg_path


def load_config() -> dict:
    """Load and return the user config as a dict, ensuring it exists first."""
    cfg_path = ensure_config_exists()
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)
