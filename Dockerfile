# Optimized Dockerfile for production deployment
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-inter \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements-web.txt

# Copy application code
COPY --chown=appuser:appuser captions/ ./captions/
COPY --chown=appuser:appuser webapp_enhanced.py ./webapp.py

# Create necessary directories
RUN mkdir -p /app/storage/uploads /app/storage/outputs && \
    chown -R appuser:appuser /app/storage

# Switch to non-root user
USER appuser

# Initialize config
RUN python -m captions init-config

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Start the application
CMD ["uvicorn", "webapp:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
