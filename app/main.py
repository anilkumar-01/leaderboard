# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import auth, leaderboard

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="A gaming leaderboard API for tracking and displaying player performance",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    debug=settings.DEBUG
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Include API routers
# app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(leaderboard.router, prefix=settings.API_V1_PREFIX)

@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "ok"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)