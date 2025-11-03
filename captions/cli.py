import sys
import click
from pathlib import Path
import logging

from .config import ensure_config_exists, load_config
from .utils import which_ffmpeg, detect_fps, setup_logger
from .renderer import CaptionRenderer


@click.group()
def cli():
    """CaptionScript – stylish caption rendering CLI."""


@cli.command("init-config")
@click.option("--overwrite", is_flag=True, help="Overwrite existing config if present.")
def init_config(overwrite):
    """(Re)write a template YAML config at the fixed path and print its location."""
    path = ensure_config_exists(overwrite=overwrite)
    click.echo(f"Config written to: {path}")


@cli.command("verify")
def verify():
    """Run environment checks and print a short report."""
    ok = True
    if which_ffmpeg():
        click.secho("ffmpeg/ffprobe: OK", fg="green")
    else:
        click.secho("ffmpeg/ffprobe: NOT FOUND on PATH", fg="red")
        ok = False

    cfg_path = ensure_config_exists()
    click.echo(f"Config path: {cfg_path}")

    cfg = load_config()
    required_font = cfg["text"]["fontFamily"]

    from .text_render import TextRenderer
    try:
        _ = TextRenderer._find_font_path(required_font)
        if _:
            click.secho(f"Font '{required_font}': FOUND", fg="green")
        else:
            click.secho(f"Font '{required_font}': NOT FOUND", fg="red")
            ok = False
    except Exception as e:
        click.secho(f"Font check error: {e}", fg="red")
        ok = False

    # basic key validation
    required_sections = ["text", "colors", "stroke", "shadow", "position"]
    missing = [s for s in required_sections if s not in cfg]
    if missing:
        click.secho(f"Missing config sections: {', '.join(missing)}", fg="red")
        ok = False
    else:
        click.secho("Config basic structure: OK", fg="green")

    sys.exit(0 if ok else 1)


def _get_unique_dir(path: Path) -> Path:
    """If path exists, find a unique alternative by suffixing with _1, _2, etc."""
    if not path.exists():
        return path
    
    i = 1
    while True:
        new_name = f"{path.name}_{i}"
        new_path = path.with_name(new_name)
        if not new_path.exists():
            return new_path
        i += 1


@cli.command("render")
@click.option("--video", "video_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--srt", "srt_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--mode", type=click.Choice(["video", "images-xml"], case_sensitive=False), required=True)
@click.option("--out", "out_path", required=True, type=click.Path(path_type=Path))
@click.option("--track-index", default=None, type=int, help="Timeline track index for images-xml mode.")
@click.option("--seed", default=None, type=int)
@click.option("--progress", is_flag=True, help="Show progress bar.")
def render_cmd(video_path: Path, srt_path: Path, mode: str, out_path: Path, track_index: int | None, seed: int | None, progress: bool):
    """Render captions according to the fixed config (no style overrides)."""
    final_out_path = out_path
    if mode == "images-xml":
        final_out_path = _get_unique_dir(out_path)

    cfg = load_config()

    log_path = (final_out_path.parent if final_out_path.suffix else final_out_path) / "captions.log"
    setup_logger(log_path)

    fps = detect_fps(video_path)
    if fps is None:
        logging.error("Could not detect FPS of input video via ffprobe.")
        sys.exit(1)
    logging.info("Detected FPS: %s", fps)

    renderer = CaptionRenderer(cfg)
    renderer.render(mode.lower(), video_path, srt_path, final_out_path, track_index or cfg["output"].get("trackIndex", 2), seed, progress)


# lightweight export command
@cli.command("export-pngs")
@click.option("--video", "video_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--srt", "srt_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--out", "out_dir", required=True, type=click.Path(path_type=Path))
@click.option("--seed", default=None, type=int)
def export_pngs_cmd(video_path: Path, srt_path: Path, out_dir: Path, seed: int | None):
    """Export each subtitle block as trimmed PNG + timestamps.txt"""
    final_out_dir = _get_unique_dir(out_dir)
    cfg = load_config()
    renderer = CaptionRenderer(cfg)
    renderer.render("export", video_path, srt_path, final_out_dir, 0, seed, False)


if __name__ == "__main__":
    cli()
