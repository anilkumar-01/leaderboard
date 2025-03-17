# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import auth, leaderboard

import newrelic.agent
from starlette.middleware.base import BaseHTTPMiddleware
import time
import sqlalchemy 

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="A gaming leaderboard API for tracking and displaying player performance",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    debug=settings.DEBUG
)

Add New Relic middleware for tracking requests
class NewRelicMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        
        # Create a New Relic web transaction
        nr_transaction = newrelic.agent.current_transaction()
        if nr_transaction:
            nr_transaction.name = f"{request.method} {request.url.path}"
        
        response = await call_next(request)
        
        # Add response time as a custom metric
        process_time = time.time() - start_time
        if nr_transaction:
            newrelic.agent.record_custom_metric('response_time', process_time)
        
        return response

app.add_middleware(NewRelicMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Include API routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
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
