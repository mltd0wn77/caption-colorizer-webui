#!/usr/bin/env python3
"""
Production FastAPI application for Caption Colorizer Web UI
with progress tracking and fixed configuration
"""

import os
import sys
import shutil
import asyncio
import logging
import zipfile
import uuid
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
import uvicorn

# Add the parent directory to the path so we can import captions module
sys.path.insert(0, str(Path(__file__).parent))

from captions.config import load_config
from captions.renderer import CaptionRenderer

# Configuration
STORAGE_DIR = Path(os.environ.get("STORAGE_PATH", "/app/storage"))
UPLOAD_DIR = STORAGE_DIR / "uploads"
OUTPUT_DIR = STORAGE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True, parents=True)
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Limits
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("webapp")

# Progress tracking
progress_store = {}

app = FastAPI(title="Caption Colorizer")

# Cleanup old files on startup
def cleanup_old_files():
    """Remove files older than 1 hour"""
    try:
        cutoff_time = time.time() - 3600  # 1 hour
        
        for dir_path in [UPLOAD_DIR, OUTPUT_DIR]:
            if dir_path.exists():
                for item in dir_path.iterdir():
                    if item.is_dir():
                        # Check creation time of directory
                        if item.stat().st_mtime < cutoff_time:
                            shutil.rmtree(item, ignore_errors=True)
                            logger.info(f"Cleaned up old directory: {item}")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

