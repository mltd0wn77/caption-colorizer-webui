"""
Production-ready Caption Colorizer Web Application
Optimized for deployment on Render, Railway, or similar platforms
"""

import os
import sys
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pathlib import Path
import tempfile
import shutil
import uuid
import zipfile
import asyncio
from datetime import datetime, timedelta
import logging

# Import your existing caption processing code
from captions.config import load_config
from captions.renderer import CaptionRenderer
from captions.utils import detect_fps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Caption Colorizer",
    description="Generate beautifully colored captions for your videos",
    version="1.0.0"
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure with your domain in production
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Configuration
STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", "/app/storage"))
UPLOAD_DIR = STORAGE_DIR / "uploads"
OUTPUT_DIR = STORAGE_DIR / "outputs"
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
CLEANUP_INTERVAL = 3600  # 1 hour
FILE_RETENTION = 3600  # 1 hour

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Background cleanup task
async def cleanup_old_files():
    """Remove files older than retention period"""
    while True:
        try:
            cutoff = datetime.now() - timedelta(seconds=FILE_RETENTION)
            cleaned = 0
            
            for dir_path in [UPLOAD_DIR, OUTPUT_DIR]:
                for item in dir_path.iterdir():
                    try:
                        if item.stat().st_mtime < cutoff.timestamp():
                            if item.is_dir():
                                shutil.rmtree(item)
                            else:
                                item.unlink()
                            cleaned += 1
                    except Exception as e:
                        logger.error(f"Error cleaning {item}: {e}")
            
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} old files/directories")
                
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")
        
        await asyncio.sleep(CLEANUP_INTERVAL)

