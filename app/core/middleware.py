# app/core/middleware.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import re
from typing import Pattern, List, Set, Dict
import hashlib

class APISecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for additional API security measures:
    - Request timing and logging
    - Suspicious pattern detection
    - Basic anti-automation measures
    """
    
    def __init__(self, app):
        super().__init__(app)
        # Suspicious patterns in request paths or query parameters
        self.suspicious_patterns: List[Pattern] = [
            re.compile(r"SELECT\s+.*\s+FROM", re.IGNORECASE),  # SQL injection attempt
            re.compile(r"<script.*?>", re.IGNORECASE),          # XSS attempt
            re.compile(r"../../", re.IGNORECASE),               # Path traversal
            re.compile(r"^\s*\$\{.+\}$", re.IGNORECASE),        # Template injection
        ]
        
        # Track request counts by IP for anomaly detection
        self.request_tracker: Dict[str, Dict] = {}
        
        # Set of known automation tools by user-agent
        self.known_bots: Set[str] = {
            "googlebot", "bingbot", "yandexbot",  # Legitimate crawlers
            "wget", "curl", "python-requests", "go-http-client",  # Common tools
            "selenium", "phantomjs", "headless", "puppeteer"  # Browser automation
        }
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host
        
        # Start timer
        start_time = time.time()
        
        # Track request for this IP
        self._track_request(client_ip, request)
        
        # Check for suspicious patterns
        if self._has_suspicious_patterns(request):
            # Return 403 Forbidden for suspicious requests
            return Response(
                content='{"detail":"Forbidden"}',
                status_code=403,
                media_type="application/json"
            )
        
        # Check for obvious automation
        is_bot, bot_score = self._check_automation(request)
        
        # Process the request
        response = await call_next(request)
        
        # Calculate request time
        process_time = time.time() - start_time
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Add timing header (useful for monitoring)
        response.headers["X-Process-Time"] = str(process_time)
        
        # If suspiciously fast automated request, add delay based on bot score
        if is_bot and process_time < 0.1 and bot_score > 0.7:
            delay = min(bot_score * 2, 1.0)  # Max 1 second delay
            time.sleep(delay)
        
        return response
    
    def _track_request(self, client_ip: str, request: Request):
        """Track requests by IP for anomaly detection"""
        now = time.time()
        path = request.url.path
        
        # Initialize tracking for this IP if not exists
        if client_ip not in self.request_tracker:
            self.request_tracker[client_ip] = {
                "first_seen": now,
                "last_seen": now,
                "count": 0,
                "paths": {},
                "user_agents": set()
            }
        
        # Update tracker
        tracker = self.request_tracker[client_ip]
        tracker["last_seen"] = now
        tracker["count"] += 1
        
        # Track paths
        if path not in tracker["paths"]:
            tracker["paths"][path] = 0
        tracker["paths"][path] += 1
        
        # Track user agents
        user_agent = request.headers.get("user-agent", "")
        tracker["user_agents"].add(user_agent)
        
        # Cleanup old entries (basic memory management)
        # In production, this should be handled more efficiently
        if len(self.request_tracker) > 1000:
            self._cleanup_trackers()
    
    def _cleanup_trackers(self):
        """Remove old entries from the request tracker"""
        now = time.time()
        expire_time = now - 3600  # 1 hour expiration
        
        # Remove expired entries
        expired_ips = [
            ip for ip, data in self.request_tracker.items()
            if data["last_seen"] < expire_time
        ]
        
        for ip in expired_ips:
            del self.request_tracker[ip]
    
    def _has_suspicious_patterns(self, request: Request) -> bool:
        """Check for suspicious patterns in the request"""
        # Check path
        path = request.url.path
        
        # Check query parameters
        query_params = str(request.query_params)
        
        # Combine data to check
        data_to_check = f"{path} {query_params}"
        
        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if pattern.search(data_to_check):
                return True
        
        return False
    
    def _check_automation(self, request: Request) -> tuple:
        """
        Check if request appears to be from an automated tool
        Returns (is_bot, confidence_score)
        """
        user_agent = request.headers.get("user-agent", "").lower()
        
        # Score starts at 0
        bot_score = 0.0
        
        # Check for known automation in user-agent
        for bot in self.known_bots:
            if bot in user_agent:
                bot_score += 0.6
                break
        
        # Missing accept headers often indicates automation
        if not request.headers.get("accept"):
            bot_score += 0.2
        
        # Missing or suspicious referer
        referer = request.headers.get("referer", "")
        if not referer:
            bot_score += 0.1
        
        # Check for missing or irregular cookies
        if not request.cookies:
            bot_score += 0.1
        
        # Calculate final score (cap at 1.0)
        bot_score = min(bot_score, 1.0)
        
        return (bot_score > 0.5), bot_score