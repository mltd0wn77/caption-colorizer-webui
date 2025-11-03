# Deployment Guide for Caption Colorizer Web App

## Quick Start (Local Testing)

```bash
# Install dependencies
pip install -r requirements-web.txt

# Initialize config (if not already done)
python -m captions init-config

# Run the web server
python webapp.py
```

Visit http://localhost:8000 to access the web interface.

## Production Deployment Options

### Option 1: Simple VPS Deployment (Recommended for Start)

#### 1. Get a VPS
- **DigitalOcean**: $12/month (2GB RAM, 2 CPUs)
- **Linode**: $12/month (2GB RAM, 1 CPU)
- **Hetzner**: €4.51/month (2GB RAM, 2 CPUs) - Best value

#### 2. Server Setup (Ubuntu 22.04)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and ffmpeg
sudo apt install python3-pip python3-venv ffmpeg -y

# Clone your repository
git clone https://github.com/yourusername/CaptionScript.git
cd CaptionScript

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements-web.txt

# Initialize config
python -m captions init-config

# Install and configure nginx
sudo apt install nginx -y

# Configure nginx (see nginx.conf below)
sudo nano /etc/nginx/sites-available/caption-colorizer

# Enable site
sudo ln -s /etc/nginx/sites-available/caption-colorizer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Create systemd service (see caption-colorizer.service below)
sudo nano /etc/systemd/system/caption-colorizer.service

# Start service
sudo systemctl enable caption-colorizer
sudo systemctl start caption-colorizer
```

#### 3. Nginx Configuration (`/etc/nginx/sites-available/caption-colorizer`)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 500M;  # Allow large video uploads
    proxy_read_timeout 300s;     # 5 min timeout for processing
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

#### 4. Systemd Service (`/etc/systemd/system/caption-colorizer.service`)

```ini
[Unit]
Description=Caption Colorizer Web Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/CaptionScript
Environment="PATH=/path/to/CaptionScript/venv/bin"
ExecStart=/path/to/CaptionScript/venv/bin/python webapp.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Option 2: Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

# Copy application code
COPY captions/ ./captions/
COPY webapp.py .

# Create directories
RUN mkdir -p uploads outputs

# Initialize config
RUN python -m captions init-config

EXPOSE 8000

CMD ["uvicorn", "webapp:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t caption-colorizer .
docker run -p 8000:8000 caption-colorizer
```

### Option 3: Cloud Platform Deployment

#### Google Cloud Run (Serverless)
```bash
# Build container
gcloud builds submit --tag gcr.io/YOUR-PROJECT/caption-colorizer

# Deploy
gcloud run deploy caption-colorizer \
  --image gcr.io/YOUR-PROJECT/caption-colorizer \
  --platform managed \
  --memory 2Gi \
  --timeout 300 \
  --max-instances 10 \
  --allow-unauthenticated
```

#### AWS Lambda + S3 (Not recommended due to 15min timeout limit)

## MCP Server Implementation (If You Want ChatGPT Integration Later)

Create `mcp_server.py`:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json
import asyncio
from typing import AsyncGenerator

app = FastAPI()

@app.get("/mcp/sse")
async def mcp_sse_endpoint(authorization: str = None):
    """MCP Server-Sent Events endpoint"""
    
    async def event_generator() -> AsyncGenerator[str, None]:
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connection', 'status': 'connected'})}\n\n"
        
        # Send tool definitions
        tools = {
            "type": "tools",
            "tools": [{
                "name": "process_captions",
                "description": "Process video captions with color styling",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "video_url": {"type": "string"},
                        "srt_content": {"type": "string"}
                    },
                    "required": ["video_url", "srt_content"]
                }
            }]
        }
        yield f"data: {json.dumps(tools)}\n\n"
        
        # Keep connection alive
        while True:
            await asyncio.sleep(30)
            yield f"data: {json.dumps({'type': 'ping'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

# Add to ChatGPT via:
# {
#   "type": "url",
#   "url": "https://your-domain.com/mcp/sse",
#   "name": "caption-colorizer",
#   "authorization_token": "your-secret"
# }
```

## Monitoring & Maintenance

### Add Logging
```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Add Health Check Endpoint
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

### Regular Cleanup Cron Job
```bash
# Add to crontab
0 * * * * find /app/uploads -mtime +1 -delete
0 * * * * find /app/outputs -mtime +1 -delete
```

## Performance Optimization

1. **Use Redis for caching** processed results
2. **Implement job queue** (Celery) for large videos
3. **Add CDN** (Cloudflare) for static assets
4. **Horizontal scaling** with load balancer

## Security Considerations

1. **Add rate limiting** to prevent abuse
2. **Implement file type validation**
3. **Add virus scanning** for uploaded files
4. **Use HTTPS** with Let's Encrypt
5. **Add authentication** if needed

## Estimated Costs

- **Basic VPS**: $10-20/month
- **Storage**: $5-10/month (if using S3)
- **Domain**: $10-15/year
- **SSL Certificate**: Free (Let's Encrypt)

**Total: ~$15-30/month** for basic deployment
