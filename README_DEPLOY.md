# Caption Colorizer - Web Deployment

This is a web-enabled version of the Caption Colorizer that can be easily deployed to cloud platforms.

## Quick Start (Local Testing)

```bash
# Install dependencies
pip install -r requirements-web.txt

# Initialize config
python -m captions init-config

# Run locally
python webapp_production.py

# Visit http://localhost:8000
```

## Easy Cloud Deployment

### Deploy to Render (Free Tier Available)

1. Push code to GitHub
2. Sign up at [render.com](https://render.com)
3. Create new "Web Service"
4. Connect your GitHub repo
5. Deploy! (auto-configures from `render.yaml`)

**Your app will be live at:** `https://your-app.onrender.com`

See [EASY_DEPLOY.md](./EASY_DEPLOY.md) for detailed step-by-step instructions.

## Features

- 🎨 Smart color cycling for captions
- 📹 Direct Premiere Pro integration
- ⚡ Fast processing
- 🌐 Web-based interface
- 📦 ZIP download of results
- 🆓 Free tier hosting available

## How It Works

1. **Upload** your video file (MP4, MOV, AVI)
2. **Upload** your SRT subtitle file
3. **Process** automatically applies coloring rules
4. **Download** ZIP containing:
   - Colored caption PNGs
   - Premiere Pro XML for easy import

## Color Rules

The system applies intelligent coloring:
- **4 accent colors** that cycle (never repeats consecutively)
- **Two-line captions**: Colors one complete line
- **Single-line captions**: Colors last half of words
- **Professional styling**: White text with black stroke/shadow

## File Structure

```
project/
├── captions/              # Core processing logic
├── webapp_production.py   # Web application
├── Dockerfile            # Container configuration
├── render.yaml           # Render deployment config
├── requirements-web.txt  # Python dependencies
└── EASY_DEPLOY.md       # Deployment guide
```

## System Requirements

- Python 3.11+
- FFmpeg (included in Docker image)
- 2GB RAM minimum
- 1GB storage for temporary files

## Support

For issues or questions:
- Check logs in your hosting dashboard
- Ensure video files are under 500MB
- Verify SRT file format is correct

## License

MIT
