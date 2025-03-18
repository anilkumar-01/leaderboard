from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

import newrelic.agent
from starlette.middleware.base import BaseHTTPMiddleware

import time

from app.config import settings
from app.api import api_router
from app.core.middleware import APISecurityMiddleware

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

# Add API security middleware
app.add_middleware(APISecurityMiddleware)

# Add request timing middleware for performance monitoring
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Add New Relic middleware for tracking requests
# class NewRelicMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request, call_next):
#         start_time = time.time()
        
#         # Create a New Relic web transaction
#         nr_transaction = newrelic.agent.current_transaction()
#         if nr_transaction:
#             nr_transaction.name = f"{request.method} {request.url.path}"
        
#         response = await call_next(request)
        
#         # Add response time as a custom metric
#         process_time = time.time() - start_time
#         if nr_transaction:
#             newrelic.agent.record_custom_metric('response_time', process_time)
        
#         return response

# app.add_middleware(NewRelicMiddleware)

# Include API routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

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
