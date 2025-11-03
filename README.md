# CaptionScript CLI

A standalone Python tool to burn stylized captions onto video or generate transparent PNGs with a Premiere-importable timeline.

## Features
* Fixed per-user YAML config ‑ edit once, reuse forever.
* Two render modes:
  * **video** – outputs a new video with baked-in captions.
  * **images-xml** – exports trimmed PNGs + FCPXML 1.6 for Premiere.
* Deterministic color accent cycling & seeded randomness for reproducibility.
* Progress bar, detailed logfile, pre-flight verification.

## Quick Start
```bash
# 1. create and activate virtualenv (Python ≥3.10)
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. install requirements
pip install -r requirements.txt

# 3. first-run – create a template config then edit it
ypython -m captions init-config  # prints the config path
$EDITOR ~/.captions/config.yaml   # or %APPDATA%\Captions\config.yaml on Windows

# 4. render!
python -m captions render \
  --video /path/video.mov \
  --srt /path/subs.srt \
  --mode video \
  --out /path/output_with_captions.mov \
  --progress
```

## CLI Overview
```
captions render --video FILE --srt FILE --mode {video,images-xml} --out PATH [--track-index N] [--seed INT] [--progress]
captions init-config   # writes/overwrites template config at the fixed path
captions verify        # checks ffmpeg, font, config validity; prints a report
```

Install `ffmpeg`/`ffprobe` and ensure they are on your `PATH`.

## Development
* All source lives in the `captions` package.
* Run tests with `pytest` (not yet included).

## License
MIT
