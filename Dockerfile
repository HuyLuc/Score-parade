# ============================================
# Dockerfile for Score-Parade Backend
# Multi-stage build for smaller image size
# ============================================

# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend files
COPY frontend/package*.json ./
RUN npm ci --silent

COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend with CUDA support (optional)
# Stage 2: Python backend
# Dùng Python 3.10 để tương thích torchreid (OSNet)
FROM python:3.10-slim AS backend

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies
# Debian trixie: libgl1-mesa-glx được thay bằng libgl1
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies FIRST (for better caching)
# Dependencies change less frequently than code
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r backend/requirements.txt && \
    pip install --no-cache-dir openmim && \
    mim install mmengine && \
    mim install "mmcv>=2.0.0" && \
    pip install --no-cache-dir "chumpy==0.70" || echo "Warning: chumpy installation failed, continuing..." && \
    pip install --no-cache-dir mmpose || \
    (pip install --no-cache-dir mmpose --no-deps && \
     pip install --no-cache-dir "numpy<2.0" "scipy>=1.10.0" "opencv-python>=4.8.0" "pillow>=10.0.0" "pyyaml>=6.0" "matplotlib>=3.7.0" "termcolor" "yapf" "addict" "rich" "tabulate" "model-index" "opendatalab" "openxlab")

# Copy backend code (this layer will be rebuilt when code changes)
COPY backend/ ./backend/

# Copy YOLOv8 model files (optional - models can be downloaded at runtime)
# Uncomment if you want to include models in image
# COPY yolov8n-pose.pt ./
# COPY yolov8s-pose.pt ./

# Copy data directory structure (only structure, not large files)
# Large files should be mounted as volumes
COPY data/ ./data/

# Copy frontend build from stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create necessary directories
RUN mkdir -p /app/data/output \
    /app/data/golden_template \
    /app/data/input_videos \
    /app/data/models \
    /app/data/cache

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

