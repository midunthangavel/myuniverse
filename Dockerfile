# Multi-Stage Dockerfile for Synapse AI Backend Cloud Engine
# Base: Python 3.12 Slim (Linux Debian Bookworm)
FROM python:3.12-slim AS base

# Install system dependencies for audio, networking, and OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency requirements
COPY backend/requirements.txt ./requirements.txt

# Install python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend /app/backend

# Create storage directory for ChromaDB vector embeddings and SQLite memory
RUN mkdir -p /app/backend/chroma_db

# Expose FastAPI HTTP & WebSocket port
EXPOSE 8000

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Launch Uvicorn production server
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
