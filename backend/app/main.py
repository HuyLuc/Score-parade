"""
FastAPI main application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import traceback
import logging
from backend.app.config import API_CONFIG
from backend.app.database.base import init_db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=API_CONFIG["title"],
    version=API_CONFIG["version"],
    docs_url=API_CONFIG["docs_url"],
    redoc_url=API_CONFIG["redoc_url"]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên giới hạn
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import custom exceptions
from backend.app.utils.exceptions import CustomException


@app.exception_handler(CustomException)
async def custom_exception_handler(request, exc: CustomException):
    """Handle all custom exceptions with consistent response format"""
    logger.error(f"CustomException: {exc.detail} (code: {exc.code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "code": exc.code,
            "path": str(request.url)
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """Handle FastAPI request validation errors"""
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "code": "VALIDATION_ERROR",
            "errors": exc.errors(),
            "path": str(request.url)
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Catch-all handler for any unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "code": "INTERNAL_ERROR",
            "path": str(request.url)
        }
    )


# Import và đăng ký routes
from backend.app.api import (
    auth,
    candidates,
    configuration,
    barem,
    camera,
    local,
    global_mode as global_api,
)
from backend.app.api import results as results_api

@app.get("/")
async def root():
    return {"message": "Score Parade API", "version": API_CONFIG["version"]}

@app.get("/health")
async def health():
    return {"status": "ok"}

# Đăng ký routes
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(candidates.router, prefix="/api/candidates", tags=["candidates"])
app.include_router(configuration.router, prefix="/api/configuration", tags=["configuration"])
app.include_router(barem.router, prefix="/api/barem", tags=["barem"])
app.include_router(camera.router, prefix="/api/camera", tags=["camera"])
app.include_router(local.router, prefix="/api/local", tags=["local"])
app.include_router(global_api.router, prefix="/api/global", tags=["global"])
app.include_router(results_api.router, prefix="/api/results", tags=["results"])
# TODO: Đăng ký các routes khác khi implement
# app.include_router(scoring.router, prefix="/api/scoring", tags=["scoring"])

@app.on_event("startup")
async def on_startup():
    # Tạo bảng nếu chưa có (tiện cho môi trường demo/docker)
    init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

