"""
FastAPI Main Application
Score Parade - Hệ thống chấm điểm điều lệnh tự động
"""
import logging
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import tempfile
from pathlib import Path

from backend.app.api import global_mode, config
from backend.app.config import API_CONFIG
from backend.app.utils.exceptions import CustomException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=API_CONFIG["title"],
    version=API_CONFIG["version"],
    docs_url=API_CONFIG["docs_url"],
    redoc_url=API_CONFIG["redoc_url"]
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(global_mode.router)
app.include_router(config.router)

# Serve skeleton videos from temp directory
temp_dir = Path(tempfile.gettempdir())
@app.get("/api/videos/{filename}")
async def get_skeleton_video(filename: str):
    """Serve skeleton video files"""
    video_path = temp_dir / filename
    
    # ✅ LOGGING
    logger.info(f"Request for skeleton video: {filename}")
    
    if not video_path.exists():
        logger.error(f"❌ Video not found: {video_path}")
        raise HTTPException(status_code=404, detail=f"Video not found: {filename}")
    
    # ✅ CHECK file size
    try:
        file_size = video_path.stat().st_size
        if file_size == 0:
            logger.error(f"❌ Video file is empty: {video_path}")
            raise HTTPException(status_code=500, detail="Video file is corrupted (0 bytes)")
    except OSError as e:
        logger.error(f"❌ Cannot access video file: {e}")
        raise HTTPException(status_code=500, detail="Cannot access video file")
    
    # ✅ VALIDATE extension
    if video_path.suffix not in ['.mp4', '.avi', '.mov', '.mkv']:
        logger.error(f"❌ Invalid video format: {video_path.suffix}")
        raise HTTPException(status_code=400, detail=f"Invalid video format: {video_path.suffix}")
    
    try:
        logger.info(f"✅ Serving skeleton video: {filename} ({file_size} bytes)")
        return FileResponse(
            str(video_path),
            media_type='video/mp4',
            filename=filename,
            headers={
                "Accept-Ranges": "bytes",  # Enable video seeking
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        logger.error(f"❌ Error serving video: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error serving video: {str(e)}")


@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    """Handle custom exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "code": exc.code,
            "path": str(request.url)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Lỗi server nội bộ",
            "code": "INTERNAL_ERROR",
            "path": str(request.url)
        }
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Score Parade API",
        "version": API_CONFIG["version"],
        "docs": API_CONFIG["docs_url"]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "score-parade-api"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
