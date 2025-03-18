# app/core/rate_limiter.py
from typing import Optional, Callable, Dict
import time
from datetime import datetime
from fastapi import Request, HTTPException, status
from pydantic import BaseModel
import threading

# Simple in-memory storage for rate limiting
class RateLimitStorage:
    def __init__(self):
        self.storage: Dict[str, Dict] = {}
        self.lock = threading.Lock()
        
        # Start a cleanup thread to prevent memory leaks
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start a thread to periodically clean up expired entries"""
        def cleanup_task():
            while True:
                self._cleanup()
                time.sleep(60)  # Run cleanup every minute
        
        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()
    
    def _cleanup(self):
        """Remove expired entries from storage"""
        now = time.time()
        with self.lock:
            keys_to_remove = []
            for key, data in self.storage.items():
                if data.get("expires_at", 0) < now:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.storage[key]
    
    def increment(self, key: str, window: int = 60) -> int:
        """Increment counter for a key and return the current count"""
        with self.lock:
            now = time.time()
            data = self.storage.get(key, {"count": 0, "expires_at": now + window})
            
            # If the window has expired, reset the counter
            if data["expires_at"] < now:
                data = {"count": 0, "expires_at": now + window}
            
            # Increment counter
            data["count"] += 1
            self.storage[key] = data
            
            return data["count"]
    
    def get_remaining(self, key: str, limit: int) -> dict:
        """Get remaining requests and reset time"""
        with self.lock:
            data = self.storage.get(key, {"count": 0, "expires_at": time.time() + 60})
            remaining = max(0, limit - data["count"])
            reset_at = data["expires_at"]
            return {
                "remaining": remaining,
                "reset_at": datetime.fromtimestamp(reset_at).isoformat()
            }

# Global rate limit storage instance
rate_limit_storage = RateLimitStorage()

# Rate limiter dependency
class RateLimiter:
    def __init__(
        self,
        limit: int = 60,
        window: int = 60,
        key_func: Optional[Callable] = None
    ):
        self.limit = limit
        self.window = window
        self.key_func = key_func or (lambda request: request.client.host)
    
    async def __call__(self, request: Request):
        # Get the key for this request (e.g., IP address, user ID, etc.)
        key = f"ratelimit:{self.key_func(request)}"
        
        # Increment counter and check if limit exceeded
        current = rate_limit_storage.increment(key, self.window)
        
        # Get remaining info for headers
        remaining_info = rate_limit_storage.get_remaining(key, self.limit)
        
        # Set rate limit headers
        request.state.rate_limit_remaining = remaining_info["remaining"]
        request.state.rate_limit_reset = remaining_info["reset_at"]
        
        # Check if limit exceeded
        if current > self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": remaining_info["reset_at"],
                    "Retry-After": str(self.window)
                }
            )
        
        return True
    

# Define rate limiters with different limits for different endpoints
get_leaderboard_limiter = RateLimiter(limit=120, window=60)  # 120 requests per minute
get_player_rank_limiter = RateLimiter(limit=60, window=60)   # 60 requests per minute
submit_score_limiter = RateLimiter(limit=10, window=60)      # 10 requests per minute