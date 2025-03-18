# app/core/cache.py
import time
from functools import wraps
from cachetools import TTLCache, cached
import hashlib
import json

# Simple in-memory cache using cachetools
# TTLCache provides time-based expiration
# Default: 1024 items with 5-minute (300s) expiration
leaderboard_cache = TTLCache(maxsize=1024, ttl=300)
player_rank_cache = TTLCache(maxsize=2048, ttl=60)  # 1-minute TTL for player ranks

def invalidate_leaderboard_cache():
    """Clear the leaderboard cache when scores change"""
    leaderboard_cache.clear()

def invalidate_player_rank_cache(user_id=None):
    """
    Clear player rank cache
    If user_id is provided, only invalidate that user's cache
    Otherwise invalidate all rank caches
    """
    if user_id is None:
        player_rank_cache.clear()
    else:
        keys_to_remove = []
        for key in player_rank_cache:
            if isinstance(key, tuple) and len(key) > 0 and key[0] == user_id:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            player_rank_cache.pop(key, None)

def cache_key_builder(*args, **kwargs):
    """
    Build a cache key from args and kwargs
    Used for more complex caching scenarios
    """
    key = str(args) + str(sorted(kwargs.items()))
    return hashlib.md5(key.encode()).hexdigest()

def cached_leaderboard(func):
    """Decorator to cache leaderboard results"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Simplified key generation for leaderboard
        key = f"leaderboard:{kwargs.get('limit', 10)}:{kwargs.get('page', 1)}"
        
        # Check if result is in cache
        if key in leaderboard_cache:
            return leaderboard_cache[key]
        
        # Get result from function
        result = await func(*args, **kwargs)
        
        # Store in cache
        leaderboard_cache[key] = result
        
        return result
    return wrapper

def cached_player_rank(func):
    """Decorator to cache player rank results"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        user_id = kwargs.get('user_id')
        if not user_id and len(args) > 2:  # Check if user_id is in args
            user_id = args[2]
        
        # Create key based on user_id
        key = f"player_rank:{user_id}"
        
        # Check if result is in cache
        if key in player_rank_cache:
            return player_rank_cache[key]
        
        # Get result from function
        result = await func(*args, **kwargs)
        
        # Store in cache
        player_rank_cache[key] = result
        
        return result
    return wrapper