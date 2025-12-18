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

from backend.app.api import global_mode, config, sessions as sessions_api
from backend.app.config import API_CONFIG
from backend.app.utils.exceptions import CustomException
from backend.app.database.connection import init_db, check_db_connection

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

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup"""
    try:
        # Check database connection
        if check_db_connection():
            # Create tables if they don't exist
            init_db()
            logger.info("✅ Database initialized successfully")
        else:
            logger.warning("⚠️ Database connection failed - running without database persistence")
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}")
        logger.warning("⚠️ Application will continue without database persistence")

# Include routers
app.include_router(global_mode.router)
app.include_router(config.router)
app.include_router(sessions_api.router)

# Import local mode router
try:
    from backend.app.api import local_mode
    app.include_router(local_mode.router)
except ImportError:
    logger.warning("⚠️ Local mode module not available - local mode disabled")

# Import auth router
try:
    from backend.app.api import auth
    app.include_router(auth.router)
except ImportError:
    logger.warning("⚠️ Auth module not available - authentication disabled")

# Import candidates router
try:
    from backend.app.api import candidates
    app.include_router(candidates.router)
except ImportError:
    logger.warning("⚠️ Candidates module not available - candidates management disabled")

# Import barem router
try:
    from backend.app.api import barem
    app.include_router(barem.router)
except ImportError:
    logger.warning("⚠️ Barem module not available - barem view disabled")

# Health check endpoint for Docker (at /api/health)
@app.get("/api/health")
async def api_health_check():
    """Health check endpoint for Docker/Kubernetes"""
    db_status = check_db_connection()
    return {
        "status": "healthy",
        "service": "score-parade",
        "database": "connected" if db_status else "disconnected"
    }

output_dir = Path("data") / "output"

@app.get("/api/videos/{filepath:path}")
async def get_skeleton_video(filepath: str):
    """
    Serve skeleton video files from data/output directory
    Supports paths like: session_id/skeleton_video.mp4
    """
    # Lấy tên file để log / header
    filename = Path(filepath).name

    # Security: Prevent directory traversal attacks
    video_path = (output_dir / filepath).resolve()
    if not str(video_path).startswith(str(output_dir.resolve())):
        logger.error(f"❌ Security: Attempted directory traversal: {filepath}")
        raise HTTPException(status_code=403, detail="Access denied")

    # Nếu frontend/request vẫn trỏ tới skeleton_video.mp4 (codec mp4v có thể không play được),
    # nhưng đã có bản web-friendly skeleton_video_web.mp4 thì ưu tiên phục vụ bản web.
    try:
        if video_path.name == "skeleton_video.mp4":
            web_path = video_path.with_name("skeleton_video_web.mp4")
            if web_path.exists() and web_path.stat().st_size > 0:
                logger.info(f"↪️ Using web-friendly skeleton video instead: {web_path}")
                video_path = web_path
                filename = web_path.name
    except Exception as e:
        logger.warning(f"⚠️ Failed to check web-friendly skeleton video: {e}")
    # ✅ LOGGING
    logger.info(f"Request for skeleton video: {filename} (raw path: {filepath})")
    
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
        logger.info(f"✅ Serving skeleton video: {filename} ({file_size} bytes) at path: {video_path}")
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