@app.on_event("startup")
async def startup_event():
    """Run cleanup on startup"""
    logger.info("Caption Colorizer started successfully")
    cleanup_old_files()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Caption Colorizer shutting down")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML interface"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Caption Colorizer - Professional Subtitle Styling</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            
            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                padding: 40px;
                max-width: 600px;
                width: 100%;
                animation: fadeIn 0.5s ease-in;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .header {
                text-align: center;
                margin-bottom: 30px;
            }
            
            .logo {
                width: 60px;
                height: 60px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 15px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 15px;
                font-size: 30px;
            }
            
            h1 {
                color: #2d3748;
                font-size: 28px;
                font-weight: 700;
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
                opacity: 0.6;
                cursor: not-allowed;
            }
            
            .status-loading, .status-success, .status-error {
                padding: 15px;
                border-radius: 10px;
                margin-top: 20px;
                font-size: 14px;
                display: none;
                animation: slideIn 0.3s ease;
            }
            
            @keyframes slideIn {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .status-loading {
                background: #e6f4ff;
                color: #0066cc;
                border: 1px solid #b3d9ff;
            }
            
            .status-success {
                background: #f0fff4;
                color: #22543d;
                border: 1px solid #9ae6b4;
            }
            
            .status-error {
                background: #fff5f5;
                color: #742a2a;
                border: 1px solid #feb2b2;
            }
            
            .progress-container {
                margin-top: 15px;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
                display: none;
            }
            
            .progress-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
                font-size: 14px;
            }
            
            .progress-status {
                color: #4a5568;
                font-weight: 500;
            }
            
            .progress-time {
                color: #718096;
                font-size: 12px;
            }
            
            .progress-bar {
                width: 100%;
                height: 8px;
                background: #e2e8f0;
                border-radius: 4px;
                overflow: hidden;
                position: relative;
            }
            
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                border-radius: 4px;
                transition: width 0.3s ease;
                position: absolute;
                left: 0;
                top: 0;
            }
            
            .progress-percentage {
                text-align: center;
                margin-top: 8px;
                font-size: 16px;
                font-weight: 600;
                color: #667eea;
            }
            
            .spinner {
                display: inline-block;
                width: 16px;
                height: 16px;
                border: 2px solid #667eea;
                border-radius: 50%;
                border-top-color: transparent;
                animation: spin 0.8s linear infinite;
            }
            
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            
            .error-details {
                margin-top: 10px;
                padding: 10px;
                background: #fff;
                border-radius: 5px;
                font-family: monospace;
                font-size: 12px;
                color: #e53e3e;
            }
            
            .footer {
                margin-top: 30px;
                text-align: center;
                color: #a0aec0;
                font-size: 12px;
            }
            
            .download-section {
                margin-top: 20px;
                padding: 20px;
                background: linear-gradient(135deg, #f0f3ff 0%, #e6f4ff 100%);
                border-radius: 12px;
                text-align: center;
                display: none;
                animation: fadeIn 0.5s ease;
            }
            
            .download-btn {
                background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                box-shadow: 0 4px 15px rgba(72, 187, 120, 0.3);
                margin-top: 10px;
            }
            
            .download-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(72, 187, 120, 0.4);
            }
            
            .download-message {
                color: #2d3748;
                font-size: 16px;
                margin-bottom: 10px;
                font-weight: 500;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">🎨</div>
                <h1>Caption Colorizer</h1>
                <p class="subtitle">Transform your subtitles with professional styling for Premiere Pro</p>
            </div>
            
            <div class="features">
                <div class="feature">
                    <span class="feature-icon">🎬</span>
                    <span>ALL CAPS formatting</span>
                </div>
                <div class="feature">
                    <span class="feature-icon">🎨</span>
                    <span>Smart accent colors</span>
                </div>
                <div class="feature">
                    <span class="feature-icon">📐</span>
                    <span>Auto-trimmed PNGs</span>
                </div>
                <div class="feature">
                    <span class="feature-icon">📦</span>
                    <span>Premiere Pro XML</span>
                </div>
            </div>
            
            <form id="uploadForm" class="upload-form">
                <div class="file-input-wrapper" onclick="document.getElementById('videoFile').click()">
                    <input type="file" id="videoFile" name="video" accept=".mp4,.mov,.avi,.mkv" required>
                    <div class="file-label">📹 Select Video File</div>
                    <div class="file-info">MP4, MOV, AVI, MKV (max 500MB)</div>
                    <div class="selected-file" id="videoFileName"></div>
                </div>
                
                <div class="file-input-wrapper" onclick="document.getElementById('srtFile').click()">
                    <input type="file" id="srtFile" name="srt" accept=".srt" required>
                    <div class="file-label">📝 Select SRT File</div>
                    <div class="file-info">SubRip subtitle file (.srt)</div>
                    <div class="selected-file" id="srtFileName"></div>
                </div>
                
                <button type="submit" class="submit-btn">
                    Generate Colored Captions
                </button>
            </form>
            
            <div id="status"></div>
            
            <div id="progressContainer" class="progress-container">
                <div class="progress-header">
                    <span class="progress-status" id="progressStatus">Preparing...</span>
                    <span class="progress-time" id="progressTime">0:00</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill" style="width: 0%"></div>
                </div>
                <div class="progress-percentage" id="progressPercentage">0%</div>
            </div>
            
            <div id="downloadSection" class="download-section">
                <div class="download-message">✨ Your captions are ready!</div>
                <button id="downloadBtn" class="download-btn">Download Colored Captions</button>
            </div>
            
            <div class="footer">
                <p>Your files are processed securely and deleted after 1 hour</p>
            </div>
        </div>
        
        <script>
            let startTime = null;
            let progressInterval = null;
            let eventSource = null;
            let currentSessionId = null;
            
            // Check for existing session on page load
            window.addEventListener('load', function() {
                const savedSession = localStorage.getItem('captionSession');
                if (savedSession) {
                    const sessionData = JSON.parse(savedSession);
                    // Check if session is less than 1 hour old
                    if (Date.now() - sessionData.timestamp < 3600000) {
                        currentSessionId = sessionData.sessionId;
                        checkSessionStatus(currentSessionId);
                    } else {
                        localStorage.removeItem('captionSession');
                    }
                }
            });
            
            // File input handlers
            document.getElementById('videoFile').addEventListener('change', function(e) {
                const fileName = e.target.files[0]?.name || '';
                document.getElementById('videoFileName').textContent = fileName ? `✓ ${fileName}` : '';
                e.target.parentElement.classList.toggle('has-file', !!fileName);
            });
            
            document.getElementById('srtFile').addEventListener('change', function(e) {
                const fileName = e.target.files[0]?.name || '';
                document.getElementById('srtFileName').textContent = fileName ? `✓ ${fileName}` : '';
                e.target.parentElement.classList.toggle('has-file', !!fileName);
            });
            
            // Download button handler
            document.getElementById('downloadBtn').addEventListener('click', async function() {
                if (currentSessionId) {
                    await downloadResult(currentSessionId);
                }
            });
            
            // Form submission
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const videoFile = document.getElementById('videoFile').files[0];
                const srtFile = document.getElementById('srtFile').files[0];
                
                if (!videoFile || !srtFile) {
                    showStatus('error', '❌ Please select both video and SRT files');
                    return;
                }
                
                const formData = new FormData();
                formData.append('video', videoFile);
                formData.append('srt', srtFile);
                
                const submitBtn = e.target.querySelector('.submit-btn');
                submitBtn.disabled = true;
                
                // Clear any previous session
                localStorage.removeItem('captionSession');
                hideDownloadSection();
                
                showStatus('loading', '<span class="spinner"></span> Uploading files...');
                showProgress();
                
                try {
                    const response = await fetch('/process', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        currentSessionId = data.session_id;
                        
                        // Save session to localStorage
                        localStorage.setItem('captionSession', JSON.stringify({
                            sessionId: currentSessionId,
                            timestamp: Date.now()
                        }));
                        
                        // Start progress tracking
                        trackProgress(currentSessionId);
                        
                    } else {
                        const error = await response.text();
                        throw new Error(error || 'Processing failed');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    hideProgress();
                    showStatus('error', `❌ Error: ${error.message || 'Something went wrong. Please try again.'}`);
                    submitBtn.disabled = false;
                }
            });
            
            function trackProgress(sessionId) {
                if (eventSource) {
                    eventSource.close();
                }
                
                eventSource = new EventSource(`/progress/${sessionId}`);
                
                eventSource.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    updateProgress(data);
                    
                    if (data.status === 'completed') {
                        eventSource.close();
                        hideProgress();
                        showDownloadSection();
                        showStatus('success', '✅ Your captions are ready! Click the download button below.');
                        document.querySelector('.submit-btn').disabled = false;
                    } else if (data.status === 'error') {
                        eventSource.close();
                        hideProgress();
                        showStatus('error', `❌ Error: ${data.message}`);
                        document.querySelector('.submit-btn').disabled = false;
                        localStorage.removeItem('captionSession');
                    }
                };
                
                eventSource.onerror = function() {
                    // Don't immediately show error - connection might reconnect
                    console.log('EventSource connection lost, will retry...');
                };
            }
            
            async function checkSessionStatus(sessionId) {
                try {
                    const response = await fetch(`/status/${sessionId}`);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.status === 'completed') {
                            currentSessionId = sessionId;
                            showDownloadSection();
                            showStatus('success', '✅ Your previous session is ready for download!');
                        } else if (data.status === 'processing') {
                            showStatus('loading', '<span class="spinner"></span> Resuming previous processing...');
                            showProgress();
                            trackProgress(sessionId);
                        }
                    }
                } catch (error) {
                    console.error('Error checking session status:', error);
                    localStorage.removeItem('captionSession');
                }
            }
            
            async function downloadResult(sessionId) {
                try {
                    const response = await fetch(`/download/${sessionId}`);
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
                        
                        showStatus('success', '✅ Download started! Check your downloads folder.');
                    } else {
                        throw new Error('Download failed');
                    }
                } catch (error) {
                    showStatus('error', '❌ Download failed. Please try again.');
                }
            }
            
            function showDownloadSection() {
                document.getElementById('downloadSection').style.display = 'block';
            }
            
            function hideDownloadSection() {
                document.getElementById('downloadSection').style.display = 'none';
            }
            
            function showProgress() {
                document.getElementById('progressContainer').style.display = 'block';
                startTime = Date.now();
                progressInterval = setInterval(updateElapsedTime, 100);
            }
            
            function hideProgress() {
                document.getElementById('progressContainer').style.display = 'none';
                if (progressInterval) {
                    clearInterval(progressInterval);
                    progressInterval = null;
                }
                startTime = null;
            }
            
            function updateProgress(data) {
                const percentage = Math.round(data.progress * 100);
                document.getElementById('progressFill').style.width = percentage + '%';
                document.getElementById('progressPercentage').textContent = percentage + '%';
                document.getElementById('progressStatus').textContent = data.message || 'Processing...';
                
                if (data.status === 'processing') {
                    showStatus('loading', `<span class="spinner"></span> ${data.message}`);
                }
            }
            
            function updateElapsedTime() {
                if (!startTime) return;
                const elapsed = Math.floor((Date.now() - startTime) / 1000);
                const minutes = Math.floor(elapsed / 60);
                const seconds = elapsed % 60;
                document.getElementById('progressTime').textContent = 
                    `${minutes}:${seconds.toString().padStart(2, '0')}`;
            }
            
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
            "version": "2.0.0",
            "storage_available": shutil.disk_usage(STORAGE_DIR).free > 100 * 1024 * 1024  # 100MB free
        },
        status_code=200
    )

