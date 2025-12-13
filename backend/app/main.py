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
    if video_path.exists() and video_path.suffix in ['.mp4', '.avi', '.mov', '.mkv']:
        return FileResponse(
            str(video_path),
            media_type='video/mp4',
            filename=filename
        )
    raise HTTPException(status_code=404, detail="Video not found")


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