# Start cleanup task on startup
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_old_files())
    logger.info("Caption Colorizer started successfully")

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the web interface"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Caption Colorizer - Beautiful Colored Captions for Your Videos</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            
            .container {
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.2);
                max-width: 600px;
                width: 100%;
                animation: slideUp 0.5s ease;
            }
            
            @keyframes slideUp {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .header {
                text-align: center;
                margin-bottom: 40px;
            }
            
            h1 {
                color: #2d3748;
                font-size: 32px;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }
            
            .subtitle {
                color: #718096;
                font-size: 16px;
                line-height: 1.5;
            }
            
            .features {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin: 30px 0;
                padding: 20px;
                background: #f7fafc;
                border-radius: 12px;
            }
            
            .feature {
                display: flex;
                align-items: center;
                gap: 8px;
                color: #4a5568;
                font-size: 14px;
            }
            
            .feature-icon {
                font-size: 18px;
            }
            
            .upload-form {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }
            
            .file-input-wrapper {
                position: relative;
                overflow: hidden;
                border: 2px dashed #cbd5e0;
                border-radius: 12px;
                padding: 25px;
                text-align: center;
                transition: all 0.3s;
                cursor: pointer;
                background: #f8f9fa;
            }
            
            .file-input-wrapper:hover {
                border-color: #667eea;
                background: #f0f3ff;
                transform: translateY(-2px);
            }
            
            .file-input-wrapper.has-file {
                border-color: #48bb78;
                background: #f0fff4;
            }
            
            .file-input-wrapper input[type=file] {
                position: absolute;
                left: -9999px;
            }
            
            .file-label {
                font-weight: 600;
                color: #2d3748;
                font-size: 16px;
                margin-bottom: 5px;
            }
            
            .file-info {
                font-size: 13px;
                color: #718096;
            }
            
            .selected-file {
                color: #48bb78;
                font-weight: 500;
                margin-top: 8px;
                font-size: 14px;
            }
            
            .submit-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 14px 30px;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }
            
            .submit-btn:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
            }
            
            .submit-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            
            #status {
                margin-top: 20px;
                padding: 15px;
                border-radius: 10px;
                display: none;
                animation: slideDown 0.3s ease;
            }
            
            @keyframes slideDown {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .status-success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            
            .status-error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            
            .status-loading {
                background: #cce5ff;
                color: #004085;
                border: 1px solid #b8daff;
            }
            
            .spinner {
                display: inline-block;
                width: 16px;
                height: 16px;
                border: 2px solid transparent;
                border-top-color: #667eea;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
                margin-right: 8px;
                vertical-align: middle;
            }
            
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            
            .progress-bar {
                width: 100%;
                height: 4px;
                background: #e2e8f0;
                border-radius: 2px;
                overflow: hidden;
                margin-top: 10px;
            }
            
            .progress-fill {
                height: 100%;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                animation: progress 2s ease-in-out infinite;
            }
            
            @keyframes progress {
                0% { width: 0%; }
                50% { width: 70%; }
                100% { width: 100%; }
            }
            
            @media (max-width: 640px) {
                .container {
                    padding: 30px 20px;
                }
                h1 {
                    font-size: 24px;
                }
                .features {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>
                    <span>🎨</span>
                    <span>Caption Colorizer</span>
                </h1>
                <p class="subtitle">Transform your subtitles into beautifully styled captions for Adobe Premiere Pro</p>
            </div>
            
            <div class="features">
                <div class="feature">
                    <span class="feature-icon">🎨</span>
                    <span>Smart color cycling</span>
                </div>
                <div class="feature">
                    <span class="feature-icon">📹</span>
                    <span>Premiere Pro ready</span>
                </div>
                <div class="feature">
                    <span class="feature-icon">⚡</span>
                    <span>Fast processing</span>
                </div>
                <div class="feature">
                    <span class="feature-icon">🎯</span>
                    <span>Professional quality</span>
                </div>
            </div>
            
            <form id="uploadForm" class="upload-form">
                <div class="file-input-wrapper" id="videoWrapper">
                    <div class="file-label">📹 Upload Video</div>
                    <div class="file-info">MP4, MOV, or AVI (max 500MB)</div>
                    <input type="file" id="video" name="video" accept="video/*" required>
                    <div id="videoName" class="selected-file"></div>
                </div>
                
                <div class="file-input-wrapper" id="srtWrapper">
                    <div class="file-label">📝 Upload Subtitles</div>
                    <div class="file-info">SRT format only</div>
                    <input type="file" id="srt" name="srt" accept=".srt" required>
                    <div id="srtName" class="selected-file"></div>
                </div>
                
                <button type="submit" class="submit-btn">
                    Generate Colored Captions
                </button>
            </form>
            
            <div id="status"></div>
        </div>
        
        <script>
            // File input handlers
            function setupFileInput(inputId, wrapperId, nameId) {
                const input = document.getElementById(inputId);
                const wrapper = document.getElementById(wrapperId);
                const nameDisplay = document.getElementById(nameId);
                
                wrapper.addEventListener('click', () => input.click());
                
                input.addEventListener('change', function(e) {
                    const file = e.target.files[0];
                    if (file) {
                        nameDisplay.textContent = `✓ ${file.name} (${(file.size / 1024 / 1024).toFixed(1)}MB)`;
                        wrapper.classList.add('has-file');
                    } else {
                        nameDisplay.textContent = '';
                        wrapper.classList.remove('has-file');
                    }
                });
            }
            
            setupFileInput('video', 'videoWrapper', 'videoName');
            setupFileInput('srt', 'srtWrapper', 'srtName');
            
            // Form submission
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const videoFile = document.getElementById('video').files[0];
                const srtFile = document.getElementById('srt').files[0];
                
                // Validate file sizes
                const maxSize = 500 * 1024 * 1024; // 500MB
                if (videoFile.size > maxSize) {
                    showStatus('error', `Video file too large (max 500MB, got ${(videoFile.size / 1024 / 1024).toFixed(1)}MB)`);
                    return;
                }
                
                const formData = new FormData();
                formData.append('video', videoFile);
                formData.append('srt', srtFile);
                
                const submitBtn = e.target.querySelector('.submit-btn');
                submitBtn.disabled = true;
                
                showStatus('loading', `
                    <span class="spinner"></span>
                    Processing your video... This may take a minute.
                    <div class="progress-bar"><div class="progress-fill"></div></div>
                `);
                
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
                        a.download = `colored_captions_${Date.now()}.zip`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        window.URL.revokeObjectURL(url);
                        
                        showStatus('success', '✅ Success! Your captions are ready and downloading now.');
                        
                        // Reset form
                        setTimeout(() => {
                            document.getElementById('uploadForm').reset();
                            document.querySelectorAll('.file-input-wrapper').forEach(w => {
                                w.classList.remove('has-file');
                            });
                            document.querySelectorAll('.selected-file').forEach(s => {
                                s.textContent = '';
                            });
                        }, 2000);
                    } else {
                        const error = await response.text();
                        throw new Error(error || 'Processing failed');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    showStatus('error', `❌ Error: ${error.message || 'Something went wrong. Please try again.'}`);
                } finally {
                    submitBtn.disabled = false;
                }
            });
            
            function showStatus(type, message) {
                const status = document.getElementById('status');
                status.className = `status-${type}`;
                status.innerHTML = message;
                status.style.display = 'block';
                
                if (type !== 'loading') {
                    setTimeout(() => {
                        status.style.display = 'none';
                    }, 10000);
                }
            }
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "caption-colorizer",
            "version": "1.0.0",
            "storage_available": shutil.disk_usage(STORAGE_DIR).free > 100 * 1024 * 1024  # 100MB free
        },
        status_code=200
    )

