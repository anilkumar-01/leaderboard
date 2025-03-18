# tests/conftest.py
import pytest
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path to make app imports work
# root_dir = Path(__file__).resolve().parent.parent
# sys.path.insert(0, str(root_dir))

# Disable rate limiting for most tests
os.environ["TESTING"] = "True"

# Import this after setting TESTING env var to ensure rate limiting is disabled
from app.core.rate_limiter import RateLimiter

# Override rate limiter for testing to avoid test failures due to rate limits
# This is used for all tests except those specifically testing rate limiting
@pytest.fixture
def disable_rate_limiter(monkeypatch):
    """Override the rate limiter call method to always return True during tests"""
    original_call = RateLimiter.__call__
    
    async def mock_call(*args, **kwargs):
        return True
    
    monkeypatch.setattr(RateLimiter, "__call__", mock_call)
    yield
    monkeypatch.setattr(RateLimiter, "__call__", original_call)

# Helper to create a modified rate limiter for controlled testing of rate limits
@pytest.fixture
def test_rate_limiter():
    """Create a rate limiter with a very low limit for testing rate limiting"""
    return RateLimiter(limit=3, window=60)  # Only 3 requests per minute for testing

# You can add more fixtures here as needed for your tests