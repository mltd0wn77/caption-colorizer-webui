"""
Simple Web Application for Caption Colorizer
Minimal FastAPI implementation for hosting the caption processing service
"""

from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import tempfile
import shutil
import uuid
import zipfile
import asyncio
from datetime import datetime, timedelta
import os

# Import your existing caption processing code
from captions.config import load_config
from captions.renderer import CaptionRenderer
from captions.utils import detect_fps

app = FastAPI(title="Caption Colorizer")

# Enable CORS for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store processed files temporarily (clean up after 1 hour)
UPLOAD_DIR = Path("./uploads")
OUTPUT_DIR = Path("./outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

def cleanup_old_files():
    """Remove files older than 1 hour"""
    cutoff = datetime.now() - timedelta(hours=1)
    for dir_path in [UPLOAD_DIR, OUTPUT_DIR]:
        for file_path in dir_path.glob("*"):
            if file_path.stat().st_mtime < cutoff.timestamp():
                if file_path.is_dir():
                    shutil.rmtree(file_path)
                else:
                    file_path.unlink()

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve a simple upload form"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Caption Colorizer</title>
        <style>
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .container {
                background: white;
                border-radius: 12px;
                padding: 40px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
            }
            .subtitle {
                color: #666;
                margin-bottom: 30px;
            }
            .upload-form {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }
            .file-input-wrapper {
                position: relative;
                overflow: hidden;
                display: inline-block;
                cursor: pointer;
                background: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                transition: all 0.3s;
            }
            .file-input-wrapper:hover {
                border-color: #667eea;
                background: #f0f3ff;
            }
            .file-input-wrapper input[type=file] {
                position: absolute;
                left: -9999px;
            }
            .file-label {
                font-weight: 600;
                color: #495057;
                margin-bottom: 5px;
            }
            .file-info {
                font-size: 14px;
                color: #6c757d;
            }
            .selected-file {
                color: #28a745;
                font-weight: 500;
                margin-top: 5px;
            }
            button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }
            button:hover:not(:disabled) {
                transform: translateY(-2px);
            }
            button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            #status {
                margin-top: 20px;
                padding: 15px;
                border-radius: 6px;
                display: none;
            }
            .success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .loading {
                background: #cce5ff;
                color: #004085;
                border: 1px solid #b8daff;
            }
            .spinner {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid #f3f3f3;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-right: 10px;
                vertical-align: middle;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .download-link {
                display: inline-block;
                margin-top: 10px;
                color: #667eea;
                font-weight: 600;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎨 Caption Colorizer</h1>
            <p class="subtitle">Upload your video and SRT file to generate beautifully colored captions</p>
            
            <form id="uploadForm" class="upload-form">
                <div class="file-input-wrapper">
                    <div class="file-label">📹 Video File</div>
                    <div class="file-info">MP4, MOV, or AVI</div>
                    <input type="file" id="video" name="video" accept="video/*" required>
                    <div id="videoName" class="selected-file"></div>
                </div>
                
                <div class="file-input-wrapper">
                    <div class="file-label">📝 Subtitle File</div>
                    <div class="file-info">SRT format</div>
                    <input type="file" id="srt" name="srt" accept=".srt" required>
                    <div id="srtName" class="selected-file"></div>
                </div>
                
                <button type="submit">Generate Colored Captions</button>
            </form>
            
            <div id="status"></div>
        </div>
        
        <script>
            // Show selected file names
            document.getElementById('video').addEventListener('change', function(e) {
                const fileName = e.target.files[0]?.name || '';
                document.getElementById('videoName').textContent = fileName ? '✓ ' + fileName : '';
            });
            
            document.getElementById('srt').addEventListener('change', function(e) {
                const fileName = e.target.files[0]?.name || '';
                document.getElementById('srtName').textContent = fileName ? '✓ ' + fileName : '';
            });
            
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const formData = new FormData();
                formData.append('video', document.getElementById('video').files[0]);
                formData.append('srt', document.getElementById('srt').files[0]);
                
                const status = document.getElementById('status');
                const submitBtn = e.target.querySelector('button');
                
                status.innerHTML = '<div class="spinner"></div> Processing your files... This may take a minute.';
                status.className = 'loading';
                status.style.display = 'block';
                submitBtn.disabled = true;
                
                try {
                    const response = await fetch('/process', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'colored_captions.zip';
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        
                        status.innerHTML = '✅ Success! Your download should start automatically.';
                        status.className = 'success';
                    } else {
                        throw new Error('Processing failed');
                    }
                } catch (error) {
                    status.innerHTML = '❌ Error: ' + error.message;
                    status.className = 'error';
                } finally {
                    submitBtn.disabled = false;
                }
            });
        </script>
    </body>
    </html>
    """

@app.post("/process")
async def process_captions(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    srt: UploadFile = File(...)
):
    """Process video and SRT to generate colored captions"""
    
    # Clean up old files
    background_tasks.add_task(cleanup_old_files)
    
    # Create unique session ID
    session_id = str(uuid.uuid4())
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    
    # Save uploaded files
    video_path = session_dir / video.filename
    srt_path = session_dir / srt.filename
    
    with open(video_path, "wb") as f:
        content = await video.read()
        f.write(content)
    
    with open(srt_path, "wb") as f:
        content = await srt.read()
        f.write(content)
    
    # Process using existing code
    output_dir = OUTPUT_DIR / session_id
    output_dir.mkdir(exist_ok=True)
    
    try:
        # Load config and create renderer
        cfg = load_config()
        renderer = CaptionRenderer(cfg)
        
        # Generate colored caption PNGs and XML
        renderer.render(
            mode="images-xml",
            video=video_path,
            srt=srt_path,
            out=output_dir / "captions",
            track_index=2,
            seed=None,
            show_progress=False
        )
        
        # Create ZIP archive
        zip_path = OUTPUT_DIR / f"{session_id}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            caption_dir = output_dir / "captions"
            for file_path in caption_dir.glob("*"):
                zipf.write(file_path, file_path.name)
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_session, session_id)
        
        return FileResponse(
            path=zip_path,
            filename="colored_captions.zip",
            media_type="application/zip"
        )
        
    except Exception as e:
        # Clean up on error
        if session_dir.exists():
            shutil.rmtree(session_dir)
        if output_dir.exists():
            shutil.rmtree(output_dir)
        raise e

async def cleanup_session(session_id: str):
    """Clean up session files after delay"""
    await asyncio.sleep(300)  # Wait 5 minutes
    
    session_upload = UPLOAD_DIR / session_id
    session_output = OUTPUT_DIR / session_id
    zip_file = OUTPUT_DIR / f"{session_id}.zip"
    
    if session_upload.exists():
        shutil.rmtree(session_upload)
    if session_output.exists():
        shutil.rmtree(session_output)
    if zip_file.exists():
        zip_file.unlink()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