@app.post("/process")
async def process_captions(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    srt: UploadFile = File(...)
):
    """Process video and SRT to generate colored captions"""
    
    # Validate file extensions
    if not video.filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
        raise HTTPException(status_code=400, detail="Invalid video format")
    
    if not srt.filename.lower().endswith('.srt'):
        raise HTTPException(status_code=400, detail="Invalid subtitle format")
    
    # Check file size
    if video.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Video file too large (max 500MB)")
    
    # Create unique session
    session_id = str(uuid.uuid4())[:8]  # Shorter ID for cleaner logs
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    
    logger.info(f"Processing request {session_id}: video={video.filename}, srt={srt.filename}")
    
    try:
        # Save uploaded files
        video_path = session_dir / f"input{Path(video.filename).suffix}"
        srt_path = session_dir / "input.srt"
        
        # Save video
        with open(video_path, "wb") as f:
            content = await video.read()
            f.write(content)
        
        # Save SRT
        with open(srt_path, "wb") as f:
            content = await srt.read()
            f.write(content)
        
        # Process using existing code
        output_dir = OUTPUT_DIR / session_id
        output_dir.mkdir(exist_ok=True)
        
        # Load config and create renderer
        cfg = load_config()
        renderer = CaptionRenderer(cfg)
        
        # Generate colored caption PNGs and XML
        caption_output = output_dir / "captions"
        renderer.render(
            mode="images-xml",
            video=video_path,
            srt=srt_path,
            out=caption_output,
            track_index=2,
            seed=None,
            show_progress=False
        )
        
        # Create ZIP archive
        zip_path = output_dir / f"captions_{session_id}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all files from caption output directory
            for file_path in caption_output.glob("*"):
                zipf.write(file_path, file_path.name)
            
            # Add a README
            readme_content = f"""Caption Colorizer Output
========================

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Session: {session_id}

Files included:
- cap_XXXX.png: Individual caption images
- captions.fcpxml or captions.xml: Premiere Pro import file

How to use in Premiere Pro:
1. Import the XML file into your project
2. The captions will appear as a sequence with proper timing
3. Place the sequence above your video track

Need help? Visit: https://github.com/yourusername/CaptionScript
"""
            zipf.writestr("README.txt", readme_content)
        
        logger.info(f"Successfully processed {session_id}")
        
        # Schedule cleanup (don't await, let it run in background)
        background_tasks.add_task(cleanup_session_files, session_id)
        
        return FileResponse(
            path=zip_path,
            filename=f"colored_captions_{session_id}.zip",
            media_type="application/zip"
        )
        
    except Exception as e:
        logger.error(f"Error processing {session_id}: {str(e)}")
        
        # Clean up on error
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)
        if 'output_dir' in locals() and output_dir.exists():
            shutil.rmtree(output_dir, ignore_errors=True)
        
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )

async def cleanup_session_files(session_id: str):
    """Clean up session files after a delay"""
    await asyncio.sleep(300)  # Wait 5 minutes before cleanup
    
    try:
        session_upload = UPLOAD_DIR / session_id
        session_output = OUTPUT_DIR / session_id
        
        if session_upload.exists():
            shutil.rmtree(session_upload, ignore_errors=True)
        if session_output.exists():
            shutil.rmtree(session_output, ignore_errors=True)
        
        logger.info(f"Cleaned up session {session_id}")
    except Exception as e:
        logger.error(f"Error cleaning up session {session_id}: {e}")

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or default
    port = int(os.environ.get("PORT", 8000))
    
    # Run the app
    uvicorn.run(
        "webapp:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )
