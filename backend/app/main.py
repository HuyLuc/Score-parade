"""
FastAPI main application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import API_CONFIG

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

# Import và đăng ký routes
from backend.app.api import auth

@app.get("/")
async def root():
    return {"message": "Score Parade API", "version": API_CONFIG["version"]}

@app.get("/health")
async def health():
    return {"status": "ok"}

# Đăng ký routes
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
# TODO: Đăng ký các routes khác khi implement
# app.include_router(candidates.router, prefix="/api/candidates", tags=["candidates"])
# app.include_router(camera.router, prefix="/api/camera", tags=["camera"])
# app.include_router(scoring.router, prefix="/api/scoring", tags=["scoring"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