async def process_with_progress(session_id: str, video_path: Path, srt_path: Path, output_dir: Path):
    """Process captions with progress tracking"""
    try:
        # Initialize progress
        progress_store[session_id] = {
            "status": "processing",
            "progress": 0.0,
            "message": "Preparing...",
            "total_steps": 100
        }
        
        # Load config and override settings for proper formatting
        cfg = load_config()
        
        # Ensure ALL CAPS and proper font
        cfg["text"]["capitalization"] = "upper"  # Force ALL CAPS
        cfg["text"]["weight"] = 700  # Bold, not italic
        
        # Create renderer
        renderer = CaptionRenderer(cfg)
        
        # Update progress: Preparation complete (10%)
        progress_store[session_id].update({
            "progress": 0.1,
            "message": "Analyzing video and captions..."
        })
        await asyncio.sleep(0.1)  # Allow progress update to be sent
        
        # Count captions for progress tracking
        from captions.parser import parse_srt
        captions = parse_srt(srt_path)
        total_captions = len(captions)
        
        # Custom render function with progress updates
        caption_output = output_dir / "captions"
        
        # We'll need to modify the render call to track progress
        # Since we can't directly modify the renderer, we'll use a wrapper approach
        
        progress_store[session_id].update({
            "progress": 0.2,
            "message": f"Generating {total_captions} caption frames..."
        })
        
        # Generate colored caption PNGs and XML
        renderer.render(
            mode="images-xml",
            video=video_path,
            srt=srt_path,
            out=caption_output,
            track_index=2,
            seed=None,
            show_progress=False
        )
        
        # Update progress: Rendering complete (90%)
        progress_store[session_id].update({
            "progress": 0.9,
            "message": "Packaging files..."
        })
        await asyncio.sleep(0.1)
        
        # Create ZIP archive
        zip_path = output_dir / f"captions_{session_id}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all PNG files
            for png_file in caption_output.glob("*.png"):
                zipf.write(png_file, arcname=png_file.name)
            
            # Add XML file
            xml_file = caption_output / "captions.xml"
            if xml_file.exists():
                zipf.write(xml_file, arcname="captions.xml")
            
            # Add manifest if exists
            manifest_file = caption_output / "captions_manifest.csv"
            if manifest_file.exists():
                zipf.write(manifest_file, arcname="captions_manifest.csv")
        
        # Update progress: Complete (100%)
        progress_store[session_id].update({
            "status": "completed",
            "progress": 1.0,
            "message": "Processing complete!",
            "zip_path": str(zip_path)
        })
        
        logger.info(f"Successfully processed {session_id}")
        
    except Exception as e:
        logger.error(f"Error processing {session_id}: {e}")
        progress_store[session_id] = {
            "status": "error",
            "progress": 0,
            "message": str(e)
        }
    finally:
        # Schedule cleanup after delay
        await asyncio.sleep(3600)  # Keep for 1 hour
        if session_id in progress_store:
            del progress_store[session_id]
        
        # Cleanup files
        try:
            if (UPLOAD_DIR / session_id).exists():
                shutil.rmtree(UPLOAD_DIR / session_id)
            if (OUTPUT_DIR / session_id).exists():
                shutil.rmtree(OUTPUT_DIR / session_id)
        except Exception as e:
            logger.error(f"Error cleaning up {session_id}: {e}")

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
    session_id = str(uuid.uuid4())[:8]
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
        
        # Start processing in background
        background_tasks.add_task(
            process_with_progress,
            session_id,
            video_path,
            srt_path,
            output_dir
        )
        
        return JSONResponse({"session_id": session_id})
        
    except Exception as e:
        logger.error(f"Error setting up processing for {session_id}: {e}")
        # Cleanup on error
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{session_id}")
async def get_status(session_id: str):
    """Check the status of a processing session"""
    if session_id in progress_store:
        return JSONResponse(progress_store[session_id])
    
    # Check if result exists
    zip_path = OUTPUT_DIR / session_id / f"captions_{session_id}.zip"
    if zip_path.exists():
        return JSONResponse({"status": "completed", "message": "Processing complete"})
    
    return JSONResponse({"status": "not_found", "message": "Session not found"}, status_code=404)

@app.get("/progress/{session_id}")
async def get_progress(session_id: str):
    """Server-Sent Events endpoint for progress updates"""
    async def generate():
        while True:
            if session_id in progress_store:
                data = progress_store[session_id]
                yield f"data: {json.dumps(data)}\n\n"
                
                if data["status"] in ["completed", "error"]:
                    break
            else:
                yield f"data: {json.dumps({'status': 'waiting', 'progress': 0, 'message': 'Waiting...'})}\n\n"
            
            await asyncio.sleep(0.5)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/download/{session_id}")
async def download_result(session_id: str):
    """Download the processed caption files"""
    zip_path = OUTPUT_DIR / session_id / f"captions_{session_id}.zip"
    
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"colored_captions_{session_id}.zip"
    )

if __name__ == "__main__":
    # For local development
    uvicorn.run(
        "webapp_production_v2:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=True
    )
