#!/usr/bin/env python3
"""
Enhanced FastAPI application for Caption Colorizer Web UI
with custom font upload and color customization
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
from typing import Optional, Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
import uvicorn

# Add the parent directory to the path so we can import captions module
sys.path.insert(0, str(Path(__file__).parent))

from captions.config import load_config
from captions.renderer import CaptionRenderer

# Configuration
STORAGE_DIR = Path(os.getenv("STORAGE_PATH", "/app/storage"))
UPLOAD_DIR = STORAGE_DIR / "uploads"
OUTPUT_DIR = STORAGE_DIR / "outputs"
FONTS_DIR = STORAGE_DIR / "fonts"
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB

# Create directories
for dir_path in [UPLOAD_DIR, OUTPUT_DIR, FONTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("webapp")

# Global storage for progress tracking
progress_store: Dict[str, Dict[str, Any]] = {}

app = FastAPI(title="Caption Colorizer Web UI")

# HTML interface with enhanced UI
def get_html_content() -> str:
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Caption Colorizer - Professional Subtitle Generator</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
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
                padding: 40px;
                max-width: 700px;
                width: 100%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            
            h1 {
                color: #2d3748;
                margin-bottom: 10px;
                font-size: 28px;
                text-align: center;
            }
            
            .subtitle {
                color: #718096;
                text-align: center;
                margin-bottom: 30px;
                font-size: 14px;
            }
            
            .form-group {
                margin-bottom: 25px;
            }
            
            .form-section {
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
            }
            
            .section-title {
                font-size: 16px;
                font-weight: 600;
                color: #4a5568;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            label {
                display: block;
                margin-bottom: 8px;
                color: #4a5568;
                font-weight: 500;
                font-size: 14px;
            }
            
            .file-input-wrapper {
                position: relative;
                display: inline-block;
                width: 100%;
            }
            
            .file-input {
                position: absolute;
                opacity: 0;
                width: 100%;
                height: 100%;
                cursor: pointer;
            }
            
            .file-input-label {
                display: block;
                padding: 12px 20px;
                background: #f7fafc;
                border: 2px dashed #cbd5e0;
                border-radius: 10px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 14px;
            }
            
            .file-input-label:hover {
                background: #edf2f7;
                border-color: #a0aec0;
            }
            
            .file-input-wrapper.has-file .file-input-label {
                border-color: #48bb78;
                background: #f0fff4;
            }
            
            .file-name {
                color: #48bb78;
                font-size: 12px;
                margin-top: 5px;
                min-height: 18px;
            }
            
            .color-inputs {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: 10px;
            }
            
            .color-input-group {
                display: flex;
                flex-direction: column;
            }
            
            .color-input-wrapper {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            input[type="color"] {
                width: 40px;
                height: 40px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                cursor: pointer;
            }
            
            input[type="text"].hex-input {
                flex: 1;
                padding: 8px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                font-family: monospace;
                font-size: 13px;
                text-transform: uppercase;
            }
            
            .optional-tag {
                background: #edf2f7;
                color: #718096;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: normal;
            }
            
            .required-tag {
                background: #fee;
                color: #c53030;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: normal;
            }
            
            .submit-btn {
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s ease, opacity 0.2s ease;
            }
            
            .submit-btn:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
            }
            
            .submit-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            
            .status-message {
                margin-top: 20px;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                display: none;
                font-size: 14px;
                animation: slideIn 0.3s ease;
            }
            
            .status-message.show {
                display: block;
            }
            
            .status-message.success {
                background: #f0fff4;
                color: #22543d;
                border: 1px solid #9ae6b4;
            }
            
            .status-message.error {
                background: #fff5f5;
                color: #742a2a;
                border: 1px solid #feb2b2;
            }
            
            .status-message.loading {
                background: #ebf8ff;
                color: #2c5282;
                border: 1px solid #90cdf4;
            }
            
            .progress-container {
                display: none;
                margin-top: 20px;
                padding: 20px;
                background: #f7fafc;
                border-radius: 12px;
            }
            
            .progress-container.show {
                display: block;
                animation: fadeIn 0.3s ease;
            }
            
            .progress-header {
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
                font-size: 14px;
            }
            
            .progress-status {
                color: #4a5568;
                font-weight: 500;
            }
            
            .progress-time {
                color: #718096;
            }
            
            .progress-bar {
                background: #e2e8f0;
                height: 20px;
                border-radius: 10px;
                overflow: hidden;
                position: relative;
            }
            
            .progress-fill {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                height: 100%;
                border-radius: 10px;
                transition: width 0.3s ease;
                box-shadow: 0 2px 4px rgba(102, 126, 234, 0.2);
            }
            
            .progress-percentage {
                text-align: center;
                margin-top: 8px;
                color: #4a5568;
                font-weight: 600;
                font-size: 14px;
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
            
            .download-section.show {
                display: block;
            }
            
            .download-btn {
                background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s ease;
                margin-top: 10px;
            }
            
            .download-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(72, 187, 120, 0.4);
            }
            
            @keyframes slideIn {
                from {
                    transform: translateY(-10px);
                    opacity: 0;
                }
                to {
                    transform: translateY(0);
                    opacity: 1;
                }
            }
            
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            .spinner {
                display: inline-block;
                width: 16px;
                height: 16px;
                border: 3px solid rgba(0,0,0,.1);
                border-radius: 50%;
                border-top-color: #667eea;
                animation: spin 1s ease-in-out infinite;
            }
            
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            
            .footer {
                margin-top: 30px;
                text-align: center;
                color: #a0aec0;
                font-size: 12px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎬 Caption Colorizer Pro</h1>
            <p class="subtitle">Transform your subtitles with beautiful colors and typography</p>
            
            <form id="uploadForm" enctype="multipart/form-data">
                <div class="form-section">
                    <h3 class="section-title">
                        📁 Required Files
                        <span class="required-tag">REQUIRED</span>
                    </h3>
                    
                    <div class="form-group">
                        <label for="videoFile">Video File (MP4)</label>
                        <div class="file-input-wrapper">
                            <input type="file" id="videoFile" name="video_file" accept=".mp4" class="file-input" required>
                            <label for="videoFile" class="file-input-label">
                                📹 Choose video file
                            </label>
                        </div>
                        <div class="file-name" id="videoFileName"></div>
                    </div>
                    
                    <div class="form-group">
                        <label for="srtFile">Subtitle File (SRT)</label>
                        <div class="file-input-wrapper">
                            <input type="file" id="srtFile" name="srt_file" accept=".srt" class="file-input" required>
                            <label for="srtFile" class="file-input-label">
                                📄 Choose SRT file
                            </label>
                        </div>
                        <div class="file-name" id="srtFileName"></div>
                    </div>
                </div>
                
                <div class="form-section">
                    <h3 class="section-title">
                        🎨 Color Customization
                        <span class="optional-tag">OPTIONAL</span>
                    </h3>
                    
                    <div class="color-inputs">
                        <div class="color-input-group">
                            <label>Base Color</label>
                            <div class="color-input-wrapper">
                                <input type="color" id="baseColor" value="#FFFFFF">
                                <input type="text" class="hex-input" id="baseColorHex" value="#FFFFFF" maxlength="7">
                            </div>
                        </div>
                        
                        <div class="color-input-group">
                            <label>Accent 1</label>
                            <div class="color-input-wrapper">
                                <input type="color" id="accent1Color" value="#FF6B6B">
                                <input type="text" class="hex-input" id="accent1ColorHex" value="#FF6B6B" maxlength="7">
                            </div>
                        </div>
                        
                        <div class="color-input-group">
                            <label>Accent 2</label>
                            <div class="color-input-wrapper">
                                <input type="color" id="accent2Color" value="#4ECDC4">
                                <input type="text" class="hex-input" id="accent2ColorHex" value="#4ECDC4" maxlength="7">
                            </div>
                        </div>
                        
                        <div class="color-input-group">
                            <label>Accent 3</label>
                            <div class="color-input-wrapper">
                                <input type="color" id="accent3Color" value="#45B7D1">
                                <input type="text" class="hex-input" id="accent3ColorHex" value="#45B7D1" maxlength="7">
                            </div>
                        </div>
                        
                        <div class="color-input-group">
                            <label>Accent 4</label>
                            <div class="color-input-wrapper">
                                <input type="color" id="accent4Color" value="#F7DC6F">
                                <input type="text" class="hex-input" id="accent4ColorHex" value="#F7DC6F" maxlength="7">
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="form-section">
                    <h3 class="section-title">
                        🔤 Custom Font
                        <span class="optional-tag">OPTIONAL</span>
                    </h3>
                    
                    <div class="form-group">
                        <label for="fontFile">Upload Custom Font (TTF/OTF)</label>
                        <div class="file-input-wrapper">
                            <input type="file" id="fontFile" name="font_file" accept=".ttf,.otf" class="file-input">
                            <label for="fontFile" class="file-input-label">
                                🔤 Choose font file (optional)
                            </label>
                        </div>
                        <div class="file-name" id="fontFileName"></div>
                    </div>
                </div>
                
                <button type="submit" class="submit-btn">🚀 Generate Colored Captions</button>
            </form>
            
            <div class="status-message" id="statusMessage"></div>
            
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
                <h3>✨ Your captions are ready!</h3>
                <p style="margin-top: 10px; color: #718096;">Click below to download your colored captions and XML file.</p>
                <button class="download-btn" id="downloadBtn">📥 Download ZIP</button>
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
            
            // Color input synchronization
            document.querySelectorAll('input[type="color"]').forEach(colorInput => {
                const hexInput = document.getElementById(colorInput.id + 'Hex');
                
                colorInput.addEventListener('input', (e) => {
                    hexInput.value = e.target.value.toUpperCase();
                });
                
                hexInput.addEventListener('input', (e) => {
                    let value = e.target.value;
                    if (!value.startsWith('#')) {
                        value = '#' + value;
                    }
                    value = value.toUpperCase().slice(0, 7);
                    hexInput.value = value;
                    if (/^#[0-9A-F]{6}$/i.test(value)) {
                        colorInput.value = value;
                    }
                });
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
            
            document.getElementById('fontFile').addEventListener('change', function(e) {
                const fileName = e.target.files[0]?.name || '';
                document.getElementById('fontFileName').textContent = fileName ? `✓ ${fileName}` : '';
                e.target.parentElement.classList.toggle('has-file', !!fileName);
            });
            
            // Check for existing session on page load
            window.addEventListener('load', () => {
                const savedSession = localStorage.getItem('captionSession');
                if (savedSession) {
                    try {
                        const session = JSON.parse(savedSession);
                        if (Date.now() - session.timestamp < 3600000) { // 1 hour
                            checkSessionStatus(session.sessionId);
                        } else {
                            localStorage.removeItem('captionSession');
                        }
                    } catch (e) {
                        localStorage.removeItem('captionSession');
                    }
                }
            });
            
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
                            trackProgress(sessionId);
                        }
                    }
                } catch (error) {
                    console.error('Failed to check session status:', error);
                }
            }
            
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const submitBtn = e.target.querySelector('.submit-btn');
                submitBtn.disabled = true;
                
                // Clear any previous session
                localStorage.removeItem('captionSession');
                hideDownloadSection();
                
                showStatus('loading', '<span class="spinner"></span> Uploading files...');
                showProgress();
                
                const formData = new FormData();
                
                // Add files
                formData.append('video_file', document.getElementById('videoFile').files[0]);
                formData.append('srt_file', document.getElementById('srtFile').files[0]);
                
                // Add font if provided
                const fontFile = document.getElementById('fontFile').files[0];
                if (fontFile) {
                    formData.append('font_file', fontFile);
                }
                
                // Add colors
                formData.append('base_color', document.getElementById('baseColorHex').value);
                formData.append('accent1_color', document.getElementById('accent1ColorHex').value);
                formData.append('accent2_color', document.getElementById('accent2ColorHex').value);
                formData.append('accent3_color', document.getElementById('accent3ColorHex').value);
                formData.append('accent4_color', document.getElementById('accent4ColorHex').value);
                
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
                        throw new Error(error || 'Upload failed');
                    }
                } catch (error) {
                    hideProgress();
                    showStatus('error', `❌ Error: ${error.message}`);
                    submitBtn.disabled = false;
                }
            });
            
            function trackProgress(sessionId) {
                // Close any existing connection
                if (eventSource) {
                    eventSource.close();
                }
                
                eventSource = new EventSource(`/progress/${sessionId}`);
                
                eventSource.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    updateProgress(data);
                    
                    if (data.status === 'completed') {
                        eventSource.close();
                        showDownloadSection();
                        hideProgress();
                        showStatus('success', '✅ Success! Your captions are ready.');
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
                    // Will auto-reconnect unless closed
                };
            }
            
            function updateProgress(data) {
                if (data.progress !== undefined) {
                    document.getElementById('progressFill').style.width = data.progress + '%';
                    document.getElementById('progressPercentage').textContent = Math.round(data.progress) + '%';
                }
                if (data.stage) {
                    document.getElementById('progressStatus').textContent = data.stage;
                }
                if (data.elapsed_time !== undefined) {
                    const minutes = Math.floor(data.elapsed_time / 60);
                    const seconds = Math.floor(data.elapsed_time % 60);
                    document.getElementById('progressTime').textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
                }
            }
            
            function showDownloadSection() {
                document.getElementById('downloadSection').classList.add('show');
            }
            
            function hideDownloadSection() {
                document.getElementById('downloadSection').classList.remove('show');
            }
            
            document.getElementById('downloadBtn')?.addEventListener('click', () => {
                if (currentSessionId) {
                    window.location.href = `/download/${currentSessionId}`;
                }
            });
            
            function showProgress() {
                document.getElementById('progressContainer').classList.add('show');
                startTime = Date.now();
                if (progressInterval) clearInterval(progressInterval);
                progressInterval = setInterval(updateElapsedTime, 1000);
            }
            
            function hideProgress() {
                document.getElementById('progressContainer').classList.remove('show');
                if (progressInterval) {
                    clearInterval(progressInterval);
                    progressInterval = null;
                }
            }
            
            function updateElapsedTime() {
                if (startTime) {
                    const elapsed = Math.floor((Date.now() - startTime) / 1000);
                    const minutes = Math.floor(elapsed / 60);
                    const seconds = elapsed % 60;
                    document.getElementById('progressTime').textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
                }
            }
            
            function showStatus(type, message) {
                const statusEl = document.getElementById('statusMessage');
                statusEl.className = `status-message ${type} show`;
                statusEl.innerHTML = message;
            }
        </script>
    </body>
    </html>
    """

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main interface"""
    return get_html_content()

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/process")
async def process_files(
    background_tasks: BackgroundTasks,
    video_file: UploadFile = File(...),
    srt_file: UploadFile = File(...),
    font_file: Optional[UploadFile] = File(None),
    base_color: str = Form("#FFFFFF"),
    accent1_color: str = Form("#FF6B6B"),
    accent2_color: str = Form("#4ECDC4"),
    accent3_color: str = Form("#45B7D1"),
    accent4_color: str = Form("#F7DC6F")
):
    """Process video and SRT files with optional custom font and colors"""
    session_id = str(uuid.uuid4())[:8]
    
    # Validate file sizes
    for file, name in [(video_file, "Video"), (srt_file, "SRT")]:
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"{name} file too large (max 500MB)")
    
    # Create session directories
    session_upload_dir = UPLOAD_DIR / session_id
    session_output_dir = OUTPUT_DIR / session_id
    session_upload_dir.mkdir(parents=True, exist_ok=True)
    session_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded files
    video_path = session_upload_dir / video_file.filename
    srt_path = session_upload_dir / srt_file.filename
    
    with open(video_path, "wb") as f:
        content = await video_file.read()
        f.write(content)
    
    with open(srt_path, "wb") as f:
        content = await srt_file.read()
        f.write(content)
    
    # Handle custom font if provided
    font_path = None
    if font_file and font_file.filename:
        font_path = session_upload_dir / font_file.filename
        with open(font_path, "wb") as f:
            content = await font_file.read()
            f.write(content)
    
    # Initialize progress
    progress_store[session_id] = {
        "status": "processing",
        "progress": 0,
        "stage": "Initializing...",
        "start_time": time.time()
    }
    
    # Process in background
    background_tasks.add_task(
        process_captions_task,
        session_id,
        video_path,
        srt_path,
        session_output_dir,
        font_path,
        {
            "base": base_color,
            "accents": [accent1_color, accent2_color, accent3_color, accent4_color]
        }
    )
    
    logger.info(f"Processing request {session_id}: video={video_file.filename}, srt={srt_file.filename}")
    return {"session_id": session_id, "status": "processing"}

def process_captions_task(
    session_id: str,
    video_path: Path,
    srt_path: Path,
    output_dir: Path,
    font_path: Optional[Path],
    colors: dict
):
    """Background task to process captions with progress tracking"""
    try:
        # Update progress: Preparation
        progress_store[session_id].update({
            "progress": 10,
            "stage": "Loading configuration..."
        })
        
        # Load and customize configuration
        config = load_config()
        
        # Override colors with user input
        config["colors"]["base"] = colors["base"]
        config["colors"]["accents"] = colors["accents"]
        
        # Force ALL CAPS and proper weight
        config["text"]["capitalization"] = "upper"
        config["text"]["weight"] = 700  # Bold, not italic
        
        # Use custom font if provided
        if font_path and font_path.exists():
            config["text"]["fontFamily"] = str(font_path)
            config["text"]["_custom_font_path"] = str(font_path)
            # Use enhanced text renderer for custom fonts
            os.environ["USE_ENHANCED_RENDERER"] = "true"
        
        # Update progress: Processing
        progress_store[session_id].update({
            "progress": 20,
            "stage": "Analyzing video and subtitles..."
        })
        
        # Create renderer with progress callback
        renderer = CaptionRenderer(config)
        
        # Hook into the rendering process for progress updates
        def progress_callback(current: int, total: int, stage: str = ""):
            if total > 0:
                progress = 20 + (current / total) * 70  # 20-90% for rendering
                elapsed = time.time() - progress_store[session_id]["start_time"]
                progress_store[session_id].update({
                    "progress": progress,
                    "stage": stage or f"Generating caption {current}/{total}...",
                    "elapsed_time": elapsed
                })
        
        # Patch the renderer to include progress callback
        original_render = renderer._render_images_xml
        def render_with_progress(video, srt, out_dir, track_index, seed, show_progress):
            # We'll need to modify the actual rendering to report progress
            # For now, simulate progress
            result = original_render(video, srt, out_dir, track_index, seed, show_progress)
            return result
        
        renderer._render_images_xml = render_with_progress
        
        # Process the captions
        pngs_dir = output_dir / "colored_captions"
        renderer.render(
            mode="images-xml",
            video=video_path,
            srt=srt_path,
            out_dir=pngs_dir,
            seed=42
        )
        
        # Update progress: Exporting
        progress_store[session_id].update({
            "progress": 90,
            "stage": "Creating download package..."
        })
        
        # Create ZIP file
        zip_path = output_dir / f"captions_{session_id}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in pngs_dir.rglob('*'):
                if file_path.is_file():
                    zf.write(file_path, file_path.relative_to(pngs_dir))
        
        # Update progress: Complete
        elapsed = time.time() - progress_store[session_id]["start_time"]
        progress_store[session_id] = {
            "status": "completed",
            "progress": 100,
            "stage": "Complete!",
            "elapsed_time": elapsed
        }
        
        # Clean up temporary files
        shutil.rmtree(video_path.parent, ignore_errors=True)
        
    except Exception as e:
        logger.error(f"Error processing {session_id}: {str(e)}")
        progress_store[session_id] = {
            "status": "error",
            "message": str(e),
            "progress": 0
        }

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
    """Stream progress updates via Server-Sent Events"""
    async def event_generator():
        while True:
            if session_id in progress_store:
                data = progress_store[session_id]
                
                # Calculate elapsed time
                if "start_time" in data:
                    data["elapsed_time"] = time.time() - data["start_time"]
                
                yield f"data: {json.dumps(data)}\n\n"
                
                if data["status"] in ["completed", "error"]:
                    break
            else:
                yield f'data: {{"status": "not_found"}}\n\n'
                break
            
            await asyncio.sleep(0.5)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "Connection": "keep-alive",
        }
    )

@app.get("/download/{session_id}")
async def download_result(session_id: str):
    """Download the processed captions ZIP file"""
    zip_path = OUTPUT_DIR / session_id / f"captions_{session_id}.zip"
    
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Result not found")
    
    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"colored_captions_{session_id}.zip"
    )

# Cleanup old files periodically
async def cleanup_old_files():
    """Remove files older than 1 hour"""
    while True:
        await asyncio.sleep(3600)  # Check every hour
        cutoff_time = time.time() - 3600  # 1 hour ago
        
        for dir_path in [UPLOAD_DIR, OUTPUT_DIR]:
            for session_dir in dir_path.iterdir():
                if session_dir.is_dir():
                    if session_dir.stat().st_mtime < cutoff_time:
                        shutil.rmtree(session_dir, ignore_errors=True)
                        logger.info(f"Cleaned up old session: {session_dir.name}")

@app.on_event("startup")
async def startup_event():
    """Start background cleanup task"""
    asyncio.create_task(cleanup_old_files())
    logger.info("Caption Colorizer started successfully")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
